import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# .env лежить у корені проекту, а не в core/ — тож беремо батьківську папку core/.
# Це працює незалежно від того, з якої директорії запущена команда python app.py.
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)

import io
import json
import re
import time
from collections import Counter
import html as html_lib
import difflib
import tempfile
import asyncio
import feedparser
import httpx
from bs4 import BeautifulSoup, NavigableString
from datetime import datetime, timedelta, time as dtime

try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

try:
    from staticmap import StaticMap, CircleMarker, Line
    _STATICMAP_AVAILABLE = True
except ImportError:
    _STATICMAP_AVAILABLE = False

try:
    from google import genai as gemini_genai
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False

from telegram.constants import ChatMemberStatus

# У різних версіях python-telegram-bot статус "вигнано з чату" називається по-різному:
# старіші версії — ChatMemberStatus.KICKED, новіші (Bot API перейменувала kicked → banned) —
# ChatMemberStatus.BANNED. Беремо те, що є в поточній встановленій бібліотеці, замість
# жорсткої прив'язки до однієї назви — інакше bot.py падає прямо на імпорті модуля
# (AttributeError: KICKED), як тільки хтось запускає код на іншій версії пакета.
_CHAT_MEMBER_KICKED_STATUS = getattr(ChatMemberStatus, "BANNED", None) or getattr(ChatMemberStatus, "KICKED")
from telegram.error import RetryAfter
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, InputMediaPhoto, InputMediaVideo
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from data import storage
from services import deduplicator
from services import media_collector
from services import moderation
from services import push as push_module
from services import telethon_reader

# --- Настройки ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError(
        f"BOT_TOKEN не найден. Создай файл {_ENV_PATH} и добавь строку BOT_TOKEN=..."
    )

# Посилання на веб-панель (Mini App). ОБОВ'ЯЗКОВО https з дійсним сертифікатом —
# Telegram відмовляється відкривати web_app-кнопку на голому http://IP:порт,
# тож самого лише переїзду на VPS замало без reverse-proxy (Caddy/nginx+Let's
# Encrypt, Cloudflare Tunnel) чи тунелю (ngrok) поверх нього. Змінюється в .env,
# без правки коду.
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://example.com").strip()

NEWS_CHECK_INTERVAL_SECONDS = 60  # було 600 (10 хв) — тепер раз на хвилину, майже "в ту саму хвилину"
NEWS_MAX_AGE_MINUTES = 30  # Recency-фільтр: ігноруємо пости, старші за 30 хв на момент виявлення (легко змінити на 60)
MAX_NEW_ITEMS_PER_SOURCE_PER_CYCLE = 5  # раніше було 1 — активне джерело, що постить частіше за раз/хв,
# «застрягало» в черзі на дозвол і встигало застаріти (Recency-фільтр вище) ще до того, як до нього
# доходила черга; тепер за один прохід check_news забираємо весь свіжий бэклог джерела, а не по краплині


async def _fetch_feed(url: str):
    """Завантажує RSS через httpx із РЕАЛЬНИМ тайм-аутом і віддає вже завантажені байти
    в feedparser.parse — на відміну від голого feedparser.parse(url), який робить
    мережевий запит сам, без жодного тайм-ауту: одне зависле чи повільне джерело
    могло б тримати весь check_news довше за інтервал джоби (60с), через що
    apscheduler починав пропускати наступні тіки ("maximum number of running
    instances reached") — і новини переставали приходити взагалі, не тільки з
    того одного джерела."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True)
        resp.raise_for_status()
        content = resp.content
    return feedparser.parse(content)


def _is_post_fresh(post_dt, max_minutes: int = NEWS_MAX_AGE_MINUTES) -> bool:
    """Єдина перевірка свіжості поста для RSS (naive UTC datetime) і Telegram (aware datetime)."""
    if post_dt is None:
        return False
    try:
        now_ref = datetime.now(post_dt.tzinfo) if post_dt.tzinfo else datetime.utcnow()
        age_minutes = (now_ref - post_dt).total_seconds() / 60
        return age_minutes <= max_minutes
    except Exception:
        return False


# Суперадмін — той, кому дозволено міняти глобальні налаштування бота (наприклад, фото профілю)
SUPERADMIN_IDS = [1453368273]

# Файл лого для фото профілю бота (Bot API вимагає саме .JPG для статичного фото, без прозорості)
BOT_LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bot_logo.jpg")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def fetch_custom_emoji_set(bot, set_name: str) -> list[dict] | None:
    """Кастомні емодзі беруться з конкретного стікерпаку типу "custom_emoji"
    (адмін створює такий пак прямо в Telegram — через будь-який набір
    кастомних емодзі, яким він володіє чи на який має доступ — і дає боту
    лише short name паку, який видно в посиланні виду t.me/addemoji/<name>).
    Bot API свідомо не дає способу перелічити ВСІ кастомні емодзі, доступні
    конкретному Premium-користувачу напряму — тільки через пак.
    Повертає None, якщо пак не знайдено; список (може бути порожній), якщо знайдено."""
    try:
        sticker_set = await bot.get_sticker_set(set_name)
    except Exception as e:
        logger.warning(f"Не вдалося завантажити емодзі-пак {set_name}: {e}")
        return None
    result = []
    for sticker in sticker_set.stickers:
        custom_emoji_id = getattr(sticker, "custom_emoji_id", None)
        if not custom_emoji_id:
            continue
        thumb = sticker.thumbnail or sticker
        result.append({
            "id": custom_emoji_id,
            "emoji": sticker.emoji or "🙂",
            "file_id": thumb.file_id,
        })
    return result


async def fetch_telegram_file_bytes(bot, file_id: str) -> bytes | None:
    """Той самий підхід, що й get_avatar_bytes_smart нижче, але без диск-кешу —
    використовується для проксування прев'ю кастомних емодзі в панелі."""
    try:
        file = await bot.get_file(file_id)
        buf = io.BytesIO()
        await file.download_to_memory(buf)
        return buf.getvalue()
    except Exception as e:
        logger.warning(f"Не вдалося завантажити файл {file_id}: {e}")
        return None


async def get_avatar_bytes_smart(bot, target, cache_key) -> bytes | None:
    """Аватарка каналу/джерела з диск-кешу (storage.py); оновлює кеш лише якщо Telegram
    показує нове фото (small_file_unique_id відрізняється від закешованого) — тому
    /api/channel-avatar не смикає Telegram API на кожне відкриття WebApp.
    target — chat_id (int) або "@username" (str); cache_key — ключ кешу на диску."""
    try:
        chat = await bot.get_chat(target)
    except Exception as e:
        logger.warning(f"Не вдалося отримати чат {target} для аватарки: {e}")
        chat = None

    photo = getattr(chat, "photo", None) if chat else None
    cached_path = storage.get_channel_avatar_path(cache_key)

    if not photo:
        # Немає фото в Telegram (або чат тимчасово недоступний) — віддаємо старий кеш, якщо є
        if cached_path:
            with open(cached_path, "rb") as f:
                return f.read()
        return None

    cached_unique_id = storage.get_avatar_unique_id(cache_key)
    if cached_path and cached_unique_id == photo.small_file_unique_id:
        with open(cached_path, "rb") as f:
            return f.read()

    try:
        file = await bot.get_file(photo.small_file_id)
        buf = io.BytesIO()
        await file.download_to_memory(buf)
        image_bytes = buf.getvalue()
    except Exception as e:
        logger.warning(f"Не вдалося завантажити аватарку {target}: {e}")
        if cached_path:
            with open(cached_path, "rb") as f:
                return f.read()
        return None

    storage.save_channel_avatar(cache_key, image_bytes)
    storage.set_avatar_unique_id(cache_key, photo.small_file_unique_id)
    return image_bytes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start. Розпізнає deep-link /start channel_<id> від читачів каналу."""
    user = update.effective_user

    if context.args and context.args[0].startswith("channel_"):
        try:
            channel_id = int(context.args[0].removeprefix("channel_"))
        except ValueError:
            channel_id = None

        if channel_id is not None:
            channels = storage.get_active_channels()
            channel = next((c for c in channels if c["id"] == channel_id), None)
            if channel:
                storage.set_active_channel(user.id, channel_id, datetime.now().strftime("%d.%m %H:%M"))
                await update.message.reply_text(
                    f"👋 Вітаю!\n\n"
                    f"Тепер усе, що ти надішлеш сюди (текст, фото, відео, локацію) — "
                    f"потрапить модераторам каналу «{channel['title']}» на перевірку."
                )
                return

    if context.args and context.args[0] == "addtgsource":
        await add_telegram_source_start(update, context)
        return

    text = (
        "👋 Вітаю!\n\n"
        "Я бот сповіщень про повітряну тривогу.\n"
        "Коли з'явиться тривога у вашому регіоні — я надішлю повідомлення сюди.\n\n"
        "Тисни кнопку нижче, щоб відкрити меню налаштувань — усе на кнопках, "
        "команди набирати не обов'язково."
    )
    await update.message.reply_text(text, reply_markup=_main_menu_keyboard(context))


async def set_bot_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Встановлює фото профілю бота в Telegram (аватарку, яку бачать усі користувачі) —
    доступно тільки суперадміну. Використовує підготовлений bot_logo.jpg поруч з bot.py
    (саме .JPG, без прозорості — так вимагає Telegram Bot API для статичного фото)."""
    user_id = update.effective_user.id
    if user_id not in SUPERADMIN_IDS:
        await update.message.reply_text("⛔ Ця команда доступна лише суперадміну.")
        return

    if not os.path.exists(BOT_LOGO_PATH):
        await update.message.reply_text(f"Файл {BOT_LOGO_PATH} не знайдено на сервері.")
        return

    try:
        with open(BOT_LOGO_PATH, "rb") as f:
            photo_bytes = f.read()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/setMyProfilePhoto",
                data={"photo": json.dumps({"type": "static", "photo": "attach://bot_photo"})},
                files={"bot_photo": ("bot_logo.jpg", photo_bytes, "image/jpeg")},
                timeout=30,
            )
            result = resp.json()
        if result.get("ok"):
            await update.message.reply_text("✅ Фото профілю бота оновлено — тепер його бачать усі.")
        else:
            await update.message.reply_text(f"⛔ Telegram відповів помилкою: {result}")
    except Exception as e:
        logger.warning(f"Не вдалося оновити фото профілю бота: {e}")
        await update.message.reply_text(f"⛔ Помилка: {e}")


async def help_command_for_chat(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Отправляет список команд в указанный чат."""
    text = (
        "📋 Доступні команди:\n\n"
        "/menu — головне меню на кнопках (рекомендовано)\n"
        "/start — привітання\n"
        "/help — цей список команд\n"
        "/channels — список каналів розсилки (тривоги, новини, тест, видалення)\n"
        "/removechannel — видалити канал зі списку (з id) або показати список з id\n"
        "/sources — список джерел новин\n"
        "/addsource — додати сайт (RSS) як джерело\n"
        "/addtgsource — додати Telegram-канал як джерело\n"
        "/newsfilter — фільтр новин за ключовими словами\n\n"
        "Щоб додати канал — натисни кнопку нижче й обери канал зі списку. "
        "Бот сам зареєструється, коли отримає права адміністратора."
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "➕ Додати бота в канал",
            url=f"https://t.me/{context.bot.username}?startchannel&admin=change_info+post_messages+edit_messages+delete_messages+invite_users+restrict_members+pin_messages+promote_members+manage_chat+manage_video_chats+anonymous",
        )
    ]])
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает список доступных команд."""
    await help_command_for_chat(context, update.effective_chat.id)


def _main_menu_keyboard(context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup:
    rows = []
    if WEBAPP_URL and WEBAPP_URL != "https://example.com":
        rows.append([InlineKeyboardButton("🖥 Відкрити панель", web_app=WebAppInfo(url=WEBAPP_URL))])
    return InlineKeyboardMarkup(rows)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает главное меню бота."""
    await update.message.reply_text(
        "🔧 Головне меню\n\nОбери, що хочеш налаштувати:",
        reply_markup=_main_menu_keyboard(context),
    )


async def on_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатия кнопок главного меню."""
    query = update.callback_query
    await query.answer()
    section = query.data.split(":", 1)[1]
    chat_id = query.message.chat_id

    if section == "channels":
        await _send_channels_list(context, chat_id)

    elif section == "sources":
        await _send_sources_list(context, chat_id)

    elif section == "addsource_help":
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "➕ Додати джерело новин:\n\n"
                "🌐 Сайт (RSS) — надішли:\n"
                "<code>/addsource Назва https://посилання-на-rss</code>\n\n"
                "📢 Telegram-канал — просто напиши:\n"
                "<code>/addtgsource</code>\n"
                "і слідуй інструкціям."
            ),
            parse_mode="HTML",
        )

    elif section == "help":
        await help_command_for_chat(context, chat_id)

    # Показуємо меню знову внизу, щоб не треба було набирати /menu кожного разу
    await context.bot.send_message(
        chat_id=chat_id,
        text="🔧 Головне меню:",
        reply_markup=_main_menu_keyboard(context),
    )


def _channel_keyboard(ch: dict) -> InlineKeyboardMarkup:
    enabled = ch.get("enabled", True)
    news_enabled = ch.get("news_enabled", False)
    keywords = ch.get("news_keywords", [])
    status_label = "🟢 Тривоги: Увімкнено" if enabled else "🔴 Тривоги: Вимкнено"
    news_label = "📰 Новини: Увімкнено" if news_enabled else "📰 Новини: Вимкнено"
    filter_label = f"🔎 Фільтр: {len(keywords)} слів" if keywords else "🔎 Фільтр: немає"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(status_label, callback_data=f"toggle:{ch['id']}")],
        [InlineKeyboardButton(news_label, callback_data=f"newstoggle:{ch['id']}")],
        [InlineKeyboardButton(filter_label, callback_data=f"filterinfo:{ch['id']}")],
        [InlineKeyboardButton("📝 Написати новину зараз", callback_data=f"onenews:{ch['id']}")],
        [
            InlineKeyboardButton("🔔 Тест", callback_data=f"test:{ch['id']}"),
            InlineKeyboardButton("🗑 Видалити", callback_data=f"del:{ch['id']}"),
        ],
    ])


async def _send_channels_list(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Отправляет список каналов с кнопками управления в указанный чат."""
    channels = storage.get_channels()
    if not channels:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Каналів ще немає.\n\nНатисни /start і скористайся кнопкою «➕ Додати бота в канал».",
        )
        return

    await context.bot.send_message(chat_id=chat_id, text="📡 Канали розсилки:")
    for ch in channels:
        title = ch["title"]
        if ch.get("status") == "inactive":
            title = f"⚠️ {title} (бот видалений з каналу)"
        await context.bot.send_message(chat_id=chat_id, text=title, reply_markup=_channel_keyboard(ch))


async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает список каналов с кнопками управления."""
    await _send_channels_list(context, update.effective_chat.id)


async def on_channel_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатия кнопок «Тест» и «Видалити» в списке каналов."""
    query = update.callback_query
    await query.answer()

    action, chat_id_str = query.data.split(":", 1)
    chat_id = int(chat_id_str)

    if action == "del":
        ok = storage.remove_channel(chat_id)
        leave_error = None
        try:
            await context.bot.leave_chat(chat_id)
        except Exception as e:
            leave_error = str(e)
            logger.warning(f"Не вдалося вийти з каналу {chat_id}: {leave_error}")

        if ok and not leave_error:
            await query.edit_message_text(f"🗑 «{query.message.text}» видалено, бот вийшов з каналу.")
        elif ok and leave_error:
            await query.edit_message_text(
                f"🗑 «{query.message.text}» видалено зі списку розсилки.\n"
                f"⚠️ Але вийти з каналу не вдалося: {leave_error}"
            )
        else:
            await query.edit_message_text("Канал вже видалено або не знайдено.")

    elif action == "test":
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="🔔 Тестове повідомлення від бота сповіщень про тривогу.",
            )
            await query.answer("✅ Тестове повідомлення надіслано", show_alert=True)
        except Exception as e:
            await query.answer(f"⛔ Помилка: {e}", show_alert=True)

    elif action == "toggle":
        current = storage.is_channel_enabled(chat_id)
        storage.set_channel_enabled(chat_id, not current)
        channels = storage.get_channels()
        ch = next((c for c in channels if c["id"] == chat_id), None)
        if ch:
            await query.edit_message_reply_markup(reply_markup=_channel_keyboard(ch))
            state_text = "увімкнено" if ch["enabled"] else "вимкнено"
            await query.answer(f"Авто-тривоги {state_text} для цього каналу")

    elif action == "newstoggle":
        current = storage.is_channel_news_enabled(chat_id)
        storage.set_channel_news_enabled(chat_id, not current)
        channels = storage.get_channels()
        ch = next((c for c in channels if c["id"] == chat_id), None)
        if ch:
            await query.edit_message_reply_markup(reply_markup=_channel_keyboard(ch))
            state_text = "увімкнено" if ch.get("news_enabled") else "вимкнено"
            await query.answer(f"Автоновини {state_text} для цього каналу")

    elif action == "filterinfo":
        keywords = storage.get_channel_keywords(chat_id)
        current = ", ".join(keywords) if keywords else "немає (пропускаються всі новини)"
        await query.answer()
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                f"🔎 Фільтр для «{query.message.text}»:\n"
                f"Поточний: {current}\n\n"
                f"Щоб налаштувати — надішли:\n"
                f"<code>/newsfilter {chat_id} війна, фронт, обстріл</code>\n\n"
                f"Щоб прибрати фільтр — надішли:\n"
                f"<code>/newsfilter {chat_id} clear</code>"
            ),
            parse_mode="HTML",
        )


    elif action == "onenews":
        keywords = storage.get_channel_keywords(chat_id)
        channel = next((c for c in storage.get_channels() if c["id"] == chat_id), None)
        owner_admin_id = channel.get("added_by") if channel else None
        result = await _get_latest_single_news(owner_admin_id, keywords)
        if result is None:
            await query.answer("Не знайдено новин під поточний фільтр.", show_alert=True)
            return

        source_name, title, link = result
        title = await _translate_plain_to_uk(title)
        text = f"📰 <b>{source_name}</b>\n\n{title}\n{link}"
        try:
            await context.bot.send_message(
                chat_id=chat_id, text=text, parse_mode="HTML",
                disable_web_page_preview=False,
            )
            storage.add_seen_news(link)
            storage.add_recent_title(_normalize_title(title))
            await query.answer("✅ Новину надіслано в канал", show_alert=True)
        except Exception as e:
            await query.answer(f"⛔ Помилка: {e}", show_alert=True)


async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Удаляет канал из списка рассылки по ID."""
    channels = storage.get_channels()

    if not context.args:
        if not channels:
            await update.message.reply_text("Каналів ще немає.")
            return
        lines = ["Щоб видалити канал, напиши:\n/removechannel <id>\n\nСписок каналів:"]
        for ch in channels:
            lines.append(f"• {ch['title']} — id: {ch['id']}")
        await update.message.reply_text("\n".join(lines))
        return

    try:
        chat_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID має бути числом. Приклад: /removechannel -1001234567890")
        return

    ok = storage.remove_channel(chat_id)
    if ok:
        await update.message.reply_text("✅ Канал видалено зі списку розсилки.")
    else:
        await update.message.reply_text("Канал з таким id не знайдено у списку.")


async def news_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Устанавливает фильтр по ключевым словам для новостей канала."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "Використання:\n"
            "/newsfilter <id_каналу> слово1, слово2, слово3\n"
            "/newsfilter <id_каналу> clear — прибрати фільтр\n\n"
            "ID каналу можна побачити в /channels."
        )
        return

    try:
        chat_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID має бути числом. Приклад: /newsfilter -1001234567890 війна")
        return

    rest = " ".join(context.args[1:])

    if rest.strip().lower() == "clear":
        ok = storage.set_channel_keywords(chat_id, [])
        if ok:
            await update.message.reply_text("✅ Фільтр прибрано — надсилатимуться всі новини.")
        else:
            await update.message.reply_text("Канал з таким id не знайдено.")
        return

    keywords = [w.strip().lower() for w in rest.split(",") if w.strip()]
    if not keywords:
        await update.message.reply_text("Не вдалося розпізнати ключові слова. Розділяй їх комою.")
        return

    ok = storage.set_channel_keywords(chat_id, keywords)
    if ok:
        await update.message.reply_text(
            f"✅ Фільтр встановлено: {', '.join(keywords)}\n"
            f"Надсилатимуться лише новини, де є хоча б одне з цих слів у заголовку."
        )
    else:
        await update.message.reply_text("Канал з таким id не знайдено.")


def _source_keyboard(source: dict) -> InlineKeyboardMarkup:
    status_label = "🟢 Увімкнено" if source.get("enabled", True) else "🔴 Вимкнено"
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(status_label, callback_data=f"srctoggle:{source['id']}"),
        InlineKeyboardButton("🗑 Видалити", callback_data=f"srcdel:{source['id']}"),
    ]])


