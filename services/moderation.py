"""
Команди модерації груп — /ban, /kick, /mute, /unmute, /unban, /warn, /modlog,
/antispam, /badword, /warnlimit, /floodlimit — плюс автомодерація (флуд і
заборонені слова) фоновим обробником повідомлень у групі.

## Ізоляція від джерел/каналів (ключова вимога ТЗ, п.А)

Цей модуль НІКОЛИ не імпортує й не звертається до логіки каналів/джерел
парсингу (storage.add_channel, storage.get_channels, storage.add_source
і т.д.). Єдина персистентна пам'ять, яку модуль використовує, — окремі
kv-простори "moderation_warns" / "moderation_settings" / "moderation_log",
жоден з яких жодна функція списку джерел/каналів навіть не читає. Група,
де бот модерує, НІКОЛИ не з'являється в інтерфейсі керування контентом
(вкладки "Джерела"/"Новини").

## Stateless ціль команд (п.В ТЗ)

/ban, /kick, /mute, /unmute, /warn спрацьовують на основі reply — ціль береться
з повідомлення, на яке відповіли. /unban — виняток (забанений не завжди може
лишити повідомлення, на яке можна відповісти), тому приймає user_id аргументом,
а якщо команда все ж викликана реплаєм — бере ціль з нього.

Жодної звірки зі списком "довірених" чатів з панелі — команди працюють у
БУДЬ-ЯКІЙ групі, де бот є адміністратором з потрібними правами, і де того,
хто їх викликав, Telegram сам підтверджує як адміністратора цієї ж групи.

## Автомодерація

`on_group_message` — фоновий обробник ЗВИЧАЙНИХ (не команда) повідомлень у
групі, вмикається командою /antispam on (вимкнено за замовчуванням, щоб не
змінювати поведінку існуючих груп без явного рішення адміна). Дві незалежні
перевірки:
  - флуд: якщо один учасник шле більше flood_limit повідомлень за
    flood_window секунд — автодія (типово mute) + видалення повідомлення-
    тригера. Лічильник часових міток лежить у пам'яті процесу (не в БД) —
    це навмисно: короткий ковзний вікно в кілька секунд не має сенсу
    переживати перезапуск бота, а БД-запис на КОЖНЕ повідомлення групи —
    зайве навантаження.
  - заборонені слова: якщо текст містить слово зі списку групи (регістр
    не важливий) — видалення повідомлення + автодія (типово warn).

Автодії використовують ту саму логіку, що й ручні команди (_apply_action),
тож і ручні, і автоматичні спрацювання однаково потрапляють у /modlog.

## Реєстрація в bot.py

    import moderation
    ...
    application.add_handler(CommandHandler("ban", moderation.cmd_ban, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("kick", moderation.cmd_kick, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("mute", moderation.cmd_mute, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("unmute", moderation.cmd_unmute, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("unban", moderation.cmd_unban, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("warn", moderation.cmd_warn, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("modlog", moderation.cmd_modlog, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("antispam", moderation.cmd_antispam, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("badword", moderation.cmd_badword, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("warnlimit", moderation.cmd_warnlimit, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("floodlimit", moderation.cmd_floodlimit, filters=filters.ChatType.GROUPS))
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND, moderation.on_group_message,
    ))

І в обробнику my_chat_member (де раніше БЕЗУМОВНО викликався storage.add_channel
для будь-якого чату) — розгалуження по chat.type ПЕРЕД будь-яким storage.*
викликом:

    if chat.type in ("group", "supergroup"):
        await moderation.on_moderation_chat_membership_change(chat, old_status, new_member, context)
        return
    # ...далі йде вже тільки гілка каналів (chat.type == "channel"), без змін...
"""
from __future__ import annotations

import logging
import re
import time

from telegram import Update, ChatPermissions
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes

from data import storage

logger = logging.getLogger(__name__)