async def _send_sources_list(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Отправляет список ВЛАСНИХ джерел новин цього адміна з кнопками управления в указанный чат
    (ізоляція: кожен адмін бачить і керує лише своїми джерелами)."""
    sources = storage.get_sources_for_admin(chat_id)
    if not sources:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "Джерел ще немає.\n\n"
                "Сайт (RSS): /addsource Назва https://посилання-на-rss\n"
                "Telegram-канал: /addtgsource"
            ),
        )
        return

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "📡 Твої джерела новин:\n\n"
            "➕ Додати сайт (RSS): /addsource Назва https://посилання-на-rss\n"
            "➕ Додати Telegram-канал: /addtgsource"
        ),
    )
    for s in sources:
        if s.get("type") == "telegram":
            label = f"📢 {s['name']} (Telegram-канал)"
        else:
            label = f"🌐 {s['name']}\n{s.get('url', '')}"
        await context.bot.send_message(chat_id=chat_id, text=label, reply_markup=_source_keyboard(s))


async def list_sources(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает список источников новостей с кнопками управления."""
    await _send_sources_list(context, update.effective_chat.id)


async def add_source(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Добавляет новый RSS-источник, прив'язаний до адміна, який його додає."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "Використання:\n/addsource Назва https://посилання-на-rss\n\n"
            "Приклад:\n/addsource Цензор.НЕТ https://censor.net.ua/includes/news_ukr.xml"
        )
        return

    url = context.args[-1]
    name = " ".join(context.args[:-1])

    if not url.startswith("http"):
        await update.message.reply_text("Останнім аргументом має бути посилання на RSS (починається з http).")
        return

    # Перевіримо, що посилання взагалі схоже на робочий RSS
    try:
        feed = await _fetch_feed(url)
        if not feed.entries:
            await update.message.reply_text(
                "⚠️ За цим посиланням не знайдено новин. Перевір, що це правильний RSS. "
                "Джерело всеодно буде додано, спробуй пізніше."
            )
    except Exception:
        pass

    admin_id = update.effective_user.id
    ok = storage.add_source(admin_id, name, url)
    if ok:
        await update.message.reply_text(f"✅ Джерело «{name}» додано.")
    else:
        await update.message.reply_text(f"У тебе вже є джерело з назвою «{name}». Обери іншу назву.")


async def add_telegram_source_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начинает процесс добавления Telegram-канала как источника новостей."""
    context.user_data["awaiting_source_forward"] = True
    await update.message.reply_text(
        "📢 Щоб додати Telegram-канал як джерело новин:\n\n"
        "1. Додай бота в цей канал (як адміністратора — так само, як для звичайних каналів)\n"
        "2. Перешли сюди (в особисті) будь-який пост із цього каналу\n\n"
        "Наступний пересланий пост я зареєструю саме як джерело новин."
    )


async def on_source_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатия кнопок управления источниками (тільки власними — ізоляція за admin_id)."""
    query = update.callback_query
    await query.answer()

    admin_id = query.from_user.id
    action, source_id_str = query.data.split(":", 1)
    source_id = int(source_id_str)

    if action == "srctoggle":
        current = next((s for s in storage.get_sources_for_admin(admin_id) if s["id"] == source_id), None)
        if not current:
            await query.edit_message_text("Джерело не знайдено, можливо вже видалено.")
            return
        storage.set_source_enabled(admin_id, source_id, not current.get("enabled", True))
        updated = next((s for s in storage.get_sources_for_admin(admin_id) if s["id"] == source_id), None)
        await query.edit_message_reply_markup(reply_markup=_source_keyboard(updated))

    elif action == "srcdel":
        name = next((s["name"] for s in storage.get_sources_for_admin(admin_id) if s["id"] == source_id), "джерело")
        ok = storage.remove_source(admin_id, source_id)
        if ok:
            await query.edit_message_text(f"🗑 Джерело «{name}» видалено.")
        else:
            await query.edit_message_text("Джерело вже видалено, не знайдено, або належить не тобі.")


async def _on_reader_album_ready(batches: list, caption_html, context_data: dict, ptb_context) -> None:
    """on_ready-колбек для reader_album_collector — викликається, коли Telegram
    перестав присилати нові частини альбому довше media_collector.DEBOUNCE_SECONDS.
    batches — майже завжди рівно один батч (Telegram сам не дає зібрати оригінальний
    альбом довше 10 елементів), але цикл на випадок гіпотетичного довшого альбому."""
    user_id = context_data["user_id"]
    author_name = context_data["author_name"]
    ts = context_data["ts"]
    target_channel_id = context_data["channel_id"]
    channel = next((c for c in storage.get_channels() if c["id"] == target_channel_id), None)

    for batch in batches:
        items = [{"type": it.kind, "file_id": it.file_id} for it in batch]
        entry = storage.add_submission(user_id, author_name, "album", items, caption_html, ts, target_channel_id,
                                        scam_suspected=_looks_like_scam(caption_html or ""))
        try:
            await ptb_context.bot.send_message(
                chat_id=user_id,
                text="✅ Дякуємо! Твою новину (альбом) надіслано модераторам на перевірку.\n"
                     "Якщо матеріал підійде — ми його опублікуємо.",
            )
        except Exception:
            pass
        await _notify_submission_owner(ptb_context, entry, channel, author_name, ts)


reader_album_collector = media_collector.MediaGroupCollector(
    name="reader_submissions", on_ready=_on_reader_album_ready,
)


async def _notify_submission_owner(context: ContextTypes.DEFAULT_TYPE, entry: dict, channel: dict, author_name: str, ts: str) -> None:
    """Сповіщає адміна-власника каналу про нову предложку (ізоляція — лише власника цього каналу)."""
    owner_admin_id = channel.get("added_by") if channel else None
    if not owner_admin_id:
        return

    type_labels = {"text": "📝 текст", "photo": "🖼 фото", "video": "🎥 відео", "location": "📍 локація", "album": "🖼 альбом"}
    notif_text = (
        f"🆕 Нова пропозиція для «{channel['title']}» від {author_name}\n"
        f"Тип: {type_labels.get(entry['type'], entry['type'])}\n"
        f"Час: {ts}"
    )
    keyboard = None
    if WEBAPP_URL and WEBAPP_URL != "https://example.com":
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🖥 Відкрити панель", web_app=WebAppInfo(url=WEBAPP_URL))
        ]])
    try:
        await context.bot.send_message(chat_id=owner_admin_id, text=notif_text, reply_markup=keyboard)
    except Exception as e:
        logger.warning(f"Не вдалося надіслати push-сповіщення адміну {owner_admin_id}: {e}")


_notified_pending_owners: dict[int, set] = {}  # item_id -> set(admin_id), щоб не слати дубль-сповіщення
_pending_digest: dict[int, list] = {}  # owner_id -> [{"id","title","source_name"}], буфер для дайджесту
DIGEST_DELAY_SECONDS = 300  # 5 хв — вікно накопичення перед відправкою одного дайджесту (п.1 ТЗ)


async def pin_queue_item_notice(bot, item: dict) -> None:
    """Службове повідомлення-пін у редакційному чаті власника каналу (п.2.3 ТЗ) —
    сигналізує редакції, що новина схвалена і чекає своєї черги публікації.
    Шукає чат категорії "editorial_chat" серед джерел власника ПЕРШОГО з
    цільових каналів запису; якщо такого чату нема (чи бот там не адмін) —
    просто нічого не робить, виклик у app.py й так обгорнутий у try/except."""
    channel_ids = item.get("channel_ids") or []
    if not channel_ids:
        return
    channel = next((c for c in storage.get_channels() if c["id"] == channel_ids[0]), None)
    owner_id = channel.get("added_by") if channel else None
    if not owner_id:
        return
    editorial_chat_id = next(
        (s.get("chat_id") for s in storage.get_sources_for_admin(owner_id)
         if s.get("type") == "telegram" and s.get("category") == "editorial_chat" and s.get("chat_id")),
        None,
    )
    if not editorial_chat_id:
        return
    title = (item.get("title") or "Новина")[:150]
    msg = await bot.send_message(
        chat_id=editorial_chat_id,
        text=f"✅ Схвалено: {title}\n\nЧекає своєї черги публікації.",
    )
    await bot.pin_chat_message(chat_id=editorial_chat_id, message_id=msg.message_id, disable_notification=True)
    storage.update_queue_item(item["id"], pinned_message_id=msg.message_id)


async def _notify_queue_owners_pending(context: ContextTypes.DEFAULT_TYPE, queue_item: dict) -> None:
    """Замість миттєвого сповіщення на КОЖНУ новину — кладе новину в буфер власника і
    (якщо для нього ще не заплановано найближчий дайджест) ставить одноразову job через
    DIGEST_DELAY_SECONDS. Усі новини, що прийдуть за цей час, підуть ОДНИМ повідомленням —
    п.1-2 ТЗ (антиспам)."""
    channel_ids = set(queue_item.get("channel_ids", []))
    if not channel_ids:
        return
    owners = {
        ch.get("added_by") for ch in storage.get_channels()
        if ch["id"] in channel_ids and ch.get("added_by")
    }
    already = _notified_pending_owners.setdefault(queue_item["id"], set())
    title_preview = (queue_item.get("title") or "")[:120]
    for owner in owners:
        if owner in already:
            continue
        already.add(owner)
        _pending_digest.setdefault(owner, []).append({
            "id": queue_item["id"], "title": title_preview, "source_name": queue_item.get("source_name", ""),
        })
        job_name = f"digest_{owner}"
        if not context.job_queue.get_jobs_by_name(job_name):
            context.job_queue.run_once(_flush_owner_digest, when=DIGEST_DELAY_SECONDS, data={"owner_id": owner}, name=job_name)


async def _flush_owner_digest(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Спрацьовує раз на власника через DIGEST_DELAY_SECONDS після ПЕРШОЇ невідправленої
    новини — надсилає ВСЕ, що накопичилось у буфері за цей час, одним компактним
    повідомленням з однією кнопкою "Відкрити панель"."""
    owner = context.job.data["owner_id"]
    items = _pending_digest.pop(owner, [])
    if not items:
        return
    if len(items) == 1:
        it = items[0]
        notif_text = (
            f"🆕 Нова новина з «{it['source_name']}» чекає схвалення\n"
            f"{it['title']}\n\n"
            f"Відкрий панель → «Джерела» → «Черга публікації», щоб схвалити, відредагувати або видалити."
        )
    else:
        lines = "\n".join(f"• {it['title']} ({it['source_name']})" for it in items[:10])
        more = f"\n…і ще {len(items) - 10}" if len(items) > 10 else ""
        notif_text = (
            f"🆕 {len(items)} нових новин чекають схвалення:\n\n{lines}{more}\n\n"
            f"Відкрий панель → «Джерела» → «Черга публікації», щоб опрацювати всі одразу."
        )
    keyboard = None
    if WEBAPP_URL and WEBAPP_URL != "https://example.com":
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🖥 Відкрити панель", web_app=WebAppInfo(url=WEBAPP_URL))
        ]])
    try:
        await context.bot.send_message(chat_id=owner, text=notif_text, reply_markup=keyboard)
    except Exception as e:
        logger.warning(f"Не вдалося надіслати дайджест-сповіщення адміну {owner}: {e}")
        storage.log_error(f"Дайджест-сповіщення адміну {owner}: {e}")

    try:
        push_title = "🆕 Нова новина в черзі" if len(items) == 1 else f"🆕 {len(items)} новин у черзі"
        push_body = items[0]["title"] if len(items) == 1 else "; ".join(it["title"] for it in items[:3])
        push_module.send_push_to_admin(owner, push_title, push_body[:150], url="/", tag="queue-pending")
    except Exception as e:
        logger.warning(f"[PUSH] Не вдалося розіслати push про новий елемент черги адміну {owner}: {e}")


async def on_reader_submission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Приймає текст/фото/відео/локацію (в т.ч. альбоми з кількох фото/відео) від читачів
    у особисті боту й кладе у чергу «предложки».
    Прив'язує новину до каналу, з якого читач прийшов (deep-link /start channel_<id>),
    і сповіщає лише адміна-власника цього каналу — ізоляція даних між різними каналами/адмінами."""
    msg = update.message
    user = update.effective_user
    if not msg or not user:
        return

    # Якщо цей користувач сам є власником хоча б одного каналу — це адмін, а не читач,
    # його повідомлення в особисті боту не повинні перетворюватись на предложку.
    if storage.get_channels_for_admin(user.id):
        return

    target_channel_id = storage.get_active_channel(user.id)
    if target_channel_id is None:
        await msg.reply_text(
            "Щоб надіслати новину, спершу перейди за посилання каналу "
            "(кнопка «Надіслати новину» в потрібному каналі) — так бот зрозуміє, "
            "для якого каналу призначений матеріал."
        )
        return

    if storage.is_channel_banned(target_channel_id):
        await msg.reply_text("⛔ Наразі прийом новин для цього каналу тимчасово призупинено.")
        return

    author_name = user.full_name or user.username or str(user.id)
    ts = datetime.now().strftime("%d.%m %H:%M")

    # --- Альбом (кілька фото/відео в одному повідомленні) ---
    if msg.media_group_id and (msg.photo or msg.video):
        kind = "photo" if msg.photo else "video"
        file_id = msg.photo[-1].file_id if msg.photo else msg.video.file_id
        reader_album_collector.add(
            job_queue=context.job_queue,
            group_id=msg.media_group_id,
            message_id=msg.message_id,
            kind=kind,
            file_id=file_id,
            caption_html=msg.caption,
            context_data={
                "user_id": user.id, "author_name": author_name,
                "channel_id": target_channel_id, "ts": ts,
            },
        )
        return

    if msg.photo:
        entry = storage.add_submission(user.id, author_name, "photo", msg.photo[-1].file_id, msg.caption, ts, target_channel_id,
                                        scam_suspected=_looks_like_scam(msg.caption or ""))
    elif msg.video:
        entry = storage.add_submission(user.id, author_name, "video", msg.video.file_id, msg.caption, ts, target_channel_id,
                                        scam_suspected=_looks_like_scam(msg.caption or ""))
    elif msg.location:
        loc = msg.location
        entry = storage.add_submission(user.id, author_name, "location", f"{loc.latitude},{loc.longitude}", None, ts, target_channel_id)
    elif msg.text:
        entry = storage.add_submission(user.id, author_name, "text", msg.text, None, ts, target_channel_id,
                                        scam_suspected=_looks_like_scam(msg.text or ""))
    else:
        return

    await msg.reply_text(
        "✅ Дякуємо! Твою новину надіслано модераторам на перевірку.\n"
        "Якщо матеріал підійде — ми його опублікуємо."
    )

    channel = next((c for c in storage.get_channels() if c["id"] == target_channel_id), None)
    await _notify_submission_owner(context, entry, channel, author_name, ts)


async def on_forwarded_from_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Если пересылают боту сообщение из канала — регистрируем канал."""
    msg = update.message
    if not msg or not msg.forward_origin:
        return

    origin = msg.forward_origin
    chat = getattr(origin, "chat", None)
    if chat is None:
        await msg.reply_text(
            "Не вдалося визначити канал. Переконайся, що переслав пост саме з каналу."
        )
        return

    try:
        member = await context.bot.get_chat_member(chat.id, context.bot.id)
    except Exception:
        await msg.reply_text(
            "Не бачу цей канал. Спочатку додай бота в канал як адміністратора."
        )
        return

    if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
        await msg.reply_text("Бот доданий у канал, але не є адміністратором — додай права адміна.")
        return

    if context.user_data.get("awaiting_source_forward"):
        context.user_data["awaiting_source_forward"] = False
        admin_id = update.effective_user.id
        ok = storage.add_telegram_source(admin_id, chat.title or str(chat.id), chat.id)
        # Якщо цей канал випадково потрапив і в список розсилки (наприклад, автоматично
        # при додаванні бота) — прибираємо його звідти, щоб джерело і отримувач не плуталися.
        storage.remove_channel(chat.id)
        if ok:
            await msg.reply_text(f"✅ Канал «{chat.title}» додано як джерело новин.")
        else:
            await msg.reply_text(f"Канал «{chat.title}» вже є серед твоїх джерел новин.")
        return

    is_new = storage.add_channel(chat.id, chat.title or str(chat.id))
    if is_new:
        await msg.reply_text(f"✅ Канал «{chat.title}» додано до списку розсилки.")
    else:
        await msg.reply_text(f"Канал «{chat.title}» вже є у списку.")


def _normalize_title(title: str) -> str:
    """Приводит заголовок к виду для сравнения: нижний регистр, без пунктуации."""
    title = title.lower()
    title = re.sub(r"[^\w\sа-яіїєґ]", " ", title, flags=re.UNICODE)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def _is_similar_title(title: str, others: list, threshold: float = 0.72) -> bool:
    """Проверяет, похож ли заголовок на один из уже отправленных (та же новость с другого джерела)."""
    for other in others:
        ratio = difflib.SequenceMatcher(None, title, other).ratio()
        if ratio >= threshold:
            return True
    return False


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
_gemini_client = None
if not _GEMINI_AVAILABLE:
    logger.warning("Пакет google-genai не встановлено — ІІ-перевірка дублів (_llm_is_duplicate) вимкнена, працює лише difflib.")
elif not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY не задано — ІІ-перевірка дублів (_llm_is_duplicate) вимкнена, працює лише difflib.")
else:
    _gemini_client = gemini_genai.Client(api_key=GEMINI_API_KEY)

GEMINI_MODEL = "gemini-flash-lite-latest"  # "lite"-модель — flagship-алиас (gemini-flash-latest)
# впирався в безкоштовну квоту всього 20 запитів/добу (RESOURCE_EXHAUSTED на реальному
# трафіку буквально за годину). Легша lite-модель на безкоштовному тарифі має значно
# щедрішу квоту — саме те, що треба для короткої задачі перевірки дублів/рерайту.
# "-latest" — той самий підхід, що й раніше: не прив'язуємось до конкретної версії.


async def _llm_is_duplicate(new_title: str, candidate_titles: list) -> bool:
    """Додаткова (поверх швидкого текстового порівняння difflib) перевірка смислових
    дублів через ІІ (Gemini — безкоштовний тариф, на відміну від Anthropic, який тут
    був раніше). Працює ЛИШЕ якщо задано GEMINI_API_KEY і встановлено пакет google-genai;
    інакше (чи при будь-якій помилці виклику) вважає, що дубля НЕМАЄ — щоб збій ІІ
    ніколи не коштував втраченої реальної новини."""
    if _gemini_client is None or not candidate_titles:
        return False
    try:
        candidates_list = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(candidate_titles[-15:]))
        prompt = (
            f"Заголовок нової новини:\n«{new_title}»\n\n"
            f"Список нещодавніх заголовків:\n{candidates_list}\n\n"
            "Чи описує нова новина ТУ Ж САМУ подію/тему, що й хоча б один заголовок зі "
            "списку (навіть якщо сформульовано інакше)? Відповідай ЛИШЕ одним словом: "
            "\"так\" або \"ні\"."
        )
        resp = await _gemini_client.aio.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        answer = (resp.text or "").strip().lower()
        return answer.startswith("так")
    except Exception as e:
        logger.warning(f"Не вдалося виконати ІІ-перевірку дублів: {e}")
        return False


def _save_media_to_queue_disk(item_id: int, media_items: list) -> list:
    """Зберігає вже завантажені байти медіа на диск (storage.QUEUE_MEDIA_DIR), повертає
    список шляхів. Новина в черзі може чекати своєї черги до 2 годин — за цей час
    тимчасові посилання джерела (особливо CDN Telegram) можуть протухнути, тож
    зберігаємо самі байти, а не URL."""
    if not media_items:
        return []
    os.makedirs(storage.QUEUE_MEDIA_DIR, exist_ok=True)
    paths = []
    for i, item in enumerate(media_items):
        ext = "mp4" if item["type"] == "video" else "jpg"
        path = os.path.join(storage.QUEUE_MEDIA_DIR, f"{item_id}_{i}.{ext}")
        with open(path, "wb") as f:
            f.write(item["bytes"])
        paths.append(path)
    return paths


def _load_media_from_queue_disk(media_paths: list) -> list:
    """Зворотна дія до _save_media_to_queue_disk — читає збережені файли назад у байти
    перед публікацією. Пропускає файли, які не вдалося прочитати (наприклад, якщо
    хтось прибрав їх вручну), а не падає з помилкою."""
    items = []
    for path in media_paths or []:
        try:
            with open(path, "rb") as f:
                data = f.read()
            items.append({"type": "video" if path.lower().endswith(".mp4") else "photo", "bytes": data})
        except Exception as e:
            logger.warning(f"Не вдалося прочитати медіа черги {path}: {e}")
    return items


def _delete_queue_media_files(media_paths: list) -> None:
    for path in media_paths or []:
        try:
            os.remove(path)
        except Exception:
            pass


async def _get_latest_single_news(admin_id: int | None, keywords: list) -> tuple | None:
    """Возвращает одну самую свежую новость (source_name, title, link) серед джерел
    ЦЬОГО admin_id, с учётом фильтра ключевых слов. None, если подходящей новости не нашлось."""
    candidates = []
    sources = storage.get_sources_for_admin(admin_id) if admin_id is not None else []
    for src in sources:
        if not src.get("enabled", True) or src.get("type", "rss") != "rss":
            continue
        source_name, feed_url = src["name"], src["url"]
        try:
            feed = await _fetch_feed(feed_url)
        except Exception:
            continue
        for entry in feed.entries[:10]:
            title_lower = entry.title.lower()
            if keywords and not any(kw in title_lower for kw in keywords):
                continue
            published = entry.get("published_parsed")
            candidates.append((published, source_name, entry.title, entry.link))

    if not candidates:
        return None

    # Сортуємо за датою публікації (найновіша перша); якщо дати немає — в кінець
    candidates.sort(key=lambda c: c[0] or (), reverse=True)
    _published, source_name, title, link = candidates[0]
    return source_name, title, link


def _strip_html(raw: str) -> str:
    """Убирає HTML-теги з тексту RSS-опису, залишаючи чистий текст."""
    text = re.sub(r"<[^>]+>", "", raw or "")
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# Реальні ліміти Telegram (НЕ для обрізки тексту — для рішення "влазить підписом
# чи треба окремим повідомленням", щоб текст новини НІКОЛИ не обрізався):
# - підпис до фото/альбому: 1024 символи
# - звичайне текстове повідомлення: 4096 символів
TELEGRAM_CAPTION_LIMIT = 1024
TELEGRAM_TEXT_LIMIT = 4096


def _smart_truncate(text: str, limit: int) -> str:
    """Обрізає текст АКУРАТНО — по завершенню речення (. ! ? …), а не посеред слова чи
    думки. Використовується ЛИШЕ як крайній запобіжник (текст довший за 4096 символів
    навіть без картинки — вкрай рідкісний випадок), а не для звичайної обрізки постів."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    best = -1
    for punct in (".", "!", "?", "…"):
        pos = cut.rfind(punct)
        if pos > best:
            best = pos
    if best >= limit * 0.4:  # межа речення знайдена не занадто рано — є сенс зупинитись саме тут
        return cut[:best + 1].strip()
    return cut.rsplit(" ", 1)[0].strip() + "…"


def _extract_entry_image(entry) -> str | None:
    """Шукає картинку у RSS-записі: media_thumbnail, media_content, enclosures, або <img> у описі."""
    for key in ("media_thumbnail", "media_content"):
        media = getattr(entry, key, None)
        if media:
            url = media[0].get("url")
            if url:
                return url
    for enc in getattr(entry, "enclosures", []) or []:
        if enc.get("type", "").startswith("image/") and enc.get("href"):
            return enc["href"]
    summary_html = getattr(entry, "summary", "") or ""
    match = re.search(r'<img[^>]+src="([^"]+)"', summary_html)
    if match:
        return match.group(1)
    return None


# Теги, які Telegram розуміє у HTML-режимі парсингу тексту — все інше (span, div-класи
# кастомних емодзі тощо) при конвертації просто "розгортається" без обгортки.
_TG_INLINE_TAGS = {
    "b": "b", "strong": "b",
    "i": "i", "em": "i",
    "u": "u", "ins": "u",
    "s": "s", "strike": "s", "del": "s",
}

# Голі посилання/@згадки прямо в тексті (не обов'язково обгорнуті в <a>) — прибираємо
# скрізь по тексту, а не тільки в кінці посту.
_BARE_LINK_RE = re.compile(r"https?://\S+|(?:(?<=\s)|^)(?:t\.me|telegram\.me)/\S+", re.IGNORECASE)
_MENTION_RE = re.compile(r"(?<!\w)@[A-Za-z][A-Za-z0-9_]{2,31}\b")


def _clean_plain_fragment(s: str) -> str:
    """Прибирає з фрагмента звичайного тексту голі посилання (http/https, t.me/telegram.me)
    та @згадки — навіть якщо вони не обгорнуті в <a>, а просто вписані текстом."""
    s = _BARE_LINK_RE.sub("", s)
    s = _MENTION_RE.sub("", s)
    s = re.sub(r"[ \t]{2,}", " ", s)  # прибираємо подвійні пробіли, що лишились після вирізання
    return s


def _tg_html_from_nodes(nodes) -> str:
    """Рекурсивно конвертує список DOM-вузлів (BeautifulSoup) у Telegram-сумісну HTML-
    розмітку: зберігає <b>/<i>/<u>/<s> і переноси рядків (<br>, <div>, <p>) — замість того
    щоб просто вирізати весь HTML і втрачати форматування джерела. АЛЕ: жодні чужі
    гіперпосилання не переносяться (донор не повинен тягнути трафік на себе) — <a> завжди
    розгортається без href, а якщо власний текст посилання сам по собі є @згадкою чи
    голим лінком (тобто без нього немає сенсу) — прибирається повністю. Кастомні/преміум
    емодзі (<tg-emoji>) теж прибираються, лишається тільки звичайний emoji-фолбек усередині."""
    parts = []

    def walk(node) -> None:
        if isinstance(node, (NavigableString, str)):
            parts.append(html_lib.escape(_clean_plain_fragment(str(node))))
            return
        tag_name = getattr(node, "name", None)
        if tag_name == "br":
            parts.append("\n")
            return
        if tag_name == "tg-emoji":
            for child in node.children:  # прибираємо тег, лишаємо тільки фолбек-emoji усередині
                walk(child)
            return
        if tag_name == "a":
            inner_text = node.get_text().strip()
            href = node.get("href", "")
            if (
                re.fullmatch(r"@[A-Za-z][A-Za-z0-9_]{2,31}", inner_text)
                or _BARE_LINK_RE.fullmatch(inner_text or "")
                or "t.me/" in href.lower() or "telegram.me/" in href.lower()
            ):
                return  # чисте посилання/mention без цінного тексту — прибираємо повністю
            for child in node.children:  # лишаємо текст, але БЕЗ гіперпосилання (не тягнемо чужий трафік)
                walk(child)
            return
        if tag_name in _TG_INLINE_TAGS:
            tg_tag = _TG_INLINE_TAGS[tag_name]
            parts.append(f"<{tg_tag}>")
            for child in node.children:
                walk(child)
            parts.append(f"</{tg_tag}>")
            return
        if tag_name in ("div", "p"):
            for child in node.children:
                walk(child)
            parts.append("\n\n")  # блочні елементи — окремі абзаци (видимий пропуск між ними в
            # Telegram), а не просто перенос рядка впритул — інакше багатоабзацні RSS-описи
            # зливались в одну суцільну "стіну тексту" без жодного візуального поділу
            return
        for child in getattr(node, "children", []):
            walk(child)

    for node in nodes:
        walk(node)

    text = "".join(parts)
    text = re.sub(r"\n{3,}", "\n\n", text)  # прибираємо зайві порожні рядки
    return text.strip()


_CTA_PHRASES = (
    "надіслати новину", "написати нам", "підписатися", "підписатись",
    "подписаться", "написати новину", "наша пошта", "зв'язок з редакцією",
    "зв'язок з нами", "реклама", "співпраця",
)
_CTA_TAIL_RE = re.compile(
    r"\s*(?:" + "|".join(re.escape(p) for p in _CTA_PHRASES) + r")\s*$",
    re.IGNORECASE,
)


def _strip_trailing_cta_phrase(text: str) -> str:
    """Якщо рядок закінчується типовою CTA-фразою типу "Надіслати новину" — прибирає
    її, навіть якщо вона приклеєна впритул до основного тексту без розриву рядка."""
    return _CTA_TAIL_RE.sub("", text)


def _is_junk_tail_node(node) -> bool:
    """Перевіряє ОДИН DOM-вузол наприкінці посту: чи виглядає він як частина чужого
    підпису-приманки — @mention-посилання, ВЕЛИКИЙ CTA-текст на кшталт "ПІДПИСАТИСЯ",
    типова фраза-заклик, чи будь-яке коротке трейлінг-посилання на сторонній ресурс."""
    if isinstance(node, NavigableString):
        p = str(node).strip()
        if not p:
            return True
        if len(p) > 60:
            return False
        low = p.lower().rstrip(" :.-—")
        if low in _CTA_PHRASES:
            return True
        if re.fullmatch(r"@\w+", p) or "t.me/" in p.lower() or re.fullmatch(r"https?://\S+", p):
            return True
        if _looks_like_link_bar(p):
            return True
        if p == p.upper() and len(p) >= 4 and re.search(r"[А-ЯІЇЄA-Z]", p):
            return True
        return False

    tag = getattr(node, "name", None)
    if tag == "br":
        return True
    if tag == "a":
        return True  # трейлінг-посилання наприкінці посту — майже завжди чуже брендування
    if tag in _TG_INLINE_TAGS:
        inner = node.get_text().strip()
        if not inner:
            return True
        low = inner.lower().rstrip(" :.-—")
        if low in _CTA_PHRASES:
            return True
        if inner == inner.upper() and len(inner) >= 4 and re.search(r"[А-ЯІЇЄA-Z]", inner):
            return True
    return False


def _strip_trailing_junk_nodes(nodes: list) -> list:
    """Прибирає з кінця списку DOM-вузлів усе, що виглядає як чужий підпис/CTA — НАВІТЬ
    якщо кілька таких шматків приклеєні один до одного БЕЗ розриву рядка чи пробілу між
    ними (типова ситуація: "Надіслати новину" + @mention-посилання + ВЕЛИКА кнопка,
    злиплі в один рядок — рядковий фільтр такого не ловить, а вузловий — ловить)."""
    nodes = list(nodes)
    trimmed = 0
    while nodes and trimmed < 8 and _is_junk_tail_node(nodes[-1]):
        nodes.pop()
        trimmed += 1
    # Якщо останній вузол, що лишився, — звичайний текст, який ЗАКІНЧУЄТЬСЯ CTA-фразою
    # (приклеєною впритул до реального речення без жодного розділювача) — обрізаємо суфікс.
    if nodes and isinstance(nodes[-1], NavigableString):
        cleaned = _strip_trailing_cta_phrase(str(nodes[-1]))
        if cleaned != str(nodes[-1]):
            nodes[-1] = cleaned
    return nodes


def _split_title_and_body_html(text_el) -> tuple[str, str]:
    """Розбиває DOM-вузол тексту посту на (title_plain, body_html):
    title — перший рядок ЗВИЧАЙНИМ текстом (без тегів — для нашого власного жирного
    заголовка й дедуплікації), body_html — решта тексту у вигляді Telegram-сумісної
    HTML-розмітки зі збереженим форматуванням (жирний/курсив/підкреслення/посилання).
    Чужий підпис-приманка джерела спершу зачищається на рівні DOM-вузлів (навіть без
    розриву рядка), і лише потім текст ділиться на заголовок і тіло."""
    children = _strip_trailing_junk_nodes(list(text_el.children))
    title_nodes, body_nodes = [], []
    split_done = False
    skip_leading_break = False

    for node in children:
        if not split_done:
            if getattr(node, "name", None) == "br":
                split_done = True
                skip_leading_break = True
                continue
            title_nodes.append(node)
        else:
            if skip_leading_break and getattr(node, "name", None) == "br":
                continue  # пропускаємо порожній рядок одразу після заголовка
            skip_leading_break = False
            body_nodes.append(node)

    title_plain = "".join(
        n.get_text() if hasattr(n, "get_text") else str(n) for n in title_nodes
    ).strip()
    body_html = _tg_html_from_nodes(body_nodes)
    return title_plain, body_html


def _html_summary_to_tg_html(raw_html: str) -> str:
    """Те саме, що _tg_html_from_nodes, але для RSS <description> — сирого HTML-рядка."""
    soup = BeautifulSoup(raw_html or "", "html.parser")
    return _tg_html_from_nodes(list(soup.children))


def _plain_line(line: str) -> str:
    """Прибирає HTML-теги з рядка — лише для перевірки паттерну (сам рядок при видаленні
    беремо оригінальний, з тегами, щоб не зіпсувати форматування, що лишається)."""
    return re.sub(r"<[^>]+>", "", line).strip()


_SOCIAL_PLATFORM_RE = re.compile(
    r"\b(tik\s?tok|instagram|інстаграм|инстаграм|youtube|ютуб|facebook|фейсбук|twitter|x\.com)\b",
    re.IGNORECASE,
)


def _looks_like_link_bar(plain_line: str) -> bool:
    """Розпізнає рядок-«банер» на кшталт "Сайт | Facebook | YouTube | TikTok" —
    кілька коротких пунктів через "|" (типова підпис-приманка каналу-донора), АБО
    короткий рядок, що прямо згадує назву соцмережі (TikTok/Instagram/YouTube/
    Facebook/Twitter/X) — навіть без "|"."""
    if len(plain_line) <= 80 and _SOCIAL_PLATFORM_RE.search(plain_line):
        return True
    if "|" not in plain_line:
        return False
    parts = [p.strip() for p in plain_line.split("|")]
    return len(parts) >= 2 and all(0 < len(p) <= 20 for p in parts)


def _remove_social_link_bar_lines(text: str) -> str:
    """Прибирає з ТЕКСТУ ЦІЛКОМ будь-які рядки-«банери» з соцмережами — на відміну від
    _strip_source_signature (яка чистить лише хвіст), ця перевірка проходить по ВСІХ
    рядках, бо джерело іноді вставляє такий блок не тільки в самому кінці посту."""
    lines = [ln for ln in text.split("\n") if not _looks_like_link_bar(_plain_line(ln))]
    return "\n".join(lines)


def _strip_source_signature(text: str) -> str:
    """Прибирає з (можливо HTML-розміченого) тексту чужі підписи каналу-джерела —
    зазвичай це останні кілька коротких рядків типу "Надіслати новину / @bot / ПІДПИСАТИСЯ"
    або лінк-бар "Сайт | Facebook | YouTube | TikTok". Розпізнавання йде по чистому тексту
    рядка (без тегів), а видаляється — оригінальний рядок (зі збереженим форматуванням)."""
    text = _remove_social_link_bar_lines(text)
    lines = text.split("\n")

    def is_signature_line(raw_line: str) -> bool:
        p = _plain_line(raw_line)
        if not p:
            return True
        return (
            len(p) <= 60 and (
                re.fullmatch(r"@\w+", p)
                or "t.me/" in p.lower()
                or re.fullmatch(r"https?://\S+", p)
                or re.fullmatch(r"[\W\d]*", p)  # рядок тільки з символів/емодзі-роздільників
                or _looks_like_link_bar(p)
            )
        )

    # Крок 1: знімаємо однорядкові маркери з самого кінця
    while lines:
        if not lines[-1].strip():
            lines.pop()
            continue
        if is_signature_line(lines[-1]):
            lines.pop()
            continue
        break

    # Крок 2: якщо серед останніх кількох КОРОТКИХ рядків є явний маркер підписки/CTA
    # (@mention, посилання, лінк-бар, або рядок ВЕЛИКИМИ ЛІТЕРАМИ на кшталт "ПІДПИСАТИСЯ") —
    # знімаємо весь цей хвіст одним блоком, навіть якщо поруч є "нейтральні" короткі
    # рядки типу "Надіслати новину", які самі по собі не схожі на посилання.
    tail_start = len(lines)
    has_marker = False
    idx = len(lines) - 1
    checked = 0
    while idx >= 0 and checked < 4:
        p = _plain_line(lines[idx])
        if not p:
            idx -= 1
            continue
        if len(p) > 60:
            break
        checked += 1
        is_marker = (
            re.fullmatch(r"@\w+", p)
            or "t.me/" in p.lower()
            or re.fullmatch(r"https?://\S+", p)
            or _looks_like_link_bar(p)
            or (len(p) >= 6 and p == p.upper() and re.search(r"[А-ЯІЇЄA-Z]", p))
        )
        if is_marker:
            has_marker = True
        tail_start = idx
        idx -= 1

    if has_marker:
        lines = lines[:tail_start]

    return "\n".join(lines).strip()


_AD_MARKERS_RE = re.compile(
    r"(#реклам\w*|#ad\b|#promo\b|\berid\s*[:=]|на\s+правах\s+реклами|"
    r"рекламн(?:а|ий|і|ого)\s+(?:допис\w*|публікаці\w*|матеріал\w*|пост\w*)|"
    r"партнерськ(?:ий|а|ого)\s+матеріал\w*|рекламодав\w*|замовн(?:ий|а)\s+матеріал\w*)",
    re.IGNORECASE,
)


_URL_RE = re.compile(r"https?://[^\s<>\"]+", re.IGNORECASE)

_SCAM_MARKERS_RE = re.compile(
    r"(безкоштовн\w*\s+(?:біткоін\w*|bitcoin|крипто\w*|btc|usdt)|"
    r"подво(?:їти|їш|ю)\s+(?:свої|свій)?\s*(?:кошти|btc|крипто\w*)|"
    r"claim\s+your\s+(?:reward|airdrop|bonus)|"
    r"airdrop\s+(?:token|crypto)|"
    r"верифікуй(?:те)?\s+(?:гаманець|wallet|акаунт)|"
    r"підтвердіть\s+(?:гаманець|wallet|дан(?:і|их)|акаунт)\s+(?:протягом|негайно|зараз)|"
    r"ваш\s+акаунт\s+(?:буде\s+)?заблокован\w*|"
    r"термінов\w*\s+підтвердіть|"
    r"ви\s+(?:виграли|переможець|переможниця)|"
    r"you\s+(?:have\s+)?won|congratulations.{0,20}winner|"
    r"інвестиц\w*\s+з\s+гарантован\w*\s+прибутк\w*|"
    r"подвои(?:ть|шь)\s+(?:свои|свой)?\s*(?:деньги|btc|крипто\w*))",
    re.IGNORECASE,
)


def _looks_like_scam(text: str) -> bool:
    """Консервативна евристика (без зовнішніх API/репутаційних сервісів):
    спрацьовує ЛИШЕ коли в тексті Є посилання І поруч типовий фішинг/крипто-
    скам маркер ("верифікуй гаманець", "ви виграли", обіцянки подвоєння тощо).
    Саме посилання без таких маркерів НЕ вважається підозрілим — інакше
    зрізало б звичайні новини, які просто містять посилання на джерело."""
    plain = _strip_html(text or "")
    if not _URL_RE.search(plain):
        return False
    return bool(_SCAM_MARKERS_RE.search(plain))


def _looks_like_ad(text: str) -> bool:
    """Розпізнає ЛИШЕ явне обов'язкове маркування рекламного посту (#реклама,
    "На правах реклами", "рекламна публікація", erid і т.п.) — навмисно не чіпає
    звичайні згадки знижок/промокодів у новинах, щоб не зрізати легітимний контент."""
    plain = re.sub(r"<[^>]+>", " ", text or "")
    return bool(_AD_MARKERS_RE.search(plain))


# Свій шрифт у папці проекту — ПЕРШИЙ пріоритет. На сервері (наприклад, Render зі
# стандартним Python-білдпаком) системних шрифтів найчастіше НЕМАЄ взагалі, тому
# Pillow тихо падав на вбудований шрифт без кирилиці — звідси квадратики замість
# тексту водяного знаку. Системні шляхи лишені як запасний варіант, якщо раптом є.
_BUNDLED_FONT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts", "DejaVuSans-Bold.ttf")
_WATERMARK_FONT_PATHS = [
    _BUNDLED_FONT_PATH,
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]


def _load_watermark_font(size: int):
    """Спершу пробує шрифт, який лежить прямо в проекті (fonts/DejaVuSans-Bold.ttf —
    підтримує кирилицю), потім — системні шляхи як запасний варіант. Якщо взагалі
    нічого не знайдено — падає на стандартний шрифт Pillow (кирилицю не покаже,
    але хоча б не впаде з помилкою)."""
    for path in _WATERMARK_FONT_PATHS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    logger.warning(
        "Не знайдено жодного TTF-шрифта для водяного знаку (навіть у fonts/) — "
        "кирилиця в водяному знаку показана НЕ буде."
    )
    try:
        return ImageFont.load_default(size=size)  # Pillow 10+
    except TypeError:
        return ImageFont.load_default()  # старіші версії Pillow — без параметра size


WATERMARK_IMAGE_OPACITY = 0.5  # запасне значення, якщо в каналу ще нема власних налаштувань
WATERMARK_IMAGE_WIDTH_RATIO = 0.4  # ширина водяного знаку — ~40% ширини фото/відео
WATERMARK_MARGIN_RATIO = 0.04  # відступ від краю для некутових позицій


def _watermark_xy(base_w: int, base_h: int, wm_w: int, wm_h: int, position: str) -> tuple[int, int]:
    """Координати верхнього лівого кута знака залежно від обраної позиції (п.2.4 ТЗ)."""
    margin_x = int(base_w * WATERMARK_MARGIN_RATIO)
    margin_y = int(base_h * WATERMARK_MARGIN_RATIO)
    if position == "top-left":
        return margin_x, margin_y
    if position == "top-right":
        return base_w - wm_w - margin_x, margin_y
    if position == "bottom-left":
        return margin_x, base_h - wm_h - margin_y
    if position == "bottom-right":
        return base_w - wm_w - margin_x, base_h - wm_h - margin_y
    return (base_w - wm_w) // 2, (base_h - wm_h) // 2  # center (за замовчуванням)


def _add_image_watermark_to_photo(image_bytes: bytes, watermark_path: str,
                                   opacity: float = WATERMARK_IMAGE_OPACITY,
                                   positions: list | None = None, scale: float = WATERMARK_IMAGE_WIDTH_RATIO) -> bytes:
    """Накладає КАСТОМНИЙ водяний знак-картинку (той, що адмін завантажив для каналу)
    з обраними прозорістю, МАСШТАБОМ і списком позицій (п.2.2-2.3/3.1 ТЗ — мультивибір
    точок, знак ставиться в КОЖНУ обрану). Якщо щось пішло не так — повертає оригінал
    без водяного знаку (краще так, ніж не надіслати фото взагалі)."""
    if not _PIL_AVAILABLE:
        return image_bytes
    positions = positions or ["center"]
    try:
        base = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        wm_orig = Image.open(watermark_path).convert("RGBA")

        target_w = max(1, int(base.width * scale))
        ratio = target_w / wm_orig.width
        wm = wm_orig.resize((target_w, max(1, int(wm_orig.height * ratio))), Image.LANCZOS)

        alpha = wm.split()[3].point(lambda a: int(a * opacity))
        wm.putalpha(alpha)

        for position in positions:
            x, y = _watermark_xy(base.width, base.height, wm.width, wm.height, position)
            base.alpha_composite(wm, (x, y))

        result = base.convert("RGB")
        buf = io.BytesIO()
        result.save(buf, format="JPEG", quality=90)
        return buf.getvalue()
    except Exception as e:
        logger.warning(f"Не вдалося накласти кастомний водяний знак на фото: {e}")
        return image_bytes


async def _add_image_watermark_to_video(video_bytes: bytes, watermark_path: str,
                                         opacity: float = WATERMARK_IMAGE_OPACITY,
                                         positions: list | None = None, scale: float = WATERMARK_IMAGE_WIDTH_RATIO) -> bytes:
    """Те саме, що й для фото, але для відео — через ffmpeg (ланцюжок фільтрів
    overlay, по одному на кожну обрану позицію, п.2.2-2.3/3.1 ТЗ). ВИМАГАЄ
    встановленого ffmpeg на сервері. Якщо ffmpeg відсутній чи стається помилка —
    повертає відео БЕЗ водяного знаку."""
    positions = positions or ["center"]
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            in_path = os.path.join(tmp_dir, "in.mp4")
            out_path = os.path.join(tmp_dir, "out.mp4")
            with open(in_path, "wb") as f:
                f.write(video_bytes)

            # Дізнаємось ширину відео, щоб масштабувати водяний знак відносно НЬОГО
            # (а не відносно самого себе) — для цього потрібні реальні пікселі, а не
            # відносний вираз ffmpeg (across двох різних вхідних потоків це ненадійно).
            probe = await asyncio.create_subprocess_exec(
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width", "-of", "csv=p=0", in_path,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            )
            probe_out, _ = await asyncio.wait_for(probe.communicate(), timeout=20)
            video_width = int(probe_out.decode().strip() or 0)
            if video_width <= 0:
                logger.warning("Не вдалося визначити ширину відео — водяний знак не накладено")
                return video_bytes
            target_w = max(2, int(video_width * scale)) // 2 * 2  # парне число — вимога ffmpeg

            margin = f"W*{WATERMARK_MARGIN_RATIO}"
            margin_h = f"H*{WATERMARK_MARGIN_RATIO}"
            overlay_positions = {
                "top-left": (margin, margin_h),
                "top-right": (f"W-w-{margin}", margin_h),
                "bottom-left": (margin, f"H-h-{margin_h}"),
                "bottom-right": (f"W-w-{margin}", f"H-h-{margin_h}"),
                "center": ("(W-w)/2", "(H-h)/2"),
            }

            # Один вхідний watermark-стрім [1:v], масштабований один раз, накладається
            # ланцюжком overlay — по одному на кожну обрану позицію.
            filters = [f"[1:v]scale={target_w}:-2,format=rgba,colorchannelmixer=aa={opacity}[wm]"]
            prev_label = "0:v"
            for i, position in enumerate(positions):
                ox, oy = overlay_positions.get(position, overlay_positions["center"])
                out_label = f"out{i}" if i < len(positions) - 1 else "out"
                filters.append(f"[{prev_label}][wm]overlay={ox}:{oy}[{out_label}]")
                prev_label = out_label
            filter_complex = ";".join(filters)

            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y", "-i", in_path, "-i", watermark_path,
                "-filter_complex", filter_complex, "-map", "[out]", "-map", "0:a?",
                "-codec:a", "copy", "-preset", "veryfast", out_path,
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=120)
            if proc.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                with open(out_path, "rb") as f:
                    return f.read()
            logger.warning(f"ffmpeg завершився з кодом {proc.returncode} — відео надіслано без водяного знаку")
    except FileNotFoundError:
        logger.warning("ffmpeg/ffprobe не встановлено на сервері — відео надсилаються без водяного знаку")
    except Exception as e:
        logger.warning(f"Не вдалося накласти кастомний водяний знак на відео: {e}")
    return video_bytes


def _add_watermark_to_image(image_bytes: bytes, watermark_text: str) -> bytes:
    """ЗАПАСНИЙ варіант (текстовий, 3 ряди) — використовується лише для каналів, які ще
    НЕ завантажили свій кастомний водяний знак-картинку. Напівпрозорий білий текст з
    тінню. Якщо Pillow недоступний чи щось пішло не так — повертає оригінал без знаку."""
    if not _PIL_AVAILABLE or not watermark_text:
        return image_bytes
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        w, h = img.size
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        font_size = max(14, w // 28)
        font = _load_watermark_font(font_size)
        shadow_offset = max(1, font_size // 16)

        for row_y in (h * 0.08, h * 0.5, h * 0.92):
            bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x = (w - text_w) / 2
            y = row_y - text_h / 2
            draw.text((x + shadow_offset, y + shadow_offset), watermark_text, font=font, fill=(0, 0, 0, 70))
            draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, 90))

        result = Image.alpha_composite(img, overlay).convert("RGB")
        buf = io.BytesIO()
        result.save(buf, format="JPEG", quality=90)
        return buf.getvalue()
    except Exception as e:
        logger.warning(f"Не вдалося накласти водяний знак на фото: {e}")
        return image_bytes


async def _add_watermark_to_video(video_bytes: bytes, watermark_text: str) -> bytes:
    """ЗАПАСНИЙ варіант (текстовий, 3 ряди) для відео — лише для каналів БЕЗ кастомного
    водяного знаку-картинки. ВИМАГАЄ встановленого ffmpeg на сервері. Якщо ffmpeg
    відсутній, стається помилка, чи перевищено таймаут — повертає відео БЕЗ водяного
    знаку (щоб відео все одно дійшло до каналу, а не пропало через збій накладання)."""
    if not watermark_text:
        return video_bytes
    escaped = watermark_text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    font_path = _BUNDLED_FONT_PATH if os.path.exists(_BUNDLED_FONT_PATH) else None
    # Без явного fontfile ffmpeg бере системний шрифт "за замовчуванням" через fontconfig —
    # на сервері без встановлених шрифтів (як Render) це могло даватиcz шрифт без кирилиці
    # (звідси квадратики замість тексту). Явно вказуємо наш власний шрифт із проекту.
    font_clause = ""
    if font_path:
        escaped_font_path = font_path.replace("\\", "/").replace(":", "\\:")
        font_clause = f":fontfile='{escaped_font_path}'"
    filters = ",".join(
        f"drawtext=text='{escaped}'{font_clause}:fontcolor=white@0.35:fontsize=h/20:"
        f"x=(w-text_w)/2:y={y_expr}:shadowcolor=black@0.25:shadowx=2:shadowy=2"
        for y_expr in ("h*0.08", "(h-text_h)/2", "h*0.90-text_h")
    )
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            in_path = os.path.join(tmp_dir, "in.mp4")
            out_path = os.path.join(tmp_dir, "out.mp4")
            with open(in_path, "wb") as f:
                f.write(video_bytes)
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y", "-i", in_path, "-vf", filters,
                "-codec:a", "copy", "-preset", "veryfast", out_path,
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=120)
            if proc.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                with open(out_path, "rb") as f:
                    return f.read()
            logger.warning(f"ffmpeg завершився з кодом {proc.returncode} — відео надіслано без водяного знаку")
    except FileNotFoundError:
        logger.warning("ffmpeg не встановлено на сервері — відео надсилаються без водяного знаку")
    except Exception as e:
        logger.warning(f"Не вдалося накласти водяний знак на відео: {e}")
    return video_bytes