# У різних версіях python-telegram-bot статус "вигнано з чату" називається
# по-різному (KICKED у старіших, BANNED у новіших) — той самий фікс, що й у
# bot.py, продубльований тут навмисно: moderation.py свідомо НЕ імпортує
# bot.py (щоб уникнути циклічного імпорту й лишитись повністю самодостатнім
# модулем — саме та ізоляція, якої вимагає ТЗ).
_CHAT_MEMBER_KICKED_STATUS = getattr(ChatMemberStatus, "BANNED", None) or getattr(ChatMemberStatus, "KICKED")


def _target_user(update: Update):
    """Ціль команди — той, на чиє повідомлення відповіли (reply): стандартний
    підхід груп-модерації в Telegram-ботах, що не вимагає жодного окремого
    пошуку по @username/id чи звернення до зовнішніх списків."""
    msg = update.effective_message
    if msg and msg.reply_to_message and msg.reply_to_message.from_user:
        return msg.reply_to_message.from_user
    return None


async def _require_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Викликати команду може лише адміністратор ЦІЄЇ конкретної групи —
    перевіряється напряму через Telegram (get_chat_member по chat.id з
    поточного апдейту), а не через жоден список з панелі керування."""
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user:
        return False
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
    except Exception:
        return False
    return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)


async def _delete_replied_message(update: Update) -> None:
    """Найкраще зусилля: прибираємо повідомлення-порушник разом з дією над
    автором. Не критично, якщо не вдасться (бот без прав, повідомлення вже
    видалено) — модерація людини все одно застосовується."""
    msg = update.effective_message
    if msg and msg.reply_to_message:
        try:
            await msg.reply_to_message.delete()
        except Exception:
            pass


_MUTE_PERMISSIONS = ChatPermissions(
    can_send_messages=False, can_send_audios=False, can_send_documents=False,
    can_send_photos=False, can_send_videos=False, can_send_video_notes=False,
    can_send_voice_notes=False, can_send_polls=False, can_send_other_messages=False,
    can_add_web_page_previews=False,
)
_UNMUTE_PERMISSIONS = ChatPermissions(
    can_send_messages=True, can_send_audios=True, can_send_documents=True,
    can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
    can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
    can_add_web_page_previews=True,
)

_DURATION_RE = re.compile(r"^(\d+)([smhd])$", re.IGNORECASE)
_DURATION_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def _parse_duration(text: str | None) -> int | None:
    """"10m"/"1h"/"2d"/"30s" -> секунди. None, якщо аргумент відсутній чи
    не розпізнаний (тоді дія безтермінова)."""
    if not text:
        return None
    m = _DURATION_RE.match(text.strip())
    if not m:
        return None
    return int(m.group(1)) * _DURATION_SECONDS[m.group(2).lower()]


def _log_action(chat_id: int, action: str, target, actor_label: str, reason: str = "") -> None:
    storage.add_moderation_log(chat_id, {
        "ts": time.time(),
        "action": action,
        "target_id": target.id if target else None,
        "target_name": target.full_name if target else None,
        "by": actor_label,
        "reason": reason,
    })


async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_group_admin(update, context):
        await update.effective_message.reply_text("Ця команда — лише для адміністраторів групи.")
        return
    target = _target_user(update)
    if not target:
        await update.effective_message.reply_text("Дай команду /ban у відповідь (reply) на повідомлення учасника, якого треба забанити.")
        return
    chat_id = update.effective_chat.id
    try:
        await context.bot.ban_chat_member(chat_id=chat_id, user_id=target.id)
    except Exception as e:
        logger.warning(f"[MODERATION] Не вдалося забанити {target.id} у {chat_id}: {e}")
        await update.effective_message.reply_text(f"Не вдалося забанити: {e}")
        return
    storage.clear_moderation_warns(chat_id, target.id)
    await _delete_replied_message(update)
    _log_action(chat_id, "ban", target, update.effective_user.full_name)
    await update.effective_message.reply_text(f"🚫 {target.full_name} забанений у цій групі.")


async def cmd_kick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Класичний "кік" — бан одразу зі зняттям бану, щоб людина могла
    повернутись за новим запрошенням (на відміну від /ban, який лишає
    заборону назавжди)."""
    if not await _require_group_admin(update, context):
        await update.effective_message.reply_text("Ця команда — лише для адміністраторів групи.")
        return
    target = _target_user(update)
    if not target:
        await update.effective_message.reply_text("Дай команду /kick у відповідь (reply) на повідомлення учасника.")
        return
    chat_id = update.effective_chat.id
    try:
        await context.bot.ban_chat_member(chat_id=chat_id, user_id=target.id)
        await context.bot.unban_chat_member(chat_id=chat_id, user_id=target.id, only_if_banned=True)
    except Exception as e:
        logger.warning(f"[MODERATION] Не вдалося кікнути {target.id} у {chat_id}: {e}")
        await update.effective_message.reply_text(f"Не вдалося виключити: {e}")
        return
    await _delete_replied_message(update)
    _log_action(chat_id, "kick", target, update.effective_user.full_name)
    await update.effective_message.reply_text(f"👢 {target.full_name} виключений з групи (може зайти за новим запрошенням).")