async def _download_media_bytes(url: str | None, kind: str = "photo") -> bytes | None:
    """Завантажує медіафайл (фото чи відео) самостійно замість передачі URL напряму —
    сервери Telegram САМІ намагаються скачати файл за URL, і для CDN Telegram (t.me/s/
    прев'ю) чи деяких сайтів це часто не вдається (захист від хотлінків, застарілі/
    підписані посилання) — саме це дає помилки "Failed to get http url content" /
    "Wrong type of the web page content". Скачуючи байти самі — обходимо це обмеження."""
    if not url:
        return None
    timeout = 12 if kind == "photo" else 40  # відео важче й довше качається
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True,
            )
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if kind == "photo" and content_type and not content_type.startswith("image/"):
                logger.warning(f"Пропущено як картинку (content-type={content_type}): {url}")
                return None
            content = resp.content
            if len(content) > 49 * 1024 * 1024:  # ліміт Bot API на завантаження файлу — 50 МБ
                logger.warning(f"Медіафайл занадто великий ({len(content)} байт), пропущено: {url}")
                return None
            return content
    except Exception as e:
        logger.warning(f"Не вдалося завантажити {kind} {url}: {e}")
        return None


async def _download_media_items(items: list) -> list:
    """Завантажує список медіа-елементів [{"type": "photo"/"video", "url": ...}] у байти.
    Повертає [{"type", "bytes"}], пропускаючи те, що не вдалось скачати — щоб один
    невдалий файл не зривав відправку решти. Обмежено 10 — максимум медіа в альбомі Telegram."""
    result = []
    for item in (items or [])[:10]:
        if item.get("bytes"):
            data = item["bytes"]
        else:
            url = item.get("url")
            if not url:
                continue
            data = await _download_media_bytes(url, item.get("type", "photo"))
        if data:
            result.append({"type": item.get("type", "photo"), "bytes": data})
    return result


async def _send_html_message(bot, chat_id: int, text: str, **kwargs) -> None:
    """send_message з HTML-розміткою і аварійним запобіжником: якщо згенерований HTML
    (форматування, збережене з джерела) чомусь виявився невалідним для Telegram —
    надсилаємо той самий текст без тегів, простим текстом, аби новина хоч дійшла,
    а не пропала мовчки через помилку парсингу."""
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", **kwargs)
    except Exception as e:
        if "parse entities" in str(e).lower() or "can't find end" in str(e).lower():
            plain = re.sub(r"<[^>]+>", "", text)
            await bot.send_message(chat_id=chat_id, text=plain, **kwargs)
        else:
            raise


def _to_input_media(item: dict, caption: str | None = None):
    """Перетворює {"type","bytes"} на InputMediaPhoto/InputMediaVideo — для одиночної
    відправки чи для send_media_group (альбом може містити фото й відео впереміш)."""
    kwargs = {}
    if caption is not None:
        kwargs["caption"] = caption
        kwargs["parse_mode"] = "HTML"
    if item["type"] == "video":
        return InputMediaVideo(media=item["bytes"], **kwargs)
    return InputMediaPhoto(media=item["bytes"], **kwargs)


async def _send_news_post(bot, chat_id: int, text: str, media_items: list, watermark_text: str | None = None, apply_watermark: bool = True) -> None:
    """Надсилає новину в канал БЕЗ ЖОДНОГО скорочення суті, з підтримкою фото, відео
    й альбомів (у тому числі змішаних фото+відео):
    - Немає медіа — просто текстове повідомлення (ліміт Telegram 4096 символів,
      практично завжди вистачає).
    - Є 1 медіа-файл і повний текст влазить у ліміт підпису (1024 символи) — фото/відео
      з повним текстом як підпис.
    - Є кілька медіа (альбом) — send_media_group; підпис на першому елементі, якщо влазить.
    - Текст ДОВШИЙ за ліміт підпису — медіа надсилається БЕЗ підпису, а одразу слідом
      окремим повідомленням іде ПОВНИЙ текст без жодних скорочень (так гарантується
      вимога "без обрізки" з будь-яким обсягом тексту).
    - Водяний знак: НАКЛАДАЄТЬСЯ ЛИШЕ якщо apply_watermark=True (п.4.2 ТЗ — читаємо
      реальний стан тумблера "Накласти водяний знак" з конкретної новини/налаштувань
      каналу, а не робимо це безумовно). Якщо адмін цього каналу завантажив СВІЙ
      водяний знак-картинку — використовується він (по центру, середня прозорість).
      Якщо ні — запасний варіант: текстовий водяний знак (watermark_text, зазвичай
      назва каналу, 3 ряди). Наноситься наново з ОРИГІНАЛЬНИХ байтів для кожного
      виклику, тож кілька каналів ніколи не "нашаровують" водяні знаки один на одного."""
    custom_watermark_path = storage.get_channel_watermark_path(chat_id)
    if apply_watermark and (custom_watermark_path or watermark_text):
        wm_settings = storage.get_channel_watermark_settings(chat_id) if custom_watermark_path else None
        stamped = []
        for item in media_items:
            try:
                if custom_watermark_path:
                    if item["type"] == "video":
                        wb = await _add_image_watermark_to_video(
                            item["bytes"], custom_watermark_path,
                            opacity=wm_settings["opacity"], positions=wm_settings["positions"], scale=wm_settings["scale"],
                        )
                    else:
                        wb = _add_image_watermark_to_photo(
                            item["bytes"], custom_watermark_path,
                            opacity=wm_settings["opacity"], positions=wm_settings["positions"], scale=wm_settings["scale"],
                        )
                elif item["type"] == "video":
                    wb = await _add_watermark_to_video(item["bytes"], watermark_text)
                else:
                    wb = _add_watermark_to_image(item["bytes"], watermark_text)
                stamped.append({"type": item["type"], "bytes": wb})
            except Exception as e:
                logger.warning(f"Не вдалося накласти водяний знак: {e}")
                stamped.append(item)  # без водяного знаку — краще так, ніж не надіслати зовсім
        media_items = stamped
    # apply_watermark=False — media_items ідуть як є, оригінальні чисті байти без змін.

    fits_as_caption = len(text) <= TELEGRAM_CAPTION_LIMIT - 20  # невеликий запас на випадок сюрпризів підрахунку

    if len(media_items) >= 2:
        if fits_as_caption:
            media = [_to_input_media(it, caption=text if i == 0 else None) for i, it in enumerate(media_items)]
            await bot.send_media_group(chat_id=chat_id, media=media)
        else:
            media = [_to_input_media(it) for it in media_items]
            await bot.send_media_group(chat_id=chat_id, media=media)
            await _send_html_message(bot, chat_id, text, disable_web_page_preview=True)
    elif len(media_items) == 1:
        item = media_items[0]
        send_fn = bot.send_video if item["type"] == "video" else bot.send_photo
        file_kwarg = "video" if item["type"] == "video" else "photo"
        if fits_as_caption:
            await send_fn(chat_id=chat_id, **{file_kwarg: item["bytes"]}, caption=text, parse_mode="HTML")
        else:
            await send_fn(chat_id=chat_id, **{file_kwarg: item["bytes"]})
            await _send_html_message(bot, chat_id, text, disable_web_page_preview=True)
    else:
        if len(text) <= TELEGRAM_TEXT_LIMIT - 20:
            await _send_html_message(bot, chat_id, text, disable_web_page_preview=True)
        else:
            # Вкрай рідкісний випадок — текст довший за 4096 символів навіть без медіа.
            # Це єдине місце, де текст все ж ріжеться, і то акуратно, по межі речення.
            safe_text = _smart_truncate(text, TELEGRAM_TEXT_LIMIT - 20)
            await _send_html_message(bot, chat_id, safe_text, disable_web_page_preview=True)


async def _fetch_public_channel_posts(username: str, limit: int = 5) -> list:
    """Reads Telegram through Telethon first, preserving real grouped_id albums.
    Falls back to the legacy t.me/s parser only when Telethon is not configured
    or temporarily fails, so the bot remains operational during setup.
    """
    if telethon_reader.configured():
        try:
            posts = await telethon_reader.fetch_public_channel_posts(username, limit=limit)
            for post in posts:
                # Той самий пайплайн очищення тексту, що й для t.me/s: розбиваємо на
                # заголовок/тіло по DOM-вузлах (перший рядок — заголовок), зрізаємо чужий
                # підпис-приманку в кінці (навіть без розриву рядка), і додатково рядковий
                # прохід _strip_source_signature — на випадок банера посеред тексту.
                soup = BeautifulSoup(f"<div>{post.pop('full_html')}</div>", "html.parser")
                title, body_html = _split_title_and_body_html(soup.div)
                post["title"] = title
                post["body_html"] = _strip_source_signature(body_html)
            logger.info(f"[TELETHON] @{username}: отримано {len(posts)} логічних постів")
            return posts
        except Exception as e:
            logger.exception(f"[TELETHON] @{username}: помилка читання, fallback на t.me/s: {e}")
    else:
        logger.warning(
            "[TELETHON] Не налаштовано TELEGRAM_API_ID/API_HASH/SESSION — "
            "використовується ненадійний fallback t.me/s"
        )
    return await _fetch_public_channel_posts_html(username, limit=limit)


async def _fetch_public_channel_posts_html(username: str, limit: int = 5) -> list:
    """Читає останні пости ПУБЛІЧНОГО каналу через t.me/s/<username> — офіційна публічна
    прев'ю-сторінка Telegram, без потреби додавати бота в канал чи вступати кудись.
    Повертає список {"title":, "body_html":, "link":, "media": [...], "post_id":}, від
    найновішого до найстарішого. "title" — перший рядок звичайним текстом (для нашого
    жирного заголовка й дедуплікації), "body_html" — решта тексту зі збереженим
    форматуванням (жирний/курсив/підкреслення/посилання). "media" — список
    {"type": "photo"/"video", "url": ...}: може містити кілька елементів, якщо пост —
    альбом (у тому числі змішаний із фото й відео разом)."""
    url = f"https://t.me/s/{username}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True)
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        logger.warning(f"Не вдалося завантажити публічну сторінку каналу @{username}: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    posts = []
    for msg in soup.select(".tgme_widget_message"):
        text_el = msg.select_one(".tgme_widget_message_text")
        if text_el:
            # Прибираємо кастомні emoji/стікер-плейсхолдери (спеціальні <i> теги в тексті Telegram
            # рендерить окремими іконками без осмисленого альт-тексту — вони засмічують текст).
            for junk in text_el.select("i.emoji, i.custom-emoji, tg-emoji"):
                junk.decompose()
            title, body_html = _split_title_and_body_html(text_el)
        else:
            title, body_html = "", ""
        body_html = _strip_source_signature(body_html)

        date_el = msg.select_one(".tgme_widget_message_date")
        link = date_el["href"] if date_el and date_el.has_attr("href") else url
        post_id = link.rstrip("/").split("/")[-1]

        post_dt = None
        time_el = date_el.select_one("time") if date_el else None
        if time_el and time_el.has_attr("datetime"):
            try:
                post_dt = datetime.fromisoformat(time_el["datetime"])
            except Exception:
                post_dt = None

        def _bg_url(el) -> str | None:
            if el and el.has_attr("style"):
                # background-image: url('...') / url("...") / url(...) без лапок —
                # усі 3 варіанти зустрічаються залежно від того, як Telegram віддав
                # конкретний елемент. Раніше ловився лише варіант з одинарними
                # лапками — решта фото в альбомі мовчки випадали з видачі.
                m = re.search(r"""url\(\s*['"]?(.+?)['"]?\s*\)""", el["style"])
                if m:
                    return m.group(1)
            return None

        media = []
        # Альбом (кілька медіа в одному пості) — беремо ВСІ елементи групи, фото й відео
        grouped = msg.select(".tgme_widget_message_grouped_photo, .tgme_widget_message_grouped_video")
        if grouped:
            logger.info(f"[SCRAPE-ALBUM] Знайдено grouped-блок: post={link}, елементів={len(grouped)}")
            for group_el in grouped:
                video_el = group_el.select_one("video[src]")
                if video_el:
                    media.append({"type": "video", "url": video_el["src"]})
                    continue
                # Довге/важке відео в альбомі не завжди має пряме посилання на файл —
                # публічна прев'ю-сторінка віддає для нього лише статичний кадр. Раніше
                # код шукав фон тільки в .tgme_widget_message_photo_wrap (клас суто для
                # фото-елементів) або на самому group_el — і для такого відео-елемента
                # альбому нічого не знаходив, тож він мовчки випадав з видачі. Тепер
                # додатково перевіряємо типові класи прев'ю-кадру відео.
                photo_url = _bg_url(
                    group_el.select_one(
                        ".tgme_widget_message_photo_wrap, "
                        ".tgme_widget_message_video_thumb, "
                        ".tgme_widget_message_video_player"
                    ) or group_el
                )
                if photo_url:
                    media.append({"type": "photo", "url": photo_url})
                else:
                    logger.info(f"Не вдалося витягти медіа з елемента альбому поста {msg.get('data-post', '')} — пропущено")
        else:
            video_el = msg.select_one("video[src]")
            if video_el:
                media.append({"type": "video", "url": video_el["src"]})
            else:
                single_photo = _bg_url(msg.select_one(".tgme_widget_message_photo_wrap"))
                if single_photo:
                    media.append({"type": "photo", "url": single_photo})
                # Якщо є тільки статичний кадр відео (саме відео задовге для інлайн-прев'ю
                # і Telegram не віддає пряме посилання на файл) — свідомо НЕ видаємо кадр
                # за фото: краще надіслати новину без медіа, ніж підмінити відео картинкою.

        if not title and not body_html and not media:
            continue  # зовсім порожній пост (ні тексту, ні медіа) — пропускаємо

        posts.append({"title": title, "body_html": body_html, "link": link, "media": media, "post_id": post_id, "post_dt": post_dt})

    # п.1 ТЗ: t.me/s/ зазвичай рендерить альбом одним блоком (.tgme_widget_message_grouped_*,
    # уже враховано вище), АЛЕ інколи Telegram віддає той самий альбом кількома окремими
    # .tgme_widget_message блоками поспіль — без спільного media_group_id у розмітці. Клеїмо
    # їх докупи за такими ж ознаками, як бот уже клеїть медіагрупи від живих апдейтів
    # (buffer + debounce-таймер у media_collector.MediaGroupCollector): сусідній post_id, майже той самий
    # час публікації, і в наступного блоку НЕМАЄ власного тексту (підпис Telegram ставить
    # лише на перший елемент альбому).
    merged: list = []
    for post in posts:  # тут ще хронологічний порядок (від старого до нового)
        prev = merged[-1] if merged else None
        has_own_text = bool(post["title"] or post["body_html"])
        adjacent = _post_ids_adjacent(prev["post_id"], post["post_id"]) if prev else False
        close_in_time = _timestamps_close(prev["post_dt"], post["post_dt"]) if prev else False
        is_continuation = (
            prev is not None
            and post["media"]
            and not has_own_text
            and adjacent
            and close_in_time
        )
        if prev is not None and post["media"] and not is_continuation:
            # Діагностика саме для випадку "мало медіа, але не склеїлось" — щоб
            # з логів було видно, яка саме умова не спрацювала, а не гадати.
            logger.info(
                f"[SCRAPE-ALBUM] НЕ склеєно: prev_post_id={prev['post_id']} cur_post_id={post['post_id']} "
                f"adjacent={adjacent} close_in_time={close_in_time} "
                f"has_own_text={has_own_text} prev_dt={prev['post_dt']} cur_dt={post['post_dt']}"
            )
        if is_continuation:
            logger.info(f"[SCRAPE-ALBUM] Склеєно: post_id={post['post_id']} → до prev_post_id={prev['post_id']}")
            prev["media"].extend(post["media"])
            continue
        merged.append(post)

    return list(reversed(merged))[:limit]  # від найновішого


def _post_ids_adjacent(prev_id: str, cur_id: str, max_gap: int = 3) -> bool:
    """post_id на t.me/s/ — це реальний message_id у Telegram; елементи одного альбому
    йдуть послідовними id (з невеликим запасом на можливі службові повідомлення між ними)."""
    try:
        return 0 < (int(cur_id) - int(prev_id)) <= max_gap
    except (TypeError, ValueError):
        return False


def _timestamps_close(prev_dt, cur_dt, max_seconds: int = 3) -> bool:
    """Telegram публікує весь альбом практично одномоментно — тож елементи одного
    альбому завжди в межах пари секунд один від одного (на відміну від двох
    незалежних постів поспіль, між якими зазвичай хвилини чи більше)."""
    if not prev_dt or not cur_dt:
        return False
    try:
        return abs((cur_dt - prev_dt).total_seconds()) <= max_seconds
    except Exception:
        return False


_TAG_STASH_RE = re.compile(r"<[^>]+>")
_MAX_TRANSLATE_CHARS = 4500  # захисний ліміт довжини для безкоштовного endpoint перекладу


_LANG_TO_GOOGLE_CODE = {"ua": "uk", "ru": "ru", "en": "en"}


async def _translate_plain(text: str, target_lang: str = "ua") -> str:
    """Перекладає звичайний (без HTML) текст на обрану мову (ua/ru) через безкоштовний
    неофіційний endpoint Google Translate (без API-ключа й без оплати). Якщо переклад
    не вдався (чи текст задовгий для цього endpoint) — повертає оригінал: краще
    надіслати новину мовою джерела, ніж не надіслати її зовсім через збій перекладу."""
    text = (text or "").strip()
    if not text or len(text) > _MAX_TRANSLATE_CHARS:
        return text
    google_code = _LANG_TO_GOOGLE_CODE.get(target_lang, "uk")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://translate.googleapis.com/translate_a/single",
                params={"client": "gtx", "sl": "auto", "tl": google_code, "dt": "t", "q": text},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return "".join(chunk[0] for chunk in data[0] if chunk[0])
    except Exception as e:
        logger.warning(f"Не вдалося перекласти текст ({target_lang}): {e}")
        return text


async def _translate_html(html_text: str, target_lang: str = "ua") -> str:
    """Те саме, що й _translate_plain, але для тексту зі збереженою HTML-розміткою
    (<b>/<i>/<a href>...) — самі теги на час перекладу ховаються за унікальними
    мітками, щоб перекладач їх не поламав і не переклав атрибути, а потім
    повертаються назад на свої місця."""
    html_text = html_text or ""
    if not html_text.strip():
        return html_text
    tags = []

    def _stash(m):
        tags.append(m.group(0))
        return f"⟦T{len(tags) - 1}⟧"

    protected = _TAG_STASH_RE.sub(_stash, html_text)
    translated = await _translate_plain(protected, target_lang)

    def _restore(m):
        idx = int(m.group(1))
        return tags[idx] if idx < len(tags) else m.group(0)

    return re.sub(r"⟦T(\d+)⟧", _restore, translated)


_AI_REWRITE_LANG_NAME = {"ua": "українською мовою", "ru": "російською мовою", "en": "in English"}

# Стилі рерайту — кнопки швидкого перемикання в редакторі (п.1.1 ТЗ). "neutral" —
# той самий стиль, що був завжди (дефолт і для автоматичного фонового рерайту).
_AI_REWRITE_STYLE_INSTRUCTION = {
    "neutral": "у стилі короткого новинного допису для Telegram-каналу",
    "official": "у офіційному, стриманому діловому стилі — без емоційних епітетів, "
                "розмовних зворотів і вигуків, як прес-реліз",
    "urgent": "у стилі термінового екстреного повідомлення — гостро, з акцентом на "
              "терміновість і головний факт одразу в першому реченні",
    "summary": "як гранично стисле саммарі — максимум 2-3 коротких речення, лише "
               "ключові факти, без деталей і другорядних подробиць",
}


async def _ai_rewrite_plain(text: str, target_lang: str = "ua", style: str = "neutral") -> str:
    """Переписує текст своїми словами (ті самі факти, інші формулювання) через
    Gemini — щоб опублікований пост не був дослівною копією джерела. Якщо Gemini
    не налаштовано (немає GEMINI_API_KEY) чи виклик зірвався з будь-якої причини —
    повертає ОРИГІНАЛЬНИЙ текст: краще опублікувати як є, ніж втратити новину
    через збій рерайту."""
    text = (text or "").strip()
    if _gemini_client is None or not text:
        return text
    lang_name = _AI_REWRITE_LANG_NAME.get(target_lang, "українською мовою")
    style_instruction = _AI_REWRITE_STYLE_INSTRUCTION.get(style, _AI_REWRITE_STYLE_INSTRUCTION["neutral"])
    try:
        prompt = (
            f"Перепиши цей текст новини {lang_name} — своїми словами, зберігаючи ВСІ факти "
            f"максимально точно (нічого не вигадуй і не додавай від себе), без зайвої води, "
            f"{style_instruction}.\n\n"
            "Повністю прибери будь-які рекламні/промо-фрази джерела, які закликають "
            "дивитися, читати чи підписуватись на СТОРОННІЙ канал, сайт чи соцмережу "
            "(наприклад «дивіться повне інтерв'ю на YouTube-каналі...», «підписуйтесь "
            "на канал...», «читайте повністю на сайті...», «джерело: ...») — це не "
            "стосується самої новини і не повинно лишитись у переписаному тексті.\n\n"
            "У тексті можуть бути технічні мітки виду ⟦T0⟧, ⟦T1⟧ тощо — це маркери "
            "форматування, які МАЮТЬ лишитись у переписаному тексті РІВНО в такому ж "
            "вигляді (той самий номер, ті самі символи ⟦ ⟧), просто постав кожну мітку "
            "приблизно там, де за змістом було відповідне місце в оригіналі.\n\n"
            "Відповідай ЛИШЕ переписаним текстом, без жодних пояснень чи лапок навколо.\n\n"
            f"{text}"
        )
        resp = await _gemini_client.aio.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        rewritten = (resp.text or "").strip()
        return rewritten or text
    except Exception as e:
        logger.warning(f"Не вдалося виконати ІІ-рерайт тексту: {e}")
        return text


async def _ai_rewrite_html(html_text: str, target_lang: str = "ua", style: str = "neutral") -> str:
    """Те саме, що _ai_rewrite_plain, але для тексту зі збереженою HTML-розміткою —
    теги ховаються за мітками на час рерайту (той самий трюк, що й у _translate_html),
    щоб ІІ їх не поламала. Якщо після рерайту хоч одна мітка не відновилась
    коректно назад у тег — це ознака побитого форматування, і функція повертає
    ОРИГІНАЛЬНИЙ html_text замість ризикувати биту розмітку в реальному пості."""
    html_text = html_text or ""
    if _gemini_client is None or not html_text.strip():
        return html_text
    tags = []

    def _stash(m):
        tags.append(m.group(0))
        return f"⟦T{len(tags) - 1}⟧"

    protected = _TAG_STASH_RE.sub(_stash, html_text)
    rewritten = await _ai_rewrite_plain(protected, target_lang, style)
    if rewritten == protected:  # рерайт не відбувся (Gemini недоступний/збій) — теги й так на місці
        return html_text

    restored_count = 0

    def _restore(m):
        nonlocal restored_count
        idx = int(m.group(1))
        restored_count += 1
        return tags[idx] if idx < len(tags) else m.group(0)

    result = re.sub(r"⟦T(\d+)⟧", _restore, rewritten)
    if "⟦" in result or restored_count != len(tags):
        logger.warning("ІІ-рерайт загубив мітки форматування — публікуємо оригінальний текст без рерайту")
        return html_text
    return result


async def _ai_suggest_title_tags(html_text: str, target_lang: str = "ua") -> dict:
    """Генерує коротий влучний заголовок і 3-5 хештегів за змістом тексту (п.1.1 ТЗ,
    кнопка «Заголовок» у редакторі). Повертає {"title": str, "hashtags": str} —
    порожні рядки, якщо Gemini недоступний чи виклик зірвався."""
    empty = {"title": "", "hashtags": ""}
    plain = _strip_html(html_text or "").strip()
    if _gemini_client is None or not plain:
        return empty
    lang_name = _AI_REWRITE_LANG_NAME.get(target_lang, "українською мовою")
    try:
        prompt = (
            f"Ось текст новини {lang_name}:\n\n{plain}\n\n"
            "Запропонуй до неї:\n"
            "1. Короткий влучний заголовок (до 8 слів, без крапки в кінці, без лапок)\n"
            "2. Від 3 до 5 релевантних хештегів (одним словом кожен, латиницею або "
            f"{lang_name.replace('мовою', '').strip()}, без пробілів усередині тега)\n\n"
            "Відповідай СУВОРО у форматі двох рядків, без жодних пояснень:\n"
            "TITLE: <заголовок>\n"
            "HASHTAGS: #тег1 #тег2 #тег3"
        )
        resp = await _gemini_client.aio.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        raw = (resp.text or "").strip()
        title_m = re.search(r"TITLE:\s*(.+)", raw)
        tags_m = re.search(r"HASHTAGS:\s*(.+)", raw)
        title = title_m.group(1).strip().strip('"').strip() if title_m else ""
        hashtags = tags_m.group(1).strip() if tags_m else ""
        return {"title": title, "hashtags": hashtags}
    except Exception as e:
        logger.warning(f"Не вдалося згенерувати заголовок/хештеги: {e}")
        return empty


# Старі назви лишені як тонкі обгортки — щоб не переписувати кожен виклик, де мова
# ще не важлива (наприклад, ручний "onenews" quick-pick завжди українською).
async def _translate_plain_to_uk(text: str) -> str:
    return await _translate_plain(text, "ua")


async def _translate_html_to_uk(html_text: str) -> str:
    return await _translate_html(html_text, "ua")


def _extract_news_content(entry) -> tuple[str, str, str | None]:
    """Витягує title_plain/summary_html/image_url з RSS-запису БЕЗ перекладу — переклад
    робиться окремо для кожної цільової мови (п.3 патчу ТЗ: у різних адмінів може бути
    різна мова інтерфейсу/контенту, тож той самий пост перекладається по-різному)."""
    summary_raw = getattr(entry, "summary", "") or getattr(entry, "description", "")
    summary_html = _html_summary_to_tg_html(summary_raw)
    title_plain = _strip_html(entry.title)

    # Прибираємо повторення заголовка на початку опису — тільки якщо опис БЕЗ розмітки
    # (щоб точно не розрізати посеред тегу і не зламати HTML)
    if "<" not in summary_html and summary_html.lower().startswith(title_plain.lower()):
        summary_html = summary_html[len(title_plain):].strip(" -—:")

    summary_html = _strip_source_signature(summary_html)
    image_url = _extract_entry_image(entry)
    return title_plain, summary_html, image_url


async def _translate_news_content(title_plain: str, summary_html: str, target_lang: str = "ua",
                                   apply_ai_rewrite: bool = True) -> str:
    """Перекладає й збирає фінальний текст поста для ОБРАНОЇ мови (ua/ru).
    apply_ai_rewrite=False — для редакційних джерел (свій текст, рерайтити нема сенсу,
    людина сама написала так, як хотіла)."""
    translated_title = await _translate_plain(title_plain, target_lang)
    translated_summary = await _translate_html(summary_html, target_lang) if summary_html else ""
    # ІІ-рерайт лише ТІЛА посту (не заголовка — короткий заголовок легко втратити
    # точність/пошукові слова при перефразуванні, а тіло виграє від унікального тексту).
    if translated_summary and apply_ai_rewrite:
        translated_summary = await _ai_rewrite_html(translated_summary, target_lang)
    text = f"⚡ <b>{html_lib.escape(translated_title)}</b>"
    if translated_summary:
        text += f"\n\n{translated_summary}"
    return text


async def _format_news_post(entry) -> tuple[str, str | None]:
    """Сумісна обгортка: формує текст ОДРАЗУ українською (за замовчуванням) — для місць,
    де мова конкретного каналу ще не важлива (наприклад, прев'ю в панелі)."""
    title_plain, summary_html, image_url = _extract_news_content(entry)
    text = await _translate_news_content(title_plain, summary_html, "ua")
    return text, image_url


def _build_channel_footer(title: str, channel_link: str | None, submit_link: str | None = None) -> str:
    """Підпис під новиною: назва каналу (гіперпосилання, якщо є) і, якщо переданий
    submit_link, — "Надіслати новину" (гіперпосилання на персональний deep-link читача
    САМЕ цього каналу), розділені "|". Кожен канал має свою назву/посилання/submit_link,
    тож підпис завжди унікальний для каналу, навіть коли одна й та сама новина
    розсилається одразу в кілька каналів."""
    channel_part = f'<a href="{channel_link}">{title}</a>' if channel_link else title
    if submit_link:
        return f'{channel_part} | <a href="{submit_link}">Надіслати новину</a>'
    return channel_part


async def _get_channel_link(bot, channel_id: int, username: str | None) -> str | None:
    """Повертає посилання на канал: публічний @username, або раніше створену інвайт-посилання,
    або створює нову інвайт-посилання (для приватних каналів без @username) і запам'ятовує її назавжди
    (create_chat_invite_link НЕ відкликає інші посилання, на відміну від export_chat_invite_link)."""
    if username:
        return f"https://t.me/{username}"

    saved = storage.get_channel_invite_link(channel_id)
    if saved:
        return saved

    try:
        result = await bot.create_chat_invite_link(chat_id=channel_id, name="Підпис у новинах")
        storage.set_channel_invite_link(channel_id, result.invite_link)
        return result.invite_link
    except Exception as e:
        logger.warning(f"Не вдалося створити інвайт-посилання для {channel_id}: {e}")
        return None


async def check_news(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Періодично перевіряє джерела і СТАВИТЬ нові новини в чергу публікації (не надсилає
    напряму) — після подвійної перевірки на дублі: швидкої текстової (difflib) і,
    якщо налаштовано, додаткової смислової через ІІ. З черги новини видає окремий
    воркер publish_from_queue — рівно 1 за раз, з паузою (КД) між публікаціями."""
    storage.set_setting("last_check_news_run_at", datetime.now().isoformat())
    logger.info("[PARSER] check_news запущено")

    news_channels = [ch for ch in storage.get_active_channels() if ch.get("news_enabled")]
    if not news_channels:
        return

    seen = set(storage.get_seen_news())

    # --- RSS-джерела: групуємо за URL, щоб НЕ смикати одну й ту саму стрічку кілька разів,
    # якщо кілька різних адмінів незалежно додали собі один і той самий сайт як джерело ---
    rss_by_url: dict[str, list] = {}
    for src in storage.get_active_rss_sources():
        rss_by_url.setdefault(src["url"], []).append(src)

    for feed_url, srcs in rss_by_url.items():
        display_name = srcs[0]["name"]
        try:
            feed = await _fetch_feed(feed_url)
        except Exception as e:
            logger.warning(f"Не вдалося отримати RSS {display_name}: {e}")
            storage.log_error(f"RSS {display_name}: {e}")
            continue

        new_entries = [entry for entry in feed.entries if entry.link not in seen]
        # п.2 ТЗ: якщо ЦЕ джерело (для всіх адмінів, які його додали) позначене
        # "Редакційний чат" — новини з нього йдуть у чергу БЕЗ перевірки на дублі
        # й з пріоритетом показу в черзі (сортування на фронтенді вже враховує priority).
        source_is_editorial = all(s.get("category") == "editorial_chat" for s in srcs)
        for entry in reversed(new_entries[:MAX_NEW_ITEMS_PER_SOURCE_PER_CYCLE]):  # весь свіжий бэклог
                                                    # джерела за раз (не по 1), щоб не втрачати новини на очікуванні
            # Recency-фільтр: пост, старший за NEWS_MAX_AGE_MINUTES — ігноруємо (не публікуємо
            # застарілу інформацію), але позначаємо переглянутою, щоб не перевіряти знову.
            published_parsed = entry.get("published_parsed")
            entry_dt = datetime(*published_parsed[:6]) if published_parsed else None  # feedparser нормалізує в UTC
            if entry_dt and not _is_post_fresh(entry_dt):
                storage.add_seen_news(entry.link)
                seen.add(entry.link)
                logger.info(f"Пропущено як застарілу: {entry.title}")
                continue

            title_plain, summary_html, image_url = _extract_news_content(entry)

            if not source_is_editorial and _looks_like_ad(f"{title_plain} {summary_html}"):
                storage.add_seen_news(entry.link)
                seen.add(entry.link)
                logger.info(f"Пропущено як рекламу: {title_plain[:60]}")
                continue

            if not source_is_editorial and _looks_like_scam(f"{title_plain} {summary_html}"):
                storage.add_seen_news(entry.link)
                seen.add(entry.link)
                logger.info(f"Пропущено як підозру на скам/фішинг: {title_plain[:60]}")
                continue

            # Крок 1: власники джерела (адміни) -> їхня обрана мова контенту (ua/ru)
            delivered_owners = set()
            owner_lang_map: dict = {}
            for src in srcs:
                owner = src.get("added_by")
                if owner in delivered_owners:
                    continue  # той самий адмін не міг додати цей URL двічі собі — не дублюємо
                delivered_owners.add(owner)
                owner_lang_map[owner] = storage.get_admin_language(owner) if owner is not None else "ua"

            needed_langs = set(owner_lang_map.values()) or {"ua"}

            # Крок 2: перекладаємо ОДИН РАЗ на кожну потрібну мову (не на кожного власника окремо)
            lang_text, lang_title, lang_title_lower, lang_norm_title = {}, {}, {}, {}
            for lang in needed_langs:
                text = await _translate_news_content(title_plain, summary_html, lang,
                                                       apply_ai_rewrite=not source_is_editorial)
                t_title = re.sub(r"<[^>]+>", "", text.split("\n", 1)[0]).replace("⚡", "").strip()
                lang_text[lang] = text
                lang_title[lang] = t_title
                lang_title_lower[lang] = t_title.lower()
                lang_norm_title[lang] = _normalize_title(t_title)

            # Крок 3: фан-аут по каналах, згрупований за мовою — ключові слова каналу
            # звіряються з заголовком, перекладеним САМЕ мовою цього адміна.
            channel_ids_by_lang: dict = {}
            for owner, lang in owner_lang_map.items():
                owner_channels = [ch for ch in news_channels if ch.get("added_by") == owner]
                title_lower = lang_title_lower[lang]
                for ch in owner_channels:
                    keywords = ch.get("news_keywords", [])
                    if keywords and not any(kw in title_lower for kw in keywords):
                        continue  # новина не проходить фільтр цього каналу
                    channel_ids_by_lang.setdefault(lang, []).append(ch["id"])

            if not any(channel_ids_by_lang.values()):
                storage.add_seen_news(entry.link)
                seen.add(entry.link)
                continue  # немає жодного каналу-отримувача — публікувати нікуди

            media_items = await _download_media_items([{"type": "photo", "url": image_url}] if image_url else [])

            for lang, channel_ids in channel_ids_by_lang.items():
                if not channel_ids:
                    continue
                norm_title = lang_norm_title[lang]

                # Пул порівняння: те, що вже РЕАЛЬНО опубліковано (чи ще стоїть у черзі) САМЕ
                # в цих цільових каналах — а не глобальний список (Target Channel Analysis).
                comparison_pool = []
                for cid in channel_ids:
                    comparison_pool.extend(storage.get_channel_recent_titles(cid))
                    comparison_pool.extend(storage.get_channel_queued_titles(cid))

                if not source_is_editorial:
                    if _is_similar_title(norm_title, comparison_pool):
                        logger.info(f"Пропущено як дублікат: {lang_title[lang]}")
                        continue

                    # Додаткова смислова перевірка через ІІ (якщо налаштовано GEMINI_API_KEY) —
                    # ловить дублі, сформульовані зовсім іншими словами, які difflib не впіймає.
                    if await _llm_is_duplicate(lang_title[lang], comparison_pool):
                        logger.info(f"ІІ позначив як дублікат: {lang_title[lang]}")
                        continue

                queue_item = storage.enqueue_news(
                    lang_title[lang], lang_text[lang], [], display_name, channel_ids, norm_title=norm_title,
                    priority=source_is_editorial,
                )
                media_paths = _save_media_to_queue_disk(queue_item["id"], media_items)
                if media_paths:
                    storage.update_queue_item(queue_item["id"], media_paths=media_paths)
                # Новина стоїть зі статусом pending — сама вона нікуди не піде, поки
                # адмін не натисне "Схвалити" в панелі. Просто сповіщаємо власника.
                await _notify_queue_owners_pending(context, queue_item)

            storage.add_seen_news(entry.link)
            seen.add(entry.link)

    # --- Публічні Telegram-канали (читання через t.me/s/<username>, без вступу бота) ---
    # Так само групуємо за username, щоб не ходити на ту саму сторінку кілька разів.
    tg_by_username: dict[str, list] = {}
    for src in storage.get_active_public_tg_sources():
        tg_by_username.setdefault(src["username"], []).append(src)

    for username, srcs in tg_by_username.items():
        posts = await _fetch_public_channel_posts(username, limit=5)
        new_posts = [p for p in posts if p["link"] not in seen]
        source_is_editorial = all(s.get("category") == "editorial_chat" for s in srcs)

        for post in reversed(new_posts[:MAX_NEW_ITEMS_PER_SOURCE_PER_CYCLE]):  # весь свіжий бэклог, як і для RSS
            # Recency-фільтр (той самий, що й для RSS): ігноруємо пости старші за NEWS_MAX_AGE_MINUTES.
            if post.get("post_dt") and not _is_post_fresh(post["post_dt"]):
                storage.add_seen_news(post["link"])
                seen.add(post["link"])
                logger.info(f"Пропущено як застарілий пост: {post['title'][:60]}")
                continue

            title_plain = post["title"][:200]
            summary_html = post["body_html"]

            if not source_is_editorial and _looks_like_ad(f"{title_plain} {summary_html}"):
                storage.add_seen_news(post["link"])
                seen.add(post["link"])
                logger.info(f"Пропущено як рекламу: {title_plain[:60]}")
                continue

            if not source_is_editorial and _looks_like_scam(f"{title_plain} {summary_html}"):
                storage.add_seen_news(post["link"])
                seen.add(post["link"])
                logger.info(f"Пропущено як підозру на скам/фішинг: {title_plain[:60]}")
                continue

            delivered_owners = set()
            owner_lang_map: dict = {}
            for src in srcs:
                owner = src.get("added_by")
                if owner in delivered_owners:
                    continue
                delivered_owners.add(owner)
                owner_lang_map[owner] = storage.get_admin_language(owner) if owner is not None else "ua"

            needed_langs = set(owner_lang_map.values()) or {"ua"}

            lang_title, lang_title_lower, lang_norm_title, lang_body = {}, {}, {}, {}
            for lang in needed_langs:
                t_title = await _translate_plain(title_plain, lang)
                t_body = await _translate_html(summary_html, lang) if summary_html else ""
                if t_body and not source_is_editorial:
                    t_body = await _ai_rewrite_html(t_body, lang)
                lang_title[lang] = t_title
                lang_title_lower[lang] = t_title.lower()
                lang_norm_title[lang] = _normalize_title(t_title)
                lang_body[lang] = t_body

            channel_ids_by_lang: dict = {}
            for owner, lang in owner_lang_map.items():
                owner_channels = [ch for ch in news_channels if ch.get("added_by") == owner]
                title_lower = lang_title_lower[lang]
                for ch in owner_channels:
                    keywords = ch.get("news_keywords", [])
                    if keywords and not any(kw in title_lower for kw in keywords):
                        continue
                    channel_ids_by_lang.setdefault(lang, []).append(ch["id"])

            if not any(channel_ids_by_lang.values()):
                storage.add_seen_news(post["link"])
                seen.add(post["link"])
                continue

            media_items = await _download_media_items(post["media"])

            for lang, channel_ids in channel_ids_by_lang.items():
                if not channel_ids:
                    continue
                norm_title = lang_norm_title[lang]

                comparison_pool = []
                for cid in channel_ids:
                    comparison_pool.extend(storage.get_channel_recent_titles(cid))
                    comparison_pool.extend(storage.get_channel_queued_titles(cid))

                if not source_is_editorial:
                    if norm_title and _is_similar_title(norm_title, comparison_pool):
                        logger.info(f"Пропущено як дублікат: {lang_title[lang]}")
                        continue

                    if norm_title and await _llm_is_duplicate(lang_title[lang], comparison_pool):
                        logger.info(f"ІІ позначив як дублікат: {lang_title[lang]}")
                        continue

                base_text = f"⚡ <b>{html_lib.escape(lang_title[lang])}</b>" if lang_title[lang] else "⚡"
                if lang_body[lang]:
                    base_text += f"\n\n{lang_body[lang]}"

                queue_item = storage.enqueue_news(
                    lang_title[lang], base_text, [], username, channel_ids, norm_title=norm_title,
                    priority=source_is_editorial,
                )
                media_paths = _save_media_to_queue_disk(queue_item["id"], media_items)
                if media_paths:
                    storage.update_queue_item(queue_item["id"], media_paths=media_paths)
                await _notify_queue_owners_pending(context, queue_item)

            storage.add_seen_news(post["link"])
            seen.add(post["link"])


async def publish_from_queue(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Часто (раз на ~20 сек) проходить чергу і публікує в кожен канал, ЧИЙ
    ВЛАСНИЙ КД уже минув — незалежно від інших каналів (п.4 ТЗ: "паралельний КД
    для сітки"). Обробляє паузу автопостингу (адмін вимкнув) і паузу через ліміти
    Telegram (помилка 429)."""
    await _process_publish_queue(context.bot)


async def _process_publish_queue(bot) -> None:
    """Спільна логіка публікації з черги — викликається і з періодичної джоби, і
    ОДРАЗУ після постановки нової новини в чергу (сценарій: якщо канал вільний —
    новина виходить негайно, а не чекає наступного тіку).
    "Автопостинг з черги" — тепер персональний перемикач для кожного каналу
    (раніше був один вимикач platform-wide у Тех.розділі), перевіряється
    нижче всередині циклу для кожного каналу окремо."""
    paused_until = storage.get_setting("autopost_paused_until")
    if paused_until:
        try:
            if datetime.fromisoformat(paused_until) > datetime.now():
                return  # ще на паузі через 429 від Telegram — це platform-wide захист, лишається глобальним
        except Exception:
            pass
        storage.set_setting("autopost_paused_until", None)

    now = datetime.now()
    await _ensure_bot_initialized(bot)  # п.3.3 ТЗ — перед bot.username нижче
    bot_username = bot.username
    already_sent_this_pass = set()  # один канал — максимум 1 нова публікація за прохід

    for item, cid in storage.get_pending_queue_targets():
        if cid in already_sent_this_pass:
            continue

        if not storage.get_channel_autopost_enabled(cid):
            continue  # цей канал вимкнув автопостинг з черги для себе

        # КД тепер персональний для кожного каналу (раніше було одне глобальне
        # число на всі канали) — налаштовується у вкладці «Головна» модалки каналу.
        cd_minutes = storage.get_channel_autopost_cd(cid)
        last_pub = storage.get_channel_last_published(cid)
        if last_pub:
            try:
                elapsed = (now - datetime.fromisoformat(last_pub)).total_seconds()
                if elapsed < cd_minutes * 60:
                    continue  # у ЦЬОГО каналу власний КД ще не минув — не чіпаємо, йдемо до наступного
            except Exception:
                pass

        channel = next((c for c in storage.get_channels() if c["id"] == cid), None)
        if not channel:
            storage.mark_channel_delivered(item["id"], cid)  # каналу більше немає — прибираємо ціль
            continue

        # Стікер — окремий шлях: без тексту/футера/водяного знаку, просто send_sticker
        # за тим самим file_id (Bot API дозволяє перевикористовувати file_id ботом
        # у будь-якому чаті, куди він має доступ — повторне завантаження не потрібне).
        if item.get("sticker_file_id"):
            try:
                await bot.send_sticker(chat_id=cid, sticker=item["sticker_file_id"])
                storage.set_channel_last_published(cid, now.isoformat())
                already_sent_this_pass.add(cid)
                storage.mark_channel_delivered(item["id"], cid)
            except RetryAfter as e:
                pause_until = now + timedelta(seconds=e.retry_after + 5)
                storage.set_setting("autopost_paused_until", pause_until.isoformat())
                logger.warning(f"Telegram 429 — автопостинг на паузі до {pause_until.isoformat()}")
                return
            except Exception as e:
                logger.warning(f"Не вдалося опублікувати стікер {item['id']} у {cid}: {e}")
                storage.log_error(f"Публікація стікера {item['id']} у {cid}: {e}")
            await asyncio.sleep(1)
            continue

        media_items = _load_media_from_queue_disk(item.get("media_paths"))
        try:
            chat = await bot.get_chat(cid)
            link = await _get_channel_link(bot, cid, chat.username)
        except Exception:
            link = None
        submit_link = f"https://t.me/{bot_username}?start=channel_{cid}" if bot_username else None
        footer = _build_channel_footer(channel["title"], link, submit_link)
        text = f"{item['text']}\n\n{footer}"
        # п.4.2 ТЗ: реально читаємо стан тумблера — власний вибір для ЦІЄЇ новини
        # має пріоритет над загальним налаштуванням каналу.
        apply_watermark = (not item.get("skip_watermark", False)) and storage.is_channel_auto_watermark_enabled(cid)
        try:
            await _send_news_post(bot, cid, text, media_items, watermark_text=channel["title"], apply_watermark=apply_watermark)
            storage.set_channel_last_published(cid, now.isoformat())
            if item.get("norm_title"):
                storage.add_channel_published_title(cid, item["norm_title"])
            already_sent_this_pass.add(cid)
            done_item = storage.mark_channel_delivered(item["id"], cid)
            if done_item:
                _delete_queue_media_files(done_item.get("media_paths"))
        except RetryAfter as e:
            # Telegram просить почекати — ставимо автопостинг на паузу (п.6 ТЗ, захист від спаму)
            pause_until = now + timedelta(seconds=e.retry_after + 5)
            storage.set_setting("autopost_paused_until", pause_until.isoformat())
            logger.warning(f"Telegram 429 — автопостинг на паузі до {pause_until.isoformat()}")
            return  # зупиняємо весь прохід — щоб одразу не наштовхнутись на ліміт ще раз
        except Exception as e:
            logger.warning(f"Не вдалося опублікувати чергу {item['id']} у {cid}: {e}")
            storage.log_error(f"Публікація черги {item['id']} у {cid}: {e}")
        await asyncio.sleep(1)  # пауза між надсиланнями — щоб не зловити flood control Telegram


async def _ensure_bot_initialized(bot) -> None:
    """п.3.3 ТЗ: гарантована ініціалізація сесії бота перед викликом методу, що
    її потребує. Стандартний Bot(token=...), створений "на льоту" в app.py для
    одноразового запиту, НЕ ініціалізований — виклик властивостей на кшталт
    bot.username (яка читає внутрішній self._bot_user) валить помилку
    "Bot is not properly initialized". initialize() ідемпотентний (безпечно
    викликати повторно навіть для вже ініціалізованого Bot з Application)."""
    try:
        if not getattr(bot, "_initialized", False):
            await bot.initialize()
    except Exception as e:
        logger.warning(f"Не вдалося ініціалізувати сесію бота: {e}")


async def _force_publish_item(bot, item: dict, reset_cooldown: bool = True) -> None:
    """"🚀 Опублікувати зараз" (п.5 ТЗ) — надсилає у ВСІ ще не охоплені канали
    негайно, ІГНОРУЮЧИ їхній поточний КД.
    reset_cooldown=True (звичайна кнопка "Опублікувати зараз"): скидає таймер КД
    цих каналів — наступна публікація знову чекатиме повний інтервал з цього моменту.
    reset_cooldown=False (нова кнопка "Виставити терміново", п.3.1 ТЗ): публікує ЦЕЙ
    матеріал негайно, але НЕ чіпає таймер каналу — розклад інших новин у черзі
    не збивається."""
    await _ensure_bot_initialized(bot)  # п.3.3 ТЗ — перед bot.username нижче
    media_items = _load_media_from_queue_disk(item.get("media_paths"))
    bot_username = bot.username
    delivered = set(item.get("delivered_channel_ids", []))

    for cid in item.get("channel_ids", []):
        if cid in delivered:
            continue
        channel = next((c for c in storage.get_channels() if c["id"] == cid), None)
        if not channel:
            storage.mark_channel_delivered(item["id"], cid)
            continue

        if item.get("sticker_file_id"):
            try:
                await bot.send_sticker(chat_id=cid, sticker=item["sticker_file_id"])
                if reset_cooldown:
                    storage.set_channel_last_published(cid, datetime.now().isoformat())
                storage.mark_channel_delivered(item["id"], cid)
            except RetryAfter as e:
                logger.warning(f"Telegram 429 при примусовій публікації стікера у {cid} — чекаємо {e.retry_after}с")
                await asyncio.sleep(e.retry_after + 1)
                try:
                    await bot.send_sticker(chat_id=cid, sticker=item["sticker_file_id"])
                    if reset_cooldown:
                        storage.set_channel_last_published(cid, datetime.now().isoformat())
                    storage.mark_channel_delivered(item["id"], cid)
                except Exception as e2:
                    logger.warning(f"Повторна спроба стікера після 429 не вдалась у {cid}: {e2}")
                    storage.log_error(f"Примусова публікація стікера (retry) черги {item['id']} у {cid}: {e2}")
            except Exception as e:
                logger.warning(f"Не вдалося примусово опублікувати стікер {item['id']} у {cid}: {e}")
                storage.log_error(f"Примусова публікація стікера черги {item['id']} у {cid}: {e}")
            continue

        try:
            chat = await bot.get_chat(cid)
            link = await _get_channel_link(bot, cid, chat.username)
        except Exception:
            link = None
        submit_link = f"https://t.me/{bot_username}?start=channel_{cid}" if bot_username else None
        footer = _build_channel_footer(channel["title"], link, submit_link)
        text = f"{item['text']}\n\n{footer}"
        apply_watermark = (not item.get("skip_watermark", False)) and storage.is_channel_auto_watermark_enabled(cid)
        try:
            await _send_news_post(bot, cid, text, media_items, watermark_text=channel["title"], apply_watermark=apply_watermark)
            if reset_cooldown:
                storage.set_channel_last_published(cid, datetime.now().isoformat())
            if item.get("norm_title"):
                storage.add_channel_published_title(cid, item["norm_title"])
            done_item = storage.mark_channel_delivered(item["id"], cid)
            if done_item:
                _delete_queue_media_files(done_item.get("media_paths"))
        except RetryAfter as e:
            # Telegram просить почекати — чекаємо і пробуємо цей самий канал ще раз ОДИН
            # раз (це ручна дія адміна "Опублікувати зараз", тож канал краще не втрачати мовчки).
            logger.warning(f"Telegram 429 при примусовій публікації у {cid} — чекаємо {e.retry_after}с")
            await asyncio.sleep(e.retry_after + 1)
            try:
                await _send_news_post(bot, cid, text, media_items, watermark_text=channel["title"], apply_watermark=apply_watermark)
                if reset_cooldown:
                    storage.set_channel_last_published(cid, datetime.now().isoformat())
                if item.get("norm_title"):
                    storage.add_channel_published_title(cid, item["norm_title"])
                done_item = storage.mark_channel_delivered(item["id"], cid)
                if done_item:
                    _delete_queue_media_files(done_item.get("media_paths"))
            except Exception as e2:
                logger.warning(f"Повторна спроба після 429 не вдалась у {cid}: {e2}")
                storage.log_error(f"Примусова публікація (retry) черги {item['id']} у {cid}: {e2}")
        except Exception as e:
            logger.warning(f"Не вдалося примусово опублікувати чергу {item['id']} у {cid}: {e}")
            storage.log_error(f"Примусова публікація черги {item['id']} у {cid}: {e}")
        await asyncio.sleep(1)


async def cleanup_queue_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """TTL-очистка (п.6 ТЗ): раз на кілька хвилин видаляє з черги новини, що чекають
    публікації довше 2 годин, разом з їхніми файлами медіа."""
    expired = storage.cleanup_expired_queue_items()
    for it in expired:
        _delete_queue_media_files(it.get("media_paths"))
    if expired:
        logger.info(f"TTL: видалено {len(expired)} застарілих новин із черги публікації")


async def check_scheduled_posts(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Планувальник відкладеного постингу (POST /api/schedule): раз на 30с перевіряє
    пости, чий publish_at вже настав, "публікує" їх (у вказані channel_ids, якщо є)
    і видаляє з активної черги — п.2-3 ТЗ."""
    now_iso = datetime.now().isoformat()
    due = storage.get_due_scheduled_posts(now_iso)
    for item in due:
        try:
            for cid in item.get("channel_ids", []):
                try:
                    await _send_html_message(context.bot, cid, item["text"] or item["title"])
                except RetryAfter as e:
                    logger.warning(f"Telegram 429 при запланованій публікації у {cid} — чекаємо {e.retry_after}с")
                    await asyncio.sleep(e.retry_after + 1)
                    try:
                        await _send_html_message(context.bot, cid, item["text"] or item["title"])
                    except Exception as e2:
                        logger.warning(f"Повторна спроба після 429 не вдалась у {cid}: {e2}")
                        storage.log_error(f"Заплановий пост {item['id']} у {cid} (retry): {e2}")
                except Exception as e:
                    logger.warning(f"Не вдалося опублікувати заплановий пост {item['id']} у {cid}: {e}")
                    storage.log_error(f"Заплановий пост {item['id']} у {cid}: {e}")
                await asyncio.sleep(0.5)  # пауза між каналами — щоб не зловити flood control Telegram
            logger.info(f"Опубліковано запланований пост {item['id']}: {item['title'][:60]}")
        finally:
            storage.remove_scheduled_post(item["id"])


# ==================== Моніторинг повітряних тривог (NEPTUN, neptun.in.ua) ====================
# API безкоштовний, без ключів, CORS відкритий — https://neptun.in.ua/developers.
# NEPTUN прямо застерігає: це інформаційний агрегатор, а НЕ офіційна система
# оповіщення (можливі неточності й затримки) — тому в кожному повідомленні нижче
# явно вказано джерело й додано відсилання до офіційних сигналів тривоги.
NEPTUN_BASE_URL = "https://neptun.in.ua"
NEPTUN_ALERTS_URL = f"{NEPTUN_BASE_URL}/api/v1/alerts"
NEPTUN_THREATS_URL = f"{NEPTUN_BASE_URL}/api/v1/threats"

# 25 областей + Київ + окуповані території одним пунктом — для UI вибору областей
# в /api/channels/alert-settings (аналогічно до /api/channels/category, п.1 ТЗ).
UKRAINE_OBLASTS = [
    "Вінницька область", "Волинська область", "Дніпропетровська область", "Донецька область",
    "Житомирська область", "Закарпатська область", "Запорізька область", "Івано-Франківська область",
    "Київська область", "м. Київ", "Кіровоградська область", "Луганська область", "Львівська область",
    "Миколаївська область", "Одеська область", "Полтавська область", "Рівненська область",
    "Сумська область", "Тернопільська область", "Харківська область", "Херсонська область",
    "Хмельницька область", "Черкаська область", "Чернівецька область", "Чернігівська область",
    "АР Крим",
]

# п.5.4 ТЗ: "у Київській області", "у Сумській області", "у Києві" — назва області з
# UKRAINE_OBLASTS стоїть у називному відмінку (для UI-вибору), а в тексті сповіщення
# потрібен місцевий відмінок з правильним прийменником (у/в). Відмінювання українських
# топонімів нерегулярне, тож тримаємо явну мапу замість алгоритмічного словозміни —
# це єдиний надійний спосіб не отримати русизм на кшталт "в Київська область".
_OBLAST_LOCATIVE = {
    "Вінницька область": "у Вінницькій області",
    "Волинська область": "у Волинській області",
    "Дніпропетровська область": "у Дніпропетровській області",
    "Донецька область": "у Донецькій області",
    "Житомирська область": "у Житомирській області",
    "Закарпатська область": "у Закарпатській області",
    "Запорізька область": "у Запорізькій області",
    "Івано-Франківська область": "в Івано-Франківській області",
    "Київська область": "у Київській області",
    "м. Київ": "у Києві",
    "Кіровоградська область": "у Кіровоградській області",
    "Луганська область": "у Луганській області",
    "Львівська область": "у Львівській області",
    "Миколаївська область": "у Миколаївській області",
    "Одеська область": "в Одеській області",
    "Полтавська область": "у Полтавській області",
    "Рівненська область": "у Рівненській області",
    "Сумська область": "у Сумській області",
    "Тернопільська область": "у Тернопільській області",
    "Харківська область": "у Харківській області",
    "Херсонська область": "у Херсонській області",
    "Хмельницька область": "у Хмельницькій області",
    "Черкаська область": "у Черкаській області",
    "Чернівецька область": "у Чернівецькій області",
    "Чернігівська область": "у Чернігівській області",
    "АР Крим": "в АР Крим",
}


def _oblast_locative(oblast_name: str) -> str:
    """Місцевий відмінок з прийменником для назви області/міста в тексті
    сповіщення (п.5.4 ТЗ). Якщо NEPTUN раптом віддасть назву, якої нема в мапі
    (нове формулювання з їхнього боку) — не падаємо, а даємо м'який фолбек
    "у <назва>", що хоч і не ідеальний відмінок, та все одно грамотніший
    за буквальне "в Назва область"."""
    if oblast_name in _OBLAST_LOCATIVE:
        return _OBLAST_LOCATIVE[oblast_name]
    prefix = "в" if oblast_name[:1].lower() in "аеєиіїоуюя" else "у"
    return f"{prefix} {oblast_name}"


async def _neptun_fetch(url: str) -> dict | None:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning(f"NEPTUN {url} недоступний: {e}")
        return None


_THREAT_TYPE_SHORT = {
    "uav": "БпЛА", "recon": "розвід. БпЛА", "missile": "крилата ракета",
    "ballistic": "балістика", "kab": "КАБ", "mig31k": "МіГ-31К", "unknown": "ціль",
}

# Дієслово руху під кожен тип цілі — для чистих оперативних зведень без слова
# "тривога" (п.2.2 нового ТЗ: "БПЛА курсом на [Локація]" / "КАБ у напрямку [Локація]").
_THREAT_DIRECTION_VERB = {
    "uav": "курсом на", "recon": "курсом на", "missile": "курсом на",
    "ballistic": "курсом на", "kab": "у напрямку", "mig31k": "у районі", "unknown": "у районі",
}


_KYIV_DISTRICT_CACHE: dict = {}
_last_nominatim_call = 0.0
_NOMINATIM_MIN_INTERVAL = 1.1  # трохи більше 1с — політика використання Nominatim вимагає не частіше 1 запиту/с


async def _kyiv_district(lat, lon) -> str | None:
    """Район Києва (Дарницький/Дніпровський/...) за координатами цілі — сам
    NEPTUN такої деталізації не дає (лише місто/область цілком, район цілі
    прямо в API відсутній), тож визначаємо через безкоштовний reverse-geocoding
    OpenStreetMap Nominatim. Кешуємо по координатах, округлених до ~100м, —
    той самий район повторно питати немає сенсу, а й політика використання
    Nominatim прямо вимагає не більше 1 запиту на секунду (звідси й затримка
    нижче, а не просто "жени запити як є")."""
    global _last_nominatim_call
    if lat is None or lon is None:
        return None
    key = (round(lat, 3), round(lon, 3))
    if key in _KYIV_DISTRICT_CACHE:
        return _KYIV_DISTRICT_CACHE[key]
    wait = _NOMINATIM_MIN_INTERVAL - (time.monotonic() - _last_nominatim_call)
    if wait > 0:
        await asyncio.sleep(wait)
    _last_nominatim_call = time.monotonic()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lon, "format": "json", "addressdetails": 1, "zoom": 14},
                headers={"User-Agent": "RezervUARadarBot/1.0 (air-alert monitoring, non-commercial)"},
                timeout=6,
            )
            resp.raise_for_status()
            address = resp.json().get("address", {})
    except Exception as e:
        logger.warning(f"Nominatim reverse-geocoding недоступний ({lat},{lon}): {e}")
        return None  # НЕ кешуємо збій — тимчасова недоступність не повинна назавжди "забороняти" район для цих координат
    district = address.get("borough") if address.get("city") == "Київ" else None
    _KYIV_DISTRICT_CACHE[key] = district
    return district


async def _get_alert_context(bot, channel_id: int) -> tuple[str | None, str, str | None]:
    """Посилання на канал, назва каналу і посилання на "Прислати новину" — для футера."""
    try:
        chat = await bot.get_chat(channel_id)
        title = chat.title or str(channel_id)
        channel_link = await _get_channel_link(bot, channel_id, chat.username)
    except Exception:
        title = str(channel_id)
        channel_link = None
    bot_username = getattr(bot, "username", None)
    submit_link = f"https://t.me/{bot_username}?start=channel_{channel_id}" if bot_username else None
    return channel_link, title, submit_link


_THREAT_MAP_SIZE = (640, 420)
_THREAT_MAP_COLOR = {
    "uav": "#ff9f0a", "recon": "#ffcc00", "missile": "#ff3b30",
    "ballistic": "#af52de", "kab": "#ff2d55", "mig31k": "#5856d6", "unknown": "#8e8e93",
}


def _render_threat_map(threat: dict) -> bytes | None:
    """Карта руху цілі на підкладці OpenStreetMap: лінія по історії точок
    (trail з NEPTUN) + маркер поточної/останньої відомої позиції. threat має
    містити принаймні lat/lon; trail — необов'язковий список {"lat","lon"}
    у хронологічному порядку (старіші -> новіші). Повертає PNG-байти, або
    None — якщо staticmap не встановлено, немає координат, чи рендер зірвався
    (наприклад, тайли OpenStreetMap тимчасово недоступні) — тоді виклик має
    відкотитись на звичайний текст, а не втратити сповіщення взагалі."""
    if not _STATICMAP_AVAILABLE:
        return None
    lat, lon = threat.get("lat"), threat.get("lon")
    if lat is None or lon is None:
        return None
    try:
        m = StaticMap(*_THREAT_MAP_SIZE, url_template="https://a.tile.openstreetmap.org/{z}/{x}/{y}.png")
        trail = threat.get("trail") or []
        points = [(p["lon"], p["lat"]) for p in trail if p.get("lat") is not None and p.get("lon") is not None]
        if (lon, lat) not in points:
            points.append((lon, lat))
        color = _THREAT_MAP_COLOR.get(threat.get("type"), _THREAT_MAP_COLOR["unknown"])
        if len(points) >= 2:
            m.add_line(Line(points, color, 4))
        m.add_marker(CircleMarker((lon, lat), color, 14))
        image = m.render()
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        logger.warning(f"Не вдалося намалювати карту руху цілі {threat.get('id')}: {e}")
        return None


def _alert_footer(channel_link: str | None, channel_title: str, submit_link: str | None) -> str:
    """<Посилання на канал> | Надіслати новину (п.3.1 ТЗ) — жодних згадок NEPTUN
    у тексті чи футері (п.3.2), прев'ю вимкнено окремо в _safe_send_alert (п.3.3)."""
    channel_part = f'<a href="{channel_link}">{channel_title}</a>' if channel_link else channel_title
    parts = [channel_part]
    if submit_link:
        parts.append(f'<a href="{submit_link}">Надіслати новину</a>')
    return " | ".join(parts)


def _format_alert_duration(seconds: float) -> str:
    """Людський формат тривалості тривоги для підсумку при відбої — "2 год 15 хв",
    "45 хв" чи "менше хвилини", без зайвої точності до секунд."""
    total_minutes = int(seconds // 60)
    if total_minutes < 1:
        return "менше хвилини"
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours} год {minutes} хв"
    if hours:
        return f"{hours} год"
    return f"{minutes} хв"


def _alert_message_siren(oblast_name: str, is_new: bool,
                          channel_link: str | None = None, channel_title: str = "", submit_link: str | None = None,
                          duration_text: str = "") -> str:
    """Фінальний стандарт (п.1-2 ТЗ): лише ❗️/❕, лише область/місто — райони НЕ
    згадуються (п.1.3), навіть якщо NEPTUN дав тривогу на рівні конкретного району.
    п.5.4 ТЗ: коректний відмінок і прийменник ("у Київській області", "у Києві")
    замість буквального "в Назва область". duration_text (лише для відбою) —
    підсумок "Тривога тривала N" перед відбоєм, якщо відомий час початку."""
    where = _oblast_locative(oblast_name)
    if is_new:
        return f"❗️ Повітряна тривога {where}\n\n{_alert_footer(channel_link, channel_title, submit_link)}"
    summary = f"\nТривога тривала {duration_text}" if duration_text else ""
    return f"❕ Відбій повітряної тривоги {where}{summary}\n\n{_alert_footer(channel_link, channel_title, submit_link)}"


def _threat_count_suffix(threat: dict) -> str:
    """Кількість засобів ураження ВСЕРЕДИНІ одного запису NEPTUN (коли API описує
    групу однотипних цілей одним id, наприклад "трійка шахедів" однією позицією
    зі своїм count). Це ІНША сутність, ніж group_count у _threat_movement_text
    (кількість ОКРЕМИХ активних записів, що прямують в один і той же напрямок) —
    обидва варіанти зустрічаються в живих даних NEPTUN, тож рахуємо і показуємо
    обидва, коли вони є."""
    count = threat.get("count")
    if not count or count <= 1:
        return ""
    return f" ({count} од.)"


def _threat_movement_text(threat: dict, where: str, group_count: int = 1) -> str:
    """Чисте оперативне зведення про рух/появу цілі (п.2.2 нового ТЗ) — БЕЗ слова
    "тривога" і без ❗️/❕. п.5.1 ТЗ: кількість цілей, що прямують в одному напрямку,
    видно одразу з формулювання — "3 БпЛА курсом на Х" замість знеособленого
    "БпЛА курсом на Х", коли NEPTUN одночасно веде декілька окремих цілей до
    однієї й тієї ж точки (group_count — підрахунок такого збігу за цей же тік
    моніторингу, рахується в _check_air_alerts_locked по всіх активних записах)."""
    label = _THREAT_TYPE_SHORT.get(threat.get("type"), _THREAT_TYPE_SHORT["unknown"])
    verb = _THREAT_DIRECTION_VERB.get(threat.get("type"), "у районі")
    label_part = f"{group_count} × {label}" if group_count and group_count > 1 else label
    return f"{label_part} {verb} {where}{_threat_count_suffix(threat)}"


def _alert_msg_threat_new(threat: dict, where: str, group_count: int = 1,
                           channel_link: str | None = None, channel_title: str = "", submit_link: str | None = None) -> str:
    """Нова ціль з'явилась в активному списку NEPTUN — оперативне зведення про рух
    (п.2.2 ТЗ), а НЕ повторний старт тривоги: слово "тривога" сюди не потрапляє,
    навіть якщо по цій області вже є активна сирена (п.3.1 ТЗ)."""
    return f"{_threat_movement_text(threat, where, group_count)}\n\n{_alert_footer(channel_link, channel_title, submit_link)}"


def _alert_msg_threat_moved(threat: dict, old_where: str, new_where: str, group_count: int = 1,
                             channel_link: str | None = None, channel_title: str = "", submit_link: str | None = None) -> str:
    """Ціль змінила курс/перемістилась у інший населений пункт. п.5.1 ТЗ вимагає
    "вектори руху та зміну напрямків" — тож, на відміну від просто нового
    місцезнаходження, тут явно показуємо ЗВІДКИ → КУДИ (сам вектор), а не лише
    поточну точку; це так само не окремий/повторний старт тривоги (п.1.1)."""
    label = _THREAT_TYPE_SHORT.get(threat.get("type"), _THREAT_TYPE_SHORT["unknown"])
    label_part = f"{group_count} × {label}" if group_count and group_count > 1 else label
    if old_where and old_where != "?" and old_where != new_where:
        base = f"{label_part} змінив курс: {old_where} → {new_where}{_threat_count_suffix(threat)}"
    else:
        base = _threat_movement_text(threat, new_where, group_count)
    return f"{base}\n\n{_alert_footer(channel_link, channel_title, submit_link)}"


def _alert_msg_threat_countdown(threat: dict, old_count: int, new_count: int, where: str,
                                 channel_link: str | None = None, channel_title: str = "", submit_link: str | None = None) -> str:
    """Кількість цілей у групі зменшилась, угруповання ще активне. На відміну від
    зникнення ОДИНОКОЇ цілі (де причина справді невідома — див. _alert_msg_threat_resolved),
    тут сигнал куди надійніший: якщо частина групи й далі впевнено відстежується
    NEPTUN, а частина зникла саме з ЦІЄЇ групи — найімовірніше пояснення це
    перехоплення, а не втрата сигналу (втрата радара зазвичай "гасить" ціль
    цілком, а не вибірково частину групи). Тому прямо називаємо ймовірну причину
    (з "ймовірно", а не як стовідсотковий факт — NEPTUN це окремо не підтверджує)."""
    label = _THREAT_TYPE_SHORT.get(threat.get("type"), _THREAT_TYPE_SHORT["unknown"])
    verb = _THREAT_DIRECTION_VERB.get(threat.get("type"), "у районі")
    downed = old_count - new_count
    base = f"{label} {verb} {where} — ймовірно збито {downed} од. ППО ({new_count} з {old_count} лишається активними)"
    return f"{base}\n\n{_alert_footer(channel_link, channel_title, submit_link)}"


# п.5.2 ТЗ: причина зникнення цілі з активного списку NEPTUN — якщо API колись
# віддає явне поле результату (наприклад "outcome"/"result"), тут мапимо його на
# людський текст. Явних значень цього поля в публічній документації NEPTUN зараз
# немає, тож мапа — точка розширення на майбутнє; доки поля нема, використовується
# чесний нейтральний фолбек нижче (без вигадування факту "збито ППО", якого API
# не підтвердило, — це було б дезінформацією).
_THREAT_OUTCOME_TEXT = {
    "shot_down": "збито ППО",
    "intercepted": "збито ППО",
    "lost": "зникла з радарів моніторингу",
    "expired": "зникла з радарів моніторингу",
    "landed": "завершила рух (приземлення/падіння)",
    "crashed": "завершила рух (приземлення/падіння)",
}


def _alert_msg_threat_resolved(prev_state: dict, channel_link: str | None = None, channel_title: str = "", submit_link: str | None = None) -> str:
    """Ціль зникла з активного списку NEPTUN — це завершення руху КОНКРЕТНОЇ цілі,
    а НЕ відбій тривоги по області/місту (п.1.2 ТЗ розділяє ці дві події чітко):
    відбій тривоги й надалі шле лише _alert_message_siren, коли по самій області
    закінчується офіційна сирена, незалежно від статусу окремих цілей.
    п.5.2 ТЗ: розгорнутий контекст замість сухого рядка — звідки й куди прямувала
    ціль (якщо відомо) і чим завершився курс, наскільки це видно з даних API.
    Без повторення "курс завершено" / "рух завершено" в одному реченні (це один
    і той самий факт, сказаний двічі різними словами) — статус і причина винесені
    в окремі рядки, кожен каже щось нове."""
    where = prev_state.get("where", "?")
    origin = prev_state.get("origin") or prev_state.get("from")
    label = _THREAT_TYPE_SHORT.get(prev_state.get("type"), _THREAT_TYPE_SHORT["unknown"])
    outcome = _THREAT_OUTCOME_TEXT.get(prev_state.get("outcome") or prev_state.get("result"))
    if outcome is None:
        # Одне слово "ймовірно" — достатній і чесний застереження, без нагромадження
        # другого альтернативного варіанту й технічної приписки про NEPTUN в тому ж
        # реченні: саме стек із кількох застережень одразу читається людьми як
        # "незрозуміло взагалі що сталось", а не як обережна, але ясна заява.
        outcome = "ймовірно збито ППО"
    route = f"{origin} → {where}" if origin else where
    return f"{label} ({route}) — {outcome}\n\n{_alert_footer(channel_link, channel_title, submit_link)}"


async def check_air_alerts(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Раз на 10с (майже реальний час, п.2 ТЗ — моніторинг через neptun.in.ua) опитує офіційні тривоги
    (сирена по районах/областях) і, для каналів що це замовили, конкретні загрози
    (шахед/ракета/КАБ) з фільтром типів — і шле сповіщення тільки про ЗМІНУ стану.

    п.5.5 ТЗ: увесь тік обгорнуто в `deduplicator.tick_lock()` — якщо попередній
    виклик цієї ж job (напр. через повільну мережу) ще не завершився, новий тік
    одразу виходить, замість накладання поверх старого (це і є причина, з якої
    без локу те саме сповіщення могло піти 4-5 разів поспіль)."""
    with deduplicator.tick_lock("air_alerts_tick") as acquired:
        if not acquired:
            return
        await _check_air_alerts_locked(context)


async def _check_air_alerts_locked(context: ContextTypes.DEFAULT_TYPE) -> None:
    channel_settings = storage.get_all_channel_alert_settings()
    if not channel_settings:
        return

    # --- Офіційна тривога/відбій по областях і районах ---
    siren_channels = {cid: s for cid, s in channel_settings.items() if s.get("notify_siren")}
    if siren_channels:
        data = await _neptun_fetch(NEPTUN_ALERTS_URL)
        if data is not None:
            current_keys = {}
            for r in data.get("raions", []):
                current_keys[r["key"]] = {"oblast": r.get("oblast", ""), "district": r.get("name", "")}
            for o in data.get("oblasts", []):
                current_keys[o["key"]] = {"oblast": o.get("name", ""), "district": None}

            known = storage.get_known_active_alert_keys()
            new_keys = set(current_keys) - known
            resolved_keys = known - set(current_keys)

            for key in new_keys:
                info = current_keys[key]
                storage.set_setting(f"alert_key_started_at:{key}", datetime.now().isoformat())
                for cid, s in siren_channels.items():
                    if info["oblast"] in s.get("oblasts", []):
                        channel_link, channel_title, submit_link = await _get_alert_context(context.bot, cid)
                        text = _alert_message_siren(
                            info["oblast"], is_new=True,
                            channel_link=channel_link, channel_title=channel_title, submit_link=submit_link,
                        )
                        await _safe_send_alert(context.bot, cid, text)
            for key in resolved_keys:
                # Область/район уже не в поточному знімку — беремо назву з попереднього кешу.
                cached = storage.get_setting(f"alert_key_name:{key}", {})
                started_at = storage.get_setting(f"alert_key_started_at:{key}")
                duration_text = ""
                if started_at:
                    try:
                        duration_text = _format_alert_duration((datetime.now() - datetime.fromisoformat(started_at)).total_seconds())
                    except Exception:
                        duration_text = ""
                for cid, s in siren_channels.items():
                    if cached.get("oblast") in s.get("oblasts", []):
                        channel_link, channel_title, submit_link = await _get_alert_context(context.bot, cid)
                        text = _alert_message_siren(
                            cached.get("oblast", key), is_new=False,
                            channel_link=channel_link, channel_title=channel_title, submit_link=submit_link,
                            duration_text=duration_text,
                        )
                        await _safe_send_alert(context.bot, cid, text)

            for key, info in current_keys.items():
                storage.set_setting(f"alert_key_name:{key}", info)
            storage.set_known_active_alert_keys(set(current_keys))

    # --- Конкретні загрози (БпЛА/ракети/КАБ) з фільтром типів, лише для каналів, що замовили ---
    # Жива стрічка (за зразком реальних каналів-моніторингів): не одне повідомлення на
    # ціль назавжди, а короткі апдейти щоразу, коли щось РЕАЛЬНО змінюється —
    # з'явилась / перемістилась у інший населений пункт / кількість зменшилась
    # (одну з групи збили) / ціль зникла з активного списку ("відбій").
    threat_channels = {cid: s for cid, s in channel_settings.items() if s.get("notify_threats")}
    if threat_channels:
        data = await _neptun_fetch(NEPTUN_THREATS_URL)
        if data is not None:
            active_threats = [t for t in data.get("threats", []) if t.get("id") and t.get("status") == "active"]
            # п.5.1 ТЗ: скільки ОКРЕМИХ активних цілей зараз прямують в один і той
            # самий населений пункт (той самий тип+область+напрямок) — рахуємо по
            # всьому поточному тіку одразу, щоб у тексті було не знеособлене
            # "БпЛА курсом на Х", а "3 БпЛА курсом на Х", коли це справді збіг.
            where_group_counts = Counter(
                (t.get("region", ""), t.get("type", "unknown"), t.get("locality") or t.get("region") or "?")
                for t in active_threats
            )
            current_ids = set()
            for threat in active_threats:
                tid = threat.get("id")
                current_ids.add(tid)
                where = threat.get("locality") or threat.get("region") or "?"
                region = threat.get("region", "")
                ttype = threat.get("type", "unknown")
                count = threat.get("count") or 0
                # group_count — за ОРИГІНАЛЬНОЮ локацією (де where_group_counts і
                # побудовано вище): порівняння в межах Києва точніше, коли обидва боки
                # рахують по одному й тому самому ключу "Київ", а не по різних районах.
                group_count = where_group_counts.get((region, ttype, where), 1)
                # Якщо ціль летить над самим Києвом — уточнюємо конкретний район
                # (Дарницький/Дніпровський/...) через reverse-geocoding: NEPTUN дає
                # лише "м. Київ" цілком, а для мільйонного міста це замало.
                if region == "м. Київ" or where in ("Київ", "м. Київ"):
                    district = await _kyiv_district(threat.get("lat"), threat.get("lon"))
                    if district:
                        where = district
                prev = storage.get_threat_state(tid)
                matching_channels = [
                    cid for cid, s in threat_channels.items()
                    if region in s.get("oblasts", []) and ttype in s.get("types", [])
                ]

                if prev is None:
                    for cid in matching_channels:
                        channel_link, channel_title, submit_link = await _get_alert_context(context.bot, cid)
                        text = _alert_msg_threat_new(
                            threat, where, group_count=group_count,
                            channel_link=channel_link, channel_title=channel_title, submit_link=submit_link,
                        )
                        await _send_threat_alert(context.bot, cid, threat_channels[cid], threat, text)
                elif prev.get("where") != where:
                    for cid in matching_channels:
                        channel_link, channel_title, submit_link = await _get_alert_context(context.bot, cid)
                        text = _alert_msg_threat_moved(
                            threat, prev.get("where", "?"), where, group_count=group_count,
                            channel_link=channel_link, channel_title=channel_title, submit_link=submit_link,
                        )
                        await _send_threat_alert(context.bot, cid, threat_channels[cid], threat, text)
                elif prev.get("count") and count and count < prev["count"]:
                    for cid in matching_channels:
                        channel_link, channel_title, submit_link = await _get_alert_context(context.bot, cid)
                        text = _alert_msg_threat_countdown(
                            threat, prev["count"], count, where,
                            channel_link=channel_link, channel_title=channel_title, submit_link=submit_link,
                        )
                        await _send_threat_alert(context.bot, cid, threat_channels[cid], threat, text)

                storage.set_threat_state(tid, {
                    "where": where, "region": region, "type": ttype, "count": count,
                    "advisory": threat.get("advisory", False),
                    # п.5.2 ТЗ: якщо NEPTUN колись почне віддавати точку старту руху
                    # цілі — підхоплюємо для маршруту у "курс завершено"; поки таких
                    # полів у відповіді немає, просто залишиться None (без вигадок).
                    "origin": threat.get("origin") or threat.get("from"),
                    # Координати й trail — щоб карта руху цілі (show_threat_map) могла
                    # намалюватись і на повідомленні "курс завершено" (відбій нижче),
                    # коли ціль уже зникла з активного списку й у самому threat-об'єкті
                    # свіжих координат більше немає.
                    "lat": threat.get("lat"), "lon": threat.get("lon"), "trail": threat.get("trail"),
                })

            # Цілі, що зникли з активного списку відколи ми перевіряли востаннє — "відбій".
            for tid in set(storage.get_all_threat_state_ids()) - current_ids:
                prev = storage.get_threat_state(tid)
                if not prev:
                    continue
                matching_channels = [
                    cid for cid, s in threat_channels.items()
                    if prev.get("region") in s.get("oblasts", []) and prev.get("type") in s.get("types", [])
                ]
                for cid in matching_channels:
                    channel_link, channel_title, submit_link = await _get_alert_context(context.bot, cid)
                    text = _alert_msg_threat_resolved(prev, channel_link=channel_link, channel_title=channel_title, submit_link=submit_link)
                    await _send_threat_alert(context.bot, cid, threat_channels[cid], prev, text)
                storage.remove_threat_state(tid)


_PUSH_STRIP_TAGS_RE = re.compile(r"<[^>]+>")


def _push_notify_alert(chat_id: int, text: str) -> None:
    """Дублює щойно надіслану тривогу як Web Push власнику/команді каналу
    (best-effort — якщо push не налаштовано чи ніхто не підписаний, просто
    нічого не станеться, публікація самої тривоги в канал це не зачіпає)."""
    try:
        admin_ids = storage.get_admin_ids_for_channel(chat_id)
        if not admin_ids:
            return
        plain = _PUSH_STRIP_TAGS_RE.sub("", text).strip()
        body = plain[:150] + ("…" if len(plain) > 150 else "")
        push_module.send_push_to_admins(admin_ids, "🚨 Тривога", body, url="/", tag=f"alert-{chat_id}")
    except Exception as e:
        logger.warning(f"[PUSH] Не вдалося розіслати push про тривогу в {chat_id}: {e}")


async def _safe_send_alert(bot, chat_id: int, text: str) -> None:
    # п.5.5 ТЗ: страхувальний дедуп на рівні конкретного повідомлення — навіть
    # якщо tick_lock() з якоїсь причини не спрацював (напр. кілька процесів
    # воркера), той самий текст для того самого каналу повторно не піде.
    if deduplicator.is_duplicate(chat_id, text):
        logger.info(f"Сповіщення для {chat_id} — дублікат за останні {deduplicator.DEDUP_TTL_SECONDS}с, пропускаємо (п.5.5 ТЗ)")
        return
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", disable_web_page_preview=True)
        storage.log_alert_sent(chat_id)
        _push_notify_alert(chat_id, text)
    except RetryAfter as e:
        await asyncio.sleep(e.retry_after + 1)
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", disable_web_page_preview=True)
            storage.log_alert_sent(chat_id)
            _push_notify_alert(chat_id, text)
        except Exception as e2:
            logger.warning(f"Не вдалося надіслати сповіщення тривоги у {chat_id} (retry): {e2}")
            storage.log_error(f"Сповіщення тривоги у {chat_id} (retry): {e2}")
    except Exception as e:
        logger.warning(f"Не вдалося надіслати сповіщення тривоги у {chat_id}: {e}")
        storage.log_error(f"Сповіщення тривоги у {chat_id}: {e}")


async def _safe_send_alert_photo(bot, chat_id: int, photo_bytes: bytes, caption: str) -> None:
    """Той самий дедуп/retry-захист, що й _safe_send_alert, але для карти руху
    цілі — фото з текстом як підпис замість звичайного текстового повідомлення."""
    if deduplicator.is_duplicate(chat_id, caption):
        logger.info(f"Сповіщення для {chat_id} — дублікат за останні {deduplicator.DEDUP_TTL_SECONDS}с, пропускаємо (п.5.5 ТЗ)")
        return
    try:
        await bot.send_photo(chat_id=chat_id, photo=photo_bytes, caption=caption, parse_mode="HTML")
        storage.log_alert_sent(chat_id)
        _push_notify_alert(chat_id, caption)
    except RetryAfter as e:
        await asyncio.sleep(e.retry_after + 1)
        try:
            await bot.send_photo(chat_id=chat_id, photo=photo_bytes, caption=caption, parse_mode="HTML")
            storage.log_alert_sent(chat_id)
            _push_notify_alert(chat_id, caption)
        except Exception as e2:
            logger.warning(f"Не вдалося надіслати карту руху цілі у {chat_id} (retry): {e2}")
            storage.log_error(f"Карта руху цілі у {chat_id} (retry): {e2}")
    except Exception as e:
        logger.warning(f"Не вдалося надіслати карту руху цілі у {chat_id}: {e}")
        storage.log_error(f"Карта руху цілі у {chat_id}: {e}")


async def _send_threat_alert(bot, chat_id: int, settings: dict, threat: dict, text: str) -> None:
    """Єдина точка відправки сповіщення про КОНКРЕТНУ ціль (на відміну від
    сирени/відбою по області — там координат немає). Якщо власник каналу
    увімкнув "Карта руху цілі" (show_threat_map) і в threat є координати —
    шле фото-карту з текстом як підпис; інакше (чи якщо рендер карти зірвався
    з будь-якої причини — тайли OSM недоступні тощо) — звичайний текст, як
    і раніше, щоб сповіщення НІКОЛИ не губилось через проблему з картою."""
    if settings.get("show_threat_map"):
        photo = _render_threat_map(threat)
        if photo:
            await _safe_send_alert_photo(bot, chat_id, photo, text)
            return
    await _safe_send_alert(bot, chat_id, text)


async def send_test_alert(bot, chat_id: int) -> None:
    """Тестова кнопка (п.2 ТЗ) — надсилає ОЧЕВИДНО позначений тестовий сигнал, щоб
    адмін перевірив форматування й доставку, не сплутавши його зі справжньою тривогою."""
    channel_link, channel_title, submit_link = await _get_alert_context(bot, chat_id)
    text = f"🧪 ТЕСТОВЕ ПОВІДОМЛЕННЯ, це НЕ реальна тривога\n\n{_alert_footer(channel_link, channel_title, submit_link)}"
    await _safe_send_alert(bot, chat_id, text)


async def _download_bot_file_bytes(bot, file_id: str) -> bytes | None:
    """Завантажує файл за Telegram file_id (на відміну від _download_media_bytes,
    який тягне за URL) — потрібно для фото/відео з джерел, де бот сам є учасником
    чату (тип "telegram"), бо там медіа приходить як file_id, а не посилання."""
    try:
        file = await bot.get_file(file_id)
        buf = io.BytesIO()
        await file.download_to_memory(buf)
        return buf.getvalue()
    except Exception as e:
        logger.warning(f"Не вдалося завантажити файл {file_id}: {e}")
        return None


async def _enqueue_source_news(context: ContextTypes.DEFAULT_TYPE, source: dict, media_items: list, caption_html: str | None, post_date) -> None:
    """Спільна логіка тексту+дедупу+enqueue для новини з джерела — використовується і
    для одиночного поста, і для фіналізованого альбому (Гілка 1 on_any_channel_post),
    щоб не дублювати її двічі."""
    if post_date and not _is_post_fresh(post_date):
        return  # застарілий пост (бот наздоганяє пропущене після простою)

    text_html = ""
    if caption_html:
        soup = BeautifulSoup(caption_html, "html.parser")
        text_html = _tg_html_from_nodes(list(soup.children))
        text_html = _strip_source_signature(text_html.strip())

    owner_lang = storage.get_admin_language(source.get("added_by")) if source.get("added_by") else "ua"
    if text_html:
        text_html = await _translate_html(text_html, owner_lang)
    title = re.sub(r"<[^>]+>", "", text_html).split("\n")[0][:200] if text_html else (media_items and "Новина з медіа" or "")
    if not title and not media_items:
        return  # ні тексту, ні медіа — реально нічого публікувати
    norm_title = _normalize_title(title)
    title_lower = title.lower()

    news_channels = [
        ch for ch in storage.get_active_channels()
        if ch.get("news_enabled") and ch.get("added_by") == source.get("added_by")
    ]
    channel_ids_to_enqueue = [
        ch["id"] for ch in news_channels
        if not ch.get("news_keywords") or any(kw in title_lower for kw in ch["news_keywords"])
    ]
    if not channel_ids_to_enqueue:
        return

    comparison_pool = []
    for cid in channel_ids_to_enqueue:
        comparison_pool.extend(storage.get_channel_recent_titles(cid))
        comparison_pool.extend(storage.get_channel_queued_titles(cid))

    source_is_editorial = source.get("category") == "editorial_chat"
    is_dup = (not source_is_editorial) and bool(text_html) and (
        _is_similar_title(norm_title, comparison_pool) or await _llm_is_duplicate(title, comparison_pool)
    )
    if is_dup:
        logger.info(f"Пропущено як дублікат: {title}")
        return

    base_text = f"⚡ {text_html}" if text_html else "⚡"
    queue_item = storage.enqueue_news(
        title, base_text, [], source.get("name", "Telegram"), channel_ids_to_enqueue,
        norm_title=norm_title, priority=source_is_editorial,
    )
    if media_items:
        media_paths = _save_media_to_queue_disk(queue_item["id"], media_items)
        if media_paths:
            storage.update_queue_item(queue_item["id"], media_paths=media_paths)
    await _process_publish_queue(context.bot)


async def _enqueue_source_sticker(context: ContextTypes.DEFAULT_TYPE, source: dict, sticker_file_id: str, post_date) -> None:
    """Стікер із джерела-каналу — але ретранслюємо лише стікери, які редакція сама
    надіслала в "Редакційний чат" (свій контент). Стікери з чужих скрапнутих
    новинних каналів (звичайні джерела) — це декоративний / чужий контент донора,
    його НЕ публікуємо в канали, інакше в стрічку летить чужа "розважалка"
    без жодного відношення до новини."""
    if source.get("category") != "editorial_chat":
        return
    if post_date and not _is_post_fresh(post_date):
        return
    news_channels = [
        ch for ch in storage.get_active_channels()
        if ch.get("news_enabled") and ch.get("added_by") == source.get("added_by")
    ]
    channel_ids = [ch["id"] for ch in news_channels]
    if not channel_ids:
        return
    queue_item = storage.enqueue_news(
        "Стікер", "", [], source.get("name", "Telegram"), channel_ids, priority=True,
    )
    storage.update_queue_item(queue_item["id"], sticker_file_id=sticker_file_id)
    await _process_publish_queue(context.bot)


async def _on_source_album_ready(batches: list, caption_html, context_data: dict, ptb_context) -> None:
    """on_ready-колбек для source_album_collector — те саме, що й для читацьких
    предложок, тільки результат іде не в submissions, а одразу в чергу
    автопостингу через _enqueue_source_news."""
    source = context_data["source"]
    post_date = context_data["date"]
    for batch in batches:
        media_items = []
        for it in batch:
            b = await _download_bot_file_bytes(ptb_context.bot, it.file_id)
            if b:
                media_items.append({"type": it.kind, "bytes": b})
        await _enqueue_source_news(ptb_context, source, media_items, caption_html, post_date)


source_album_collector = media_collector.MediaGroupCollector(
    name="source_posts", on_ready=_on_source_album_ready,
)


async def on_any_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Єдиний обробник подій channel_post (Telegram дозволяє лише один такий хендлер на апдейт):
    1) якщо канал зареєстрований як джерело новин — ретранслює новину підписаним каналам;
    2) якщо канал є ВЛАСНИМ каналом якогось адміна — пасивно накопичує зразок посту для аналізу стилю
       (заміна «сканування історії», яке Bot API не підтримує — працює тільки для нових постів)."""
    post = update.channel_post
    if not post:
        return

    # Захист від зациклення: не реагуємо на власні пости бота
    if post.from_user and post.from_user.id == context.bot.id:
        return

    # --- Гілка 1: джерело новин ---
    source = storage.get_telegram_source_by_chat_id(post.chat.id)
    if source:
        logger.info(f"[PARSER] Received message from source_id: {post.chat.id}")

        # Альбом (кілька фото/відео в одному пості джерела) — буферизуємо ТОЧНО так само,
        # як для предложок від читачів (media_collector.MediaGroupCollector нижче): до цього
        # виправлення сюди долітав лише текст першого апдейту, а фото/відео взагалі не
        # бралися — саме це й було причиною "альбоми не переносяться з новин".
        if post.media_group_id and (post.photo or post.video):
            kind = "photo" if post.photo else "video"
            file_id = post.photo[-1].file_id if post.photo else post.video.file_id
            caption_html = post.caption_html or (html_lib.escape(post.caption) if post.caption else None)
            source_album_collector.add(
                job_queue=context.job_queue,
                group_id=post.media_group_id,
                message_id=post.message_id,
                kind=kind,
                file_id=file_id,
                caption_html=caption_html,
                context_data={"source": source, "date": post.date},
            )
            return  # канал є або джерелом, або власним — не обидва одразу

        # Стікер (звичайний чи кастомний, статичний чи анімований) — раніше взагалі
        # не читався (перевірялись лише photo/video), тож мовчки губився. Стікер не
        # можна перетворити на photo/video чи накласти водяний знак, тож іде окремим
        # шляхом одразу в чергу й публікується через send_sticker (той самий file_id
        # цілком можна повторно використати в іншому чаті цим самим ботом).
        if post.sticker:
            await _enqueue_source_sticker(context, source, post.sticker.file_id, post.date)
            return

        # Одиночне фото/відео (не альбом) — раніше просто ігнорувалось без тексту.
        media_items = []
        if post.photo or post.video:
            file_id = post.photo[-1].file_id if post.photo else post.video.file_id
            b = await _download_bot_file_bytes(context.bot, file_id)
            if b:
                media_items.append({"type": "video" if post.video else "photo", "bytes": b})

        caption_html = post.text_html or post.caption_html
        if caption_html or media_items:
            await _enqueue_source_news(context, source, media_items, caption_html, post.date)
        return  # канал є або джерелом, або власним — не обидва одразу

    # --- Гілка 2: пасивний збір стилю власного каналу ---
    own_channel = next((c for c in storage.get_channels() if c["id"] == post.chat.id), None)
    if not own_channel or not own_channel.get("added_by"):
        return

    text_content = post.text or post.caption
    if not text_content:
        return

    entities = post.entities or post.caption_entities or []
    has_bold_start = any(e.type == "bold" and e.offset == 0 for e in entities)
    has_link = any(e.type in ("text_link", "url") for e in entities)
    storage.add_style_sample(post.chat.id, text_content, has_bold_start, has_link)


async def _prime_seen_news() -> None:
    """Для каждого нового источника запоминает текущие новости без отправки,
    чтобы не разослать всю старую ленту разом при первом подключении фида."""
    primed = set(storage.get_primed_feeds())
    for source in storage.get_active_rss_sources():
        feed_url = source["url"]
        if feed_url in primed:
            continue
        try:
            feed = await _fetch_feed(feed_url)
        except Exception:
            continue
        for entry in feed.entries:
            storage.add_seen_news(entry.link)
        storage.mark_feed_primed(feed_url)


async def _set_commands(application: Application) -> None:
    await _prime_seen_news()
    await application.bot.set_my_commands([
        BotCommand("start", "Привітання"),
        BotCommand("menu", "Головне меню на кнопках"),
        BotCommand("help", "Список команд"),
        BotCommand("channels", "Список каналів розсилки"),
        BotCommand("removechannel", "Видалити канал зі списку"),
        BotCommand("newsfilter", "Фільтр новин за ключовими словами"),
        BotCommand("sources", "Керування джерелами новин"),
        BotCommand("addsource", "Додати нове джерело новин (RSS)"),
    ])


async def on_bot_added_to_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Автоматически регистрирует канал, если боту дали права администратора.
    Сохраняет chat_id, title, user_id того, хто додав бота, і права бота в каналі.
    Якщо бота видалили/розжалували — статус каналу міняється на 'inactive' (без видалення даних).

    ВАЖЛИВО: розгалуження по chat.type — ПЕРШЕ, що робить ця функція, до будь-
    якого storage.* виклику. Групи (chat.type "group"/"supergroup") призначені
    для модерації (moderation.py) і повністю ізольовані від логіки нижче —
    жоден storage.add_channel для групи ніколи не викликається (ключова вимога
    ТЗ про ізоляцію модерації від списків джерел)."""
    result = update.my_chat_member
    if not result:
        return

    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status
    chat = result.chat
    added_by_user_id = result.from_user.id if result.from_user else None

    if chat.type in ("group", "supergroup"):
        await moderation.on_moderation_chat_membership_change(chat, old_status, result.new_chat_member, context)
        return

    if new_status == ChatMemberStatus.ADMINISTRATOR and old_status != ChatMemberStatus.ADMINISTRATOR:
        member = result.new_chat_member
        rights = {
            "can_post_messages": getattr(member, "can_post_messages", None),
            "can_edit_messages": getattr(member, "can_edit_messages", None),
            "can_delete_messages": getattr(member, "can_delete_messages", None),
            "can_invite_users": getattr(member, "can_invite_users", None),
            "can_restrict_members": getattr(member, "can_restrict_members", None),
            "can_pin_messages": getattr(member, "can_pin_messages", None),
            "can_promote_members": getattr(member, "can_promote_members", None),
            "can_manage_chat": getattr(member, "can_manage_chat", None),
            "can_manage_video_chats": getattr(member, "can_manage_video_chats", None),
            "is_anonymous": getattr(member, "is_anonymous", None),
        }

        is_new = storage.add_channel(chat.id, chat.title or str(chat.id), added_by=added_by_user_id, rights=rights)
        logger.info(
            f"Канал зареєстровано: {chat.title} ({chat.id}), новий: {is_new}, "
            f"додав: {added_by_user_id}, права: {rights}"
        )
        if is_new:
            try:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text="✅ Бот сповіщень про тривогу підключено до цього каналу.",
                )
            except Exception:
                pass

    elif new_status in (ChatMemberStatus.LEFT, _CHAT_MEMBER_KICKED_STATUS):
        storage.set_channel_status(chat.id, "inactive")
        logger.info(f"Бота видалено з каналу {chat.title} ({chat.id}) — статус змінено на inactive")


_MEMBER_ACTIVE_STATUSES = {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER, ChatMemberStatus.RESTRICTED}
_MEMBER_INACTIVE_STATUSES = {ChatMemberStatus.LEFT, _CHAT_MEMBER_KICKED_STATUS}


async def on_channel_member_change(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Підписався/відписався звичайний читач каналу (п.2.2 ТЗ: графік «Підписники»
    з роздільним підрахунком «Подписались»/«Отписались»). Приходить лише для
    каналів, де бот — адміністратор з правом бачити учасників; спрацьовує
    окремо від on_bot_added_to_chat, який відстежує зміну статусу САМОГО бота."""
    result = update.chat_member
    if not result:
        return
    chat = result.chat
    if not any(c["id"] == chat.id for c in storage.get_channels()):
        return  # канал не зареєстровано в системі — не рахуємо його статистику

    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status
    if old_status == new_status:
        return

    if old_status in _MEMBER_INACTIVE_STATUSES and new_status in _MEMBER_ACTIVE_STATUSES:
        storage.record_member_event(chat.id, "joined")
    elif old_status in _MEMBER_ACTIVE_STATUSES and new_status in _MEMBER_INACTIVE_STATUSES:
        storage.record_member_event(chat.id, "left")


async def snapshot_channel_growth_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Раз на добу фіксує загальну кількість підписників кожного активного
    каналу — це і є ряд даних для блоку «Ріст / Загальна динаміка» (п.2.2 ТЗ),
    незалежний від точкових подій приєднання/відходу."""
    for ch in storage.get_channels():
        if ch.get("status") == "inactive":
            continue
        try:
            total = await context.bot.get_chat_member_count(ch["id"])
            storage.record_growth_snapshot(ch["id"], total)
        except Exception as e:
            logger.warning(f"Не вдалося зняти щоденний знімок підписників {ch['id']}: {e}")


def build_application() -> Application:
    """Создаёт и настраивает Application бота (без запуска polling)."""
    application = Application.builder().token(BOT_TOKEN).post_init(_set_commands).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("setbotphoto", set_bot_photo))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("channels", list_channels))
    application.add_handler(CommandHandler("removechannel", remove_channel))
    application.add_handler(CommandHandler("newsfilter", news_filter))
    application.add_handler(CommandHandler("sources", list_sources))
    application.add_handler(CommandHandler("addsource", add_source))
    application.add_handler(CommandHandler("addtgsource", add_telegram_source_start))

    # ---- Команди модерації груп (moderation.py) — filters.ChatType.GROUPS гарантує,
    # що ці хендлери навіть не спрацюють у приватних чатах чи каналах; жодного
    # зв'язку зі списками джерел/каналів вище (ключова вимога ТЗ про ізоляцію). ----
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
    # Автомодерація (флуд/заборонені слова) — фоновий обробник звичайних повідомлень
    # групи, реально щось робить лише якщо адмін явно увімкнув /antispam on.
    # ~filters.FORWARDED — щоб не перехоплювати пересилання повідомлень з каналів
    # у групі раніше за on_forwarded_from_channel нижче (реєстрація каналу форвардом).
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND & ~filters.FORWARDED, moderation.on_group_message,
    ))

    reader_content_filter = (
        filters.ChatType.PRIVATE
        & (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.LOCATION)
        & ~filters.COMMAND
        & ~filters.FORWARDED
    )
    application.add_handler(MessageHandler(reader_content_filter, on_reader_submission))
    application.add_handler(MessageHandler(filters.FORWARDED, on_forwarded_from_channel))
    application.add_handler(ChatMemberHandler(on_bot_added_to_chat, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(ChatMemberHandler(on_channel_member_change, ChatMemberHandler.CHAT_MEMBER))
    application.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, on_any_channel_post))
    application.add_handler(CallbackQueryHandler(on_menu_button, pattern=r"^menu:"))
    application.add_handler(CallbackQueryHandler(on_source_button, pattern=r"^src(toggle|del):"))
    application.add_handler(CallbackQueryHandler(on_channel_button))

    application.job_queue.run_repeating(check_news, interval=NEWS_CHECK_INTERVAL_SECONDS, first=30)
    application.job_queue.run_repeating(publish_from_queue, interval=20, first=20)
    application.job_queue.run_repeating(cleanup_queue_job, interval=300, first=60)
    application.job_queue.run_repeating(check_scheduled_posts, interval=30, first=30)
    application.job_queue.run_repeating(check_air_alerts, interval=10, first=10)
    application.job_queue.run_daily(snapshot_channel_growth_job, time=dtime(hour=0, minute=5))
    return application


def main() -> None:
    application = build_application()
    logger.info("Бот запущено, очікую на команди...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()