async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """На відміну від ban/kick/mute/warn — приймає user_id аргументом, бо
    забаненого не завжди можна знайти реплаєм на його повідомлення (якщо
    команда все ж викликана реплаєм, ціль береться з нього, як і всюди)."""
    if not await _require_group_admin(update, context):
        await update.effective_message.reply_text("Ця команда — лише для адміністраторів групи.")
        return
    target = _target_user(update)
    target_id = target.id if target else None
    if target_id is None and context.args:
        try:
            target_id = int(context.args[0])
        except ValueError:
            target_id = None
    if target_id is None:
        await update.effective_message.reply_text("Використання: /unban <user_id> (або реплаєм на повідомлення учасника).")
        return
    chat_id = update.effective_chat.id
    try:
        await context.bot.unban_chat_member(chat_id=chat_id, user_id=target_id, only_if_banned=True)
    except Exception as e:
        logger.warning(f"[MODERATION] Не вдалося розбанити {target_id} у {chat_id}: {e}")
        await update.effective_message.reply_text(f"Не вдалося розбанити: {e}")
        return
    _log_action(chat_id, "unban", target or type("T", (), {"id": target_id, "full_name": str(target_id)})(), update.effective_user.full_name)
    await update.effective_message.reply_text(f"✅ Учасника {target_id} розбанено.")


async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_group_admin(update, context):
        await update.effective_message.reply_text("Ця команда — лише для адміністраторів групи.")
        return
    target = _target_user(update)
    if not target:
        await update.effective_message.reply_text("Дай команду /mute у відповідь (reply) на повідомлення учасника. Можна з тривалістю: /mute 1h")
        return
    chat_id = update.effective_chat.id
    duration = _parse_duration(context.args[0]) if context.args else None
    kwargs = {"chat_id": chat_id, "user_id": target.id, "permissions": _MUTE_PERMISSIONS}
    if duration:
        kwargs["until_date"] = int(time.time()) + duration
    try:
        await context.bot.restrict_chat_member(**kwargs)
    except Exception as e:
        logger.warning(f"[MODERATION] Не вдалося замʼютити {target.id} у {chat_id}: {e}")
        await update.effective_message.reply_text(f"Не вдалося обмежити: {e}")
        return
    await _delete_replied_message(update)
    label = f" на {context.args[0]}" if duration else ""
    _log_action(chat_id, "mute", target, update.effective_user.full_name, reason=context.args[0] if duration else "")
    await update.effective_message.reply_text(f"🔇 {target.full_name} обмежений у надсиланні повідомлень{label}.")


async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_group_admin(update, context):
        await update.effective_message.reply_text("Ця команда — лише для адміністраторів групи.")
        return
    target = _target_user(update)
    if not target:
        await update.effective_message.reply_text("Дай команду /unmute у відповідь (reply) на повідомлення учасника.")
        return
    chat_id = update.effective_chat.id
    try:
        await context.bot.restrict_chat_member(chat_id=chat_id, user_id=target.id, permissions=_UNMUTE_PERMISSIONS)
    except Exception as e:
        logger.warning(f"[MODERATION] Не вдалося зняти обмеження з {target.id} у {chat_id}: {e}")
        await update.effective_message.reply_text(f"Не вдалося зняти обмеження: {e}")
        return
    _log_action(chat_id, "unmute", target, update.effective_user.full_name)
    await update.effective_message.reply_text(f"🔊 З {target.full_name} знято обмеження.")


async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_group_admin(update, context):
        await update.effective_message.reply_text("Ця команда — лише для адміністраторів групи.")
        return
    target = _target_user(update)
    if not target:
        await update.effective_message.reply_text("Дай команду /warn у відповідь (reply) на повідомлення учасника.")
        return
    chat_id = update.effective_chat.id
    await _delete_replied_message(update)
    await _warn_and_maybe_ban(chat_id, target, context, actor_label=update.effective_user.full_name, reply_to=update.effective_message)


async def _warn_and_maybe_ban(chat_id: int, target, context: ContextTypes.DEFAULT_TYPE, actor_label: str, reply_to=None) -> None:
    """Спільна логіка нарахування попередження й автобану на ліміті — викликається
    і з ручного /warn, і з автомодерації (badword_action="warn")."""
    count = storage.add_moderation_warn(chat_id, target.id)
    limit = storage.get_moderation_settings(chat_id)["warn_limit"]
    _log_action(chat_id, "warn", target, actor_label, reason=f"{count}/{limit or '∞'}")

    async def _reply(text: str):
        if reply_to is not None:
            await reply_to.reply_text(text)

    if limit and count >= limit:
        try:
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=target.id)
            storage.clear_moderation_warns(chat_id, target.id)
            _log_action(chat_id, "autoban", target, "система (ліміт попереджень)")
            await _reply(f"⚠️ {target.full_name}: попередження {count}/{limit} — ліміт вичерпано, учасника забанено.")
        except Exception as e:
            logger.warning(f"[MODERATION] Не вдалося автоматично забанити {target.id} у {chat_id} після ліміту: {e}")
            await _reply(f"⚠️ {target.full_name}: попередження {count}/{limit} — ліміт вичерпано, але забанити не вдалося: {e}")
        return
    await _reply(f"⚠️ {target.full_name}: попередження {count}/{limit or '∞'}.")


async def cmd_modlog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_group_admin(update, context):
        await update.effective_message.reply_text("Ця команда — лише для адміністраторів групи.")
        return
    chat_id = update.effective_chat.id
    limit = 10
    if context.args:
        try:
            limit = max(1, min(50, int(context.args[0])))
        except ValueError:
            pass
    entries = storage.get_moderation_log(chat_id, limit)
    if not entries:
        await update.effective_message.reply_text("Історія модерації цієї групи поки порожня.")
        return
    _ACTION_LABEL = {
        "ban": "🚫 бан", "kick": "👢 кік", "unban": "✅ розбан", "mute": "🔇 мʼют",
        "unmute": "🔊 зняття мʼюту", "warn": "⚠️ попередження", "autoban": "🚫 автобан",
        "antispam_delete": "🧹 антиспам (видалення)",
    }
    lines = []
    for e in entries:
        ts = time.strftime("%d.%m %H:%M", time.localtime(e.get("ts", 0)))
        label = _ACTION_LABEL.get(e.get("action"), e.get("action", "?"))
        target_name = e.get("target_name") or e.get("target_id") or "?"
        reason = f" ({e['reason']})" if e.get("reason") else ""
        lines.append(f"{ts} — {label}: {target_name}{reason} · {e.get('by', '?')}")
    await update.effective_message.reply_text("Останні дії модерації:\n" + "\n".join(lines))


async def cmd_antispam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_group_admin(update, context):
        await update.effective_message.reply_text("Ця команда — лише для адміністраторів групи.")
        return
    chat_id = update.effective_chat.id
    arg = (context.args[0].lower() if context.args else "")
    if arg not in ("on", "off"):
        current = storage.get_moderation_settings(chat_id)["antispam_enabled"]
        await update.effective_message.reply_text(
            f"Автомодерація зараз {'увімкнена' if current else 'вимкнена'}.\nВикористання: /antispam on або /antispam off"
        )
        return
    storage.update_moderation_settings(chat_id, antispam_enabled=(arg == "on"))
    await update.effective_message.reply_text(f"Автомодерація {'увімкнена ✅' if arg == 'on' else 'вимкнена ❌'}.")


async def cmd_badword(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_group_admin(update, context):
        await update.effective_message.reply_text("Ця команда — лише для адміністраторів групи.")
        return
    chat_id = update.effective_chat.id
    sub = (context.args[0].lower() if context.args else "")
    rest = " ".join(context.args[1:]).strip().lower() if len(context.args) > 1 else ""

    if sub == "list" or not sub:
        words = storage.get_moderation_settings(chat_id)["bad_words"]
        text = ", ".join(words) if words else "(порожньо)"
        await update.effective_message.reply_text(
            f"Заборонені слова цієї групи: {text}\n\n"
            "Керування: /badword add <слово>, /badword remove <слово>"
        )
        return

    words = storage.get_moderation_settings(chat_id)["bad_words"]
    if sub == "add":
        if not rest:
            await update.effective_message.reply_text("Використання: /badword add <слово>")
            return
        if rest not in words:
            words.append(rest)
            storage.update_moderation_settings(chat_id, bad_words=words)
        await update.effective_message.reply_text(f"Додано в список заборонених: «{rest}»")
    elif sub == "remove":
        if not rest:
            await update.effective_message.reply_text("Використання: /badword remove <слово>")
            return
        if rest in words:
            words.remove(rest)
            storage.update_moderation_settings(chat_id, bad_words=words)
            await update.effective_message.reply_text(f"Прибрано зі списку заборонених: «{rest}»")
        else:
            await update.effective_message.reply_text("Такого слова немає в списку.")
    else:
        await update.effective_message.reply_text("Використання: /badword add <слово> | /badword remove <слово> | /badword list")


async def cmd_warnlimit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_group_admin(update, context):
        await update.effective_message.reply_text("Ця команда — лише для адміністраторів групи.")
        return
    chat_id = update.effective_chat.id
    if not context.args:
        current = storage.get_moderation_settings(chat_id)["warn_limit"]
        await update.effective_message.reply_text(
            f"Поточний ліміт попереджень: {current or 'вимкнено'}.\nВикористання: /warnlimit <число> (0 — вимкнути автобан)"
        )
        return
    try:
        limit = max(0, int(context.args[0]))
    except ValueError:
        await update.effective_message.reply_text("Ліміт має бути числом.")
        return
    storage.update_moderation_settings(chat_id, warn_limit=limit)
    await update.effective_message.reply_text(f"Ліміт попереджень встановлено: {limit or 'вимкнено (автобан не спрацює)'}.")


async def cmd_floodlimit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_group_admin(update, context):
        await update.effective_message.reply_text("Ця команда — лише для адміністраторів групи.")
        return
    chat_id = update.effective_chat.id
    if len(context.args) < 2:
        s = storage.get_moderation_settings(chat_id)
        await update.effective_message.reply_text(
            f"Поточний поріг флуду: {s['flood_limit']} повідомлень за {s['flood_window']} сек.\n"
            "Використання: /floodlimit <повідомлень> <секунд>"
        )
        return
    try:
        n = max(2, int(context.args[0]))
        window = max(2, int(context.args[1]))
    except ValueError:
        await update.effective_message.reply_text("Обидва аргументи мають бути числами.")
        return
    storage.update_moderation_settings(chat_id, flood_limit=n, flood_window=window)
    await update.effective_message.reply_text(f"Поріг флуду встановлено: {n} повідомлень за {window} сек.")


# ---------- Автомодерація ----------
# Мітки часу повідомлень для флуд-детекції — навмисно в пам'яті процесу, а
# не в БД (короткий ковзний вікно, БД-запис на кожне повідомлення групи —
# зайве навантаження; втрата цього стану при перезапуску бота нешкідлива).
_flood_tracker: dict[tuple[int, int], list[float]] = {}


async def _apply_autospam_action(action: str, chat_id: int, target, context: ContextTypes.DEFAULT_TYPE, reason: str) -> None:
    if action == "ban":
        try:
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=target.id)
            storage.clear_moderation_warns(chat_id, target.id)
            _log_action(chat_id, "ban", target, "автомодерація", reason=reason)
        except Exception as e:
            logger.warning(f"[MODERATION] Автомодерація: не вдалося забанити {target.id} у {chat_id}: {e}")
    elif action == "mute":
        try:
            await context.bot.restrict_chat_member(chat_id=chat_id, user_id=target.id, permissions=_MUTE_PERMISSIONS)
            _log_action(chat_id, "mute", target, "автомодерація", reason=reason)
        except Exception as e:
            logger.warning(f"[MODERATION] Автомодерація: не вдалося замʼютити {target.id} у {chat_id}: {e}")
    else:  # "warn" за замовчуванням
        await _warn_and_maybe_ban(chat_id, target, context, actor_label="автомодерація")


async def on_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Фоновий обробник ЗВИЧАЙНИХ повідомлень групи (не команд) — перевіряє
    флуд і заборонені слова, якщо /antispam увімкнено для цієї групи. Нічого
    не робить для груп, де автомодерація вимкнена (типово), — жодних побічних
    ефектів для тих, хто нею не користується."""
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not msg or not chat or not user or not msg.text:
        return

    settings = storage.get_moderation_settings(chat.id)
    if not settings["antispam_enabled"]:
        return

    # Адмінів автомодерація не займає — типова поведінка антиспам-ботів.
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        if member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return
    except Exception:
        pass

    # --- Заборонені слова ---
    bad_words = settings["bad_words"]
    if bad_words:
        text_lower = msg.text.lower()
        hit = next((w for w in bad_words if w in text_lower), None)
        if hit:
            try:
                await msg.delete()
            except Exception:
                pass
            _log_action(chat.id, "antispam_delete", user, "автомодерація", reason=f"заборонене слово «{hit}»")
            await _apply_autospam_action(settings["badword_action"], chat.id, user, context, reason=f"заборонене слово «{hit}»")
            return

    # --- Флуд ---
    key = (chat.id, user.id)
    now = time.time()
    window = settings["flood_window"]
    timestamps = [t for t in _flood_tracker.get(key, []) if now - t <= window]
    timestamps.append(now)
    _flood_tracker[key] = timestamps
    if len(timestamps) > settings["flood_limit"]:
        _flood_tracker[key] = []  # скидаємо, щоб не спрацьовувати на кожному наступному повідомленні поспіль
        try:
            await msg.delete()
        except Exception:
            pass
        reason = f"флуд: {len(timestamps)} повідомлень за {window} сек"
        _log_action(chat.id, "antispam_delete", user, "автомодерація", reason=reason)
        await _apply_autospam_action(settings["flood_action"], chat.id, user, context, reason=reason)


async def on_moderation_chat_membership_change(chat, old_status, new_member, context) -> None:
    """Бот доданий/видалений з ГРУПИ (не каналу). ЖОДНОГО storage.add_channel
    чи storage.add_source тут немає і НЕ повинно з'являтися (п.А.2 ТЗ) — це і
    є та "тиша", про яку просить ТЗ: бот просто перевіряє права й починає
    приймати команди модерації, нічого нікуди не записуючи про сам чат."""
    new_status = new_member.status
    if new_status == ChatMemberStatus.ADMINISTRATOR and old_status != ChatMemberStatus.ADMINISTRATOR:
        can_delete = bool(getattr(new_member, "can_delete_messages", False))
        can_restrict = bool(getattr(new_member, "can_restrict_members", False))
        logger.info(
            f"[MODERATION] Бота додано адміністратором у групу {chat.title} ({chat.id}) — "
            f"can_delete_messages={can_delete}, can_restrict_members={can_restrict}. "
            f"Джерело/канал НЕ створювався — модерація ізольована від панелі керування."
        )
        if not (can_delete and can_restrict):
            try:
                await context.bot.send_message(
                    chat.id,
                    "⚠️ Для повноцінної модерації видай боту права «Видаляти повідомлення» "
                    "і «Обмежувати учасників» у налаштуваннях групи.",
                )
            except Exception:
                pass
    elif new_status in (ChatMemberStatus.LEFT, _CHAT_MEMBER_KICKED_STATUS):
        logger.info(f"[MODERATION] Бота видалено з групи {chat.title} ({chat.id})")
