import asyncio
import logging
import os
import threading
import time
import uuid
from datetime import datetime

# Рекомендовані публічні TG-джерела про війну й політику (п. запиту адміна) —
# перевірено вручну (реальні username, підтверджені пошуком), щоб не пропонувати
# неробочі/вигадані канали. Список статичний — адмін просто тисне "Додати".
RECOMMENDED_WAR_POLITICS_SOURCES = [
    {"name": "Труха Україна", "username": "truexanewsua"},
    {"name": "Zelenskiy / Official", "username": "V_Zelenskiy_official"},
    {"name": "Pravda Gerashchenko", "username": "Pravda_Gerashchenko"},
    {"name": "DeepState", "username": "DeepStateUA"},
    {"name": "Повітряні Сили ЗС України", "username": "kpszsu"},
    {"name": "Оперативний ЗСУ", "username": "operativnoZSU"},
    {"name": "Служба безпеки України (СБУ)", "username": "SBUkr"},
    {"name": "Генеральний штаб ЗСУ", "username": "GeneralStaffZSU"},
    {"name": "Міністерство оборони України", "username": "ministry_of_defense_ua"},
    {"name": "АрміяInform", "username": "armyofukraine"},
    {"name": "Українська правда", "username": "ukrpravda_news"},
    {"name": "УП", "username": "ukr_pravda"},
    {"name": "Радіо Свобода", "username": "svoboda_radio"},
    {"name": "Схеми (Радіо Свобода)", "username": "cxemu"},
    {"name": "Громадське радіо", "username": "HromadskeRadioNews"},
    {"name": "InformNapalm", "username": "informnapalm"},
    {"name": "Новини Еспресо.TV", "username": "espresotb"},
    {"name": "24 Канал", "username": "channel24_ua"},
    {"name": "Цензор.НЕТ", "username": "censor_net"},
    {"name": "Бутусов Плюс", "username": "ButusovPlus"},
    {"name": "STERNENKO", "username": "ssternenko"},
]

import httpx
import feedparser
from flask import Flask, request, jsonify, send_from_directory, Response
from telegram import Bot

from core import bot as bot_module
from data import storage
from data.webapp_auth import validate_init_data
from services import push as push_module

BOT_TOKEN = bot_module.BOT_TOKEN
SUPERADMIN_IDS = [1453368273]  # тех-розділ бачить і може відкрити тільки цей ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# core/ -> корінь проекту, де реально лежить папка webapp/ (сама вона не переїжджала).
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WEBAPP_DIR = os.path.join(_PROJECT_ROOT, "webapp")

app = Flask(__name__, static_folder=_WEBAPP_DIR, static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024  # 30 МБ — запобіжник від OOM на великих аплоадах від читачів


@app.errorhandler(Exception)
def handle_any_exception(e):
    """Гарантія: НІЯКА помилка в будь-якому ендпоінті не поверне HTML-сторінку —
    завжди JSON, щоб фронтенд міг показати справжню причину, а не тихо зламатись
    на спробі розпарсити не-JSON відповідь."""
    import traceback
    tb = traceback.format_exc()
    logger.error(f"Необроблений виняток на {request.path}: {e}\n{tb}")
    try:
        storage.log_error(f"{request.path}: {e}")
    except Exception:
        pass
    status = getattr(e, "code", 500) if hasattr(e, "code") and isinstance(getattr(e, "code"), int) else 500
    return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), status

BOT_USERNAME = None
BOT_NAME = None


def _fetch_bot_username() -> None:
    """Получает username і ім'я бота один раз при старті, щоб віддавати панелі
    (заголовок топбару — реальне ім'я бота, а не статичний текст)."""
    global BOT_USERNAME, BOT_NAME
    try:
        me = asyncio.run(Bot(token=BOT_TOKEN).get_me())
        BOT_USERNAME = me.username
        BOT_NAME = me.first_name
        logger.info(f"Username бота: @{BOT_USERNAME}")
    except Exception as e:
        logger.warning(f"Не вдалося отримати username бота: {e}")


def run_bot_in_background() -> None:
    """Запускает Telegram-бота (polling) в окремому потоці зі своїм event loop.
    Обгорнуто в захист: якщо polling впаде (найчастіша причина — Conflict: десь
    уже запущений інший екземпляр цього самого бота з тим самим токеном) — це
    більше НЕ тихо вбиває потік непомітно. Помилка йде в лог (видно в панелі,
    "Тех.розділ" → "Останні помилки"), і бот пробує перезапуститись сам."""
    asyncio.set_event_loop(asyncio.new_event_loop())
    attempt = 0
    while True:
        attempt += 1
        try:
            application = bot_module.build_application()
            logger.info(f"Бот запущено у фоновому потоці (спроба {attempt})...")
            application.run_polling(allowed_updates=None, stop_signals=None)
            break  # run_polling завершився штатно (зупинка бота) — не рестартуємо
        except Exception as e:
            logger.error(f"Бот у фоновому потоці впав: {e}", exc_info=True)
            try:
                storage.log_error(f"Бот-процес впав і перезапускається: {e}")
            except Exception:
                pass
            time.sleep(10)  # пауза перед рестартом — щоб не спамити спробами при стійкій помилці (напр. Conflict)


def check_admin(req) -> int | None:
    """Проверяет лише справжність підпису initData (запит дійсно прийшов із Telegram WebApp).
    Доступ до панелі відкритий для БУДЬ-ЯКОГО користувача Telegram — це дає можливість людині,
    яка ще не додала жодного каналу, зайти й додати перший. Ізоляція даних (хто що бачить)
    забезпечується не тут, а фільтрами get_channels_with_role_for_admin / get_submissions_for_admin
    та guard-перевірками require_role у кожному ендпоінті."""
    init_data = req.headers.get("X-Init-Data", "")
    parsed = validate_init_data(init_data, BOT_TOKEN)
    if not parsed:
        return None
    import json
    user = json.loads(parsed.get("user", "{}"))
    user_id = user.get("id")
    return user_id or None


def _parse_init_data_user(req) -> dict:
    """Той самий розбір initData, що й у check_admin, але повертає ПОВНИЙ словник
    user (id/first_name/username/photo_url), а не лише id — для кешу профілів
    (див. cache_user_profile)."""
    init_data = req.headers.get("X-Init-Data", "")
    parsed = validate_init_data(init_data, BOT_TOKEN)
    if not parsed:
        return {}
    import json
    return json.loads(parsed.get("user", "{}"))


def check_superadmin(req) -> int | None:
    """Middleware-перевірка для тех-розділу: тільки user_id зі SUPERADMIN_IDS."""
    init_data = req.headers.get("X-Init-Data", "")
    parsed = validate_init_data(init_data, BOT_TOKEN)
    if not parsed:
        return None
    import json
    user = json.loads(parsed.get("user", "{}"))
    user_id = user.get("id")
    if user_id in SUPERADMIN_IDS:
        return user_id
    return None


def _auth_error_response():
    """403 при провалі check_admin/check_superadmin (п.4 ТЗ) — розрізняє дві причини,
    щоб фронтенд показав правильну підказку, а не загальне "щось пішло не так":
    (1) заголовок X-Init-Data взагалі не прийшов — клієнтський баг/застосунок
    відкрито не з Telegram; (2) initData прийшов, але підпис невалідний/застарілий —
    сесію треба перевідкрити."""
    init_data = request.headers.get("X-Init-Data", "")
    if not init_data:
        return jsonify({
            "error": "forbidden", "reason": "no_init_data",
            "message": "Немає даних сесії Telegram WebApp — застосунок відкрито не з Telegram, або заголовок X-Init-Data не надіслано",
        }), 403
    return jsonify({
        "error": "forbidden", "reason": "invalid_init_data",
        "message": "Сесія Telegram WebApp недійсна або застаріла — перезапусти застосунок з Telegram",
    }), 403


_ROLE_LABELS = {"owner": "власник", "editor": "редактор", "moderator": "модератор"}


def _role_error_response(min_role: str):
    return jsonify({
        "error": "forbidden", "reason": "insufficient_role",
        "message": f"Потрібна роль «{_ROLE_LABELS.get(min_role, min_role)}» або вища в цьому каналі",
    }), 403


def require_role(req, channel_id, min_role: str = "moderator"):
    """Єдина точка перевірки доступу до каналу — замінює повторюваний патерн
    (check_admin + is_channel_owner) у кожному ендпоінті. Повертає (admin_id, None)
    при успіху, або (None, response) — виклик просто робить `return err`."""
    admin_id = check_admin(req)
    if not admin_id:
        return None, _auth_error_response()
    role = storage.get_channel_role(admin_id, channel_id)
    if not storage.role_at_least(role, min_role):
        return None, _role_error_response(min_role)
    return admin_id, None


@app.before_request
def _maintenance_gate():
    """Технічний перерив: звичайні адміни не проходять далі /api/, суперадмін — завжди проходить."""
    path = request.path
    if not path.startswith("/api/"):
        return None
    if path.startswith("/api/dev") or path == "/api/me":
        return None
    if not storage.is_maintenance_mode():
        return None
    if check_superadmin(request):
        return None
    return jsonify({"error": "maintenance", "message": "Йдуть технічні роботи, панель тимчасово недоступна."}), 503


@app.route("/")
def index():
    return send_from_directory(_WEBAPP_DIR, "index.html")


# ---------- Канали ----------

@app.route("/api/channels", methods=["GET"])
def api_channels():
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    channels = storage.get_channels_with_role_for_admin(admin_id, "moderator")

    async def _fetch_counts():
        local_bot = Bot(token=BOT_TOKEN)
        counts = {}
        for ch in channels:
            if ch.get("status") == "inactive":
                continue
            try:
                counts[ch["id"]] = await local_bot.get_chat_member_count(ch["id"])
            except Exception as e:
                logger.warning(f"Не вдалося отримати кількість підписників {ch['id']}: {e}")
        return counts

    try:
        counts = asyncio.run(_fetch_counts())
    except Exception:
        counts = {}

    for ch in channels:
        ch["submit_link"] = f"https://t.me/{BOT_USERNAME}?start=channel_{ch['id']}" if BOT_USERNAME else None
        style = storage.get_channel_style(ch["id"])
        ch["footer_text"] = style.get("footer_text", "")
        ch["footer_link"] = style.get("footer_link", "")
        ch["subscribers"] = counts.get(ch["id"])
    return jsonify(channels)


@app.route("/api/channel-avatar/<chat_id>", methods=["GET"])
def api_channel_avatar(chat_id):
    """Проксирует аватарку каналу через сервер (щоб не світити токен бота в браузері).
    Автоматично оновлює кеш, якщо канал поставив нове фото (bot_module.get_avatar_bytes_smart) —
    ручний ?refresh=1 більше не потрібен, але залишений як явний примусовий варіант.
    Приймає chat_id як РЯДОК (не <int:...>) — Flask-конвертер int не пропускає мінус,
    а chat_id каналів завжди від'ємний (-100...), тож раніше маршрут просто не спрацьовував."""
    try:
        chat_id = int(chat_id)
    except ValueError:
        return jsonify({"error": "bad_chat_id"}), 400

    if not check_admin(request):
        return _auth_error_response()

    if request.args.get("refresh"):
        storage.clear_channel_avatar_cache(chat_id)

    try:
        image_bytes = asyncio.run(bot_module.get_avatar_bytes_smart(Bot(token=BOT_TOKEN), chat_id, chat_id))
    except Exception as e:
        logger.warning(f"Не вдалося отримати аватарку каналу {chat_id}: {e}")
        image_bytes = None

    if image_bytes is None:
        return jsonify({"error": "no_photo"}), 404
    return Response(image_bytes, mimetype="image/jpeg", headers={"Cache-Control": "no-cache"})


@app.route("/api/source-avatar/<int:source_id>", methods=["GET"])
def api_source_avatar(source_id):
    """Аналог /api/channel-avatar, але для джерел новин (Telegram-канали) — щоб у
    вкладці «Джерела» показувалась справжня аватарка каналу, а не типова іконка."""
    if not check_admin(request):
        return _auth_error_response()

    src = storage.get_source_by_id(source_id)
    if not src or src.get("type") not in ("telegram", "telegram_public"):
        return jsonify({"error": "no_avatar"}), 404

    cache_key = f"src{source_id}"
    if request.args.get("refresh"):
        storage.clear_channel_avatar_cache(cache_key)

    target = src["chat_id"] if src["type"] == "telegram" else f"@{src['username']}"

    try:
        image_bytes = asyncio.run(bot_module.get_avatar_bytes_smart(Bot(token=BOT_TOKEN), target, cache_key))
    except Exception as e:
        logger.warning(f"Не вдалося отримати аватарку джерела {source_id}: {e}")
        image_bytes = None

    if image_bytes is None:
        return jsonify({"error": "no_photo"}), 404
    return Response(image_bytes, mimetype="image/jpeg", headers={"Cache-Control": "no-cache"})


@app.route("/api/channels/toggle", methods=["POST"])
def api_channels_toggle():
    chat_id = request.json.get("id")
    admin_id, err = require_role(request, chat_id, "owner")
    if err:
        return err
    current = storage.is_channel_enabled(chat_id)
    storage.set_channel_enabled(chat_id, not current)
    return jsonify({"ok": True})


@app.route("/api/channels/newstoggle", methods=["POST"])
def api_channels_newstoggle():
    chat_id = request.json.get("id")
    admin_id, err = require_role(request, chat_id, "owner")
    if err:
        return err
    current = storage.is_channel_news_enabled(chat_id)
    storage.set_channel_news_enabled(chat_id, not current)
    return jsonify({"ok": True})


@app.route("/api/channels/style/<channel_id>", methods=["GET"])
def api_channel_style_get(channel_id):
    try:
        channel_id = int(channel_id)
    except ValueError:
        return jsonify({"error": "bad_channel_id"}), 400
    admin_id, err = require_role(request, channel_id, "editor")
    if err:
        return err
    return jsonify(storage.get_channel_style(channel_id))


@app.route("/api/channels/footer", methods=["POST"])
def api_channel_footer_set():
    chat_id = request.json.get("id")
    admin_id, err = require_role(request, chat_id, "editor")
    if err:
        return err
    footer_text = request.json.get("footer_text", "").strip()
    footer_link = request.json.get("footer_link", "").strip()
    storage.set_channel_footer(chat_id, footer_text, footer_link)
    return jsonify({"ok": True})


# ---------- Водяний знак каналу (кастомна картинка, по центру, середня прозорість) ----------

@app.route("/api/channels/watermark/<channel_id>", methods=["GET"])
def api_channel_watermark_status(channel_id):
    """Чи є в цього каналу власний водяний знак — щоб панель показала прев'ю/статус."""
    try:
        channel_id = int(channel_id)
    except ValueError:
        return jsonify({"error": "bad_channel_id"}), 400
    admin_id, err = require_role(request, channel_id, "editor")
    if err:
        return err
    has_watermark = storage.get_channel_watermark_path(channel_id) is not None
    return jsonify({"has_watermark": has_watermark, "auto_watermark": storage.is_channel_auto_watermark_enabled(channel_id)})


@app.route("/api/channels/watermark/image/<channel_id>", methods=["GET"])
def api_channel_watermark_image(channel_id):
    """Віддає саму картинку водяного знаку (для прев'ю в панелі)."""
    try:
        channel_id = int(channel_id)
    except ValueError:
        return jsonify({"error": "bad_channel_id"}), 400
    admin_id, err = require_role(request, channel_id, "editor")
    if err:
        return err
    path = storage.get_channel_watermark_path(channel_id)
    if not path:
        return jsonify({"error": "not_found"}), 404
    with open(path, "rb") as f:
        image_bytes = f.read()
    return Response(image_bytes, mimetype="image/png", headers={"Cache-Control": "no-cache"})


@app.route("/api/channels/watermark/upload", methods=["POST"])
def api_channel_watermark_upload():
    """Завантажує (чи замінює) кастомний водяний знак каналу — картинка з форми.
    Адмін робить це ОДИН РАЗ на канал, далі знак використовується автоматично на
    кожному фото/відео цього каналу: по центру, із середньою прозорістю."""
    channel_id = request.form.get("channel_id", type=int)
    image_file = request.files.get("image")
    if not channel_id or not image_file:
        return jsonify({"ok": False, "error": "Бракує каналу або картинки"}), 400
    admin_id, err = require_role(request, channel_id, "editor")
    if err:
        return err

    try:
        image_bytes = image_file.read()
        # Приводимо до PNG (зберігаючи прозорість, якщо вона є) — незалежно від того,
        # в якому форматі адмін завантажив картинку (jpg/webp/png).
        if bot_module._PIL_AVAILABLE:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            image_bytes = buf.getvalue()
        storage.set_channel_watermark(channel_id, image_bytes)
        return jsonify({"ok": True})
    except Exception as e:
        logger.warning(f"Не вдалося зберегти водяний знак каналу {channel_id}: {e}")
        storage.log_error(f"Водяний знак каналу {channel_id}: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/channels/watermark/remove", methods=["POST"])
def api_channel_watermark_remove():
    """Прибирає кастомний водяний знак каналу (повертається запасний текстовий варіант)."""
    channel_id = (request.json or {}).get("channel_id")
    admin_id, err = require_role(request, channel_id, "editor")
    if err:
        return err
    ok = storage.remove_channel_watermark(channel_id)
    return jsonify({"ok": ok})


@app.route("/api/channels/watermark/auto-toggle", methods=["POST"])
def api_channel_watermark_auto_toggle():
    """Канальний рубильник водяного знаку — незалежний від per-item skip_watermark
    у черзі. Якщо вимкнено — жоден пост цього каналу не штампується, навіть якщо
    конкретний запис у черзі не встиг явно попросити skip_watermark (типовий
    сценарій багу: пост іде в канал миттєво, ще до того, як адмін відкрив редактор)."""
    data = request.json or {}
    channel_id = data.get("channel_id")
    admin_id, err = require_role(request, channel_id, "editor")
    if err:
        return err
    enabled = bool(data.get("enabled"))
    storage.set_channel_auto_watermark(channel_id, enabled)
    return jsonify({"ok": True, "enabled": enabled})


@app.route("/api/channels/watermark/settings", methods=["GET"])
def api_channel_watermark_settings_get():
    """Прозорість, мультипозиції і масштаб водяного знака (п.2.2-2.3/3.2 ТЗ)."""
    channel_id = request.args.get("id", type=int)
    admin_id, err = require_role(request, channel_id, "editor")
    if err:
        return err
    return jsonify(storage.get_channel_watermark_settings(channel_id))


@app.route("/api/channels/watermark/settings", methods=["POST"])
def api_channel_watermark_settings_set():
    data = request.json or {}
    channel_id = data.get("id")
    admin_id, err = require_role(request, channel_id, "editor")
    if err:
        return err
    positions = data.get("positions")
    if positions is not None and not isinstance(positions, list):
        positions = None
    entry = storage.set_channel_watermark_settings(
        channel_id, opacity=data.get("opacity"), positions=positions, scale=data.get("scale"),
    )
    return jsonify({"ok": True, "settings": entry})


@app.route("/api/channels/stats", methods=["GET"])
def api_channel_stats():
    """Статистика для вкладки "Головна" в налаштуваннях каналу (п.1.3/2.1 ТЗ):
    тривоги за добу/місяць, статус, час останньої публікації."""
    channel_id = request.args.get("id", type=int)
    admin_id, err = require_role(request, channel_id, "owner")
    if err:
        return err
    ch = next((c for c in storage.get_channels() if c["id"] == channel_id), None)
    if not ch:
        return jsonify({"ok": False, "error": "Канал не знайдено"}), 404
    alert_stats = storage.get_channel_alert_stats(channel_id)
    return jsonify({
        "ok": True,
        "alerts_today": alert_stats["today"],
        "alerts_month": alert_stats["month"],
        "status": ch.get("status", "active"),
        "enabled": ch.get("enabled", True),
        "last_published": storage.get_channel_last_published(channel_id),
    })


@app.route("/api/channels/automation", methods=["GET"])
def api_channel_automation_get():
    """Вкладка «Головна» модалки каналу, картка «Автоматизація»: автосхвалення
    предложок читачів, автопостинг з черги новин (вкл/викл + КД), і скільки
    новин цього каналу зараз чекають у черзі. Все — персонально для каналу
    (раніше жило одним спільним перемикачем на всі канали адміна у Тех.розділі)."""
    channel_id = request.args.get("id", type=int)
    admin_id, err = require_role(request, channel_id, "owner")
    if err:
        return err
    return jsonify({
        "ok": True,
        "auto_approve": storage.get_channel_auto_approve(channel_id),
        "autopost_enabled": storage.get_channel_autopost_enabled(channel_id),
        "cd_minutes": storage.get_channel_autopost_cd(channel_id),
        "queue_pending": storage.get_channel_pending_queue_count(channel_id),
    })


@app.route("/api/channels/automation", methods=["POST"])
def api_channel_automation_set():
    data = request.json or {}
    channel_id = data.get("id")
    admin_id, err = require_role(request, channel_id, "owner")
    if err:
        return err

    if "auto_approve" in data:
        storage.set_channel_auto_approve(channel_id, bool(data["auto_approve"]))
    if "autopost_enabled" in data:
        storage.set_channel_autopost_enabled(channel_id, bool(data["autopost_enabled"]))
    if "cd_minutes" in data:
        try:
            cd = max(5, min(180, int(data["cd_minutes"])))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "Некоректне значення КД"}), 400
        storage.set_channel_autopost_cd(channel_id, cd)
    return jsonify({"ok": True})


@app.route("/api/channels/growth", methods=["GET"])
def api_channel_growth():
    """Дані для преміальних графіків на вкладці «Головна» (п.2 ТЗ):
    — total: щоденний знімок загальної кількості підписників («Ріст»);
    — joined/left: щоденні підписки/відписки («Підписники», два тумблери).
    days — розмір вікна, яке показує фронтенд (за замовчуванням 5, як у
    прикладі ТЗ), fetch_days — скільки днів історії віддати за раз, щоб
    міні-таймлайн (‹ ›) міг гортати без повторних запитів до сервера."""
    channel_id = request.args.get("id", type=int)
    admin_id, err = require_role(request, channel_id, "owner")
    if err:
        return err
    fetch_days = min(max(request.args.get("days", default=30, type=int), 1), 90)

    try:
        local_bot = Bot(token=BOT_TOKEN)
        current_total = asyncio.run(local_bot.get_chat_member_count(channel_id))
    except Exception:
        current_total = None

    growth = storage.get_growth_snapshots(channel_id, days=fetch_days, current_total=current_total)
    member_daily = storage.get_member_daily(channel_id, days=fetch_days)
    member_by_date = {d["date"]: d for d in member_daily}

    days = []
    for g in growth:
        m = member_by_date.get(g["date"], {"joined": 0, "left": 0})
        days.append({"date": g["date"], "total": g["total"], "joined": m["joined"], "left": m["left"]})

    return jsonify({"ok": True, "days": days, "default_window": 5})


@app.route("/api/channels/category", methods=["POST"])
def api_channels_category():
    chat_id = request.json.get("id")
    admin_id, err = require_role(request, chat_id, "editor")
    if err:
        return err
    category = request.json.get("category", "")
    storage.set_channel_category(chat_id, category)
    if category.strip():
        storage.add_channel_folder(admin_id, category)  # щоб одразу з'явилась як опція в селекті/табах
    return jsonify({"ok": True})


# ---------- Команда каналу (Owner / Editor / Moderator) ----------

# Права, які видаються в САМОМУ Telegram-каналі (через promote_chat_member) —
# на додачу до ролі всередині нашої панелі, щоб Editor/Moderator міг працювати
# і напряму в Telegram, а не лише через веб-панель. Дзеркалить повний набір прав
# самого бота (див. скрін "Возможности администратора" в самому Telegram) —
# КРІМ can_promote_members: Telegram і так не дозволить видати права, яких
# немає в самого бота-промоутера, а власник каналу свідомо тримає це право
# вимкненим навіть у бота — Editor/Moderator не повинен мати змогу додавати
# ще адмінів через нашу панель.
_ROLE_TG_PERMISSIONS_FULL = dict(
    can_change_info=True,
    can_post_messages=True, can_edit_messages=True, can_delete_messages=True,
    can_post_stories=True, can_edit_stories=True, can_delete_stories=True,
    can_invite_users=True,
    can_manage_video_chats=True,
    can_manage_chat=True,
    can_restrict_members=True,
    can_pin_messages=True,
)
_ROLE_TG_PERMISSIONS = {
    "editor": dict(_ROLE_TG_PERMISSIONS_FULL),
    "moderator": dict(_ROLE_TG_PERMISSIONS_FULL),
}
_ROLE_TG_REVOKE = {k: False for k in _ROLE_TG_PERMISSIONS_FULL}


def _apply_telegram_role(channel_id: int, user_id: int, role: str) -> str | None:
    """Видає user_id права адміністратора САМЕ в Telegram-каналі. Повертає текст
    помилки (якщо Telegram відмовив — наприклад, бот сам не адмін з правом
    "Додавати нових адміністраторів", або людина ще не підписана на канал) або
    None, якщо все пройшло успішно. Помилка тут НЕ скасовує зміну ролі в панелі —
    роль у нашій БД і права в самому Telegram навмисно незалежні одне від одного."""
    try:
        asyncio.run(Bot(token=BOT_TOKEN).promote_chat_member(
            chat_id=channel_id, user_id=user_id, **_ROLE_TG_PERMISSIONS.get(role, {}),
        ))
        return None
    except Exception as e:
        logger.warning(f"Не вдалося видати Telegram-права ({role}) user_id={user_id} у каналі {channel_id}: {e}")
        return str(e)


def _revoke_telegram_role(channel_id: int, user_id: int) -> None:
    try:
        asyncio.run(Bot(token=BOT_TOKEN).promote_chat_member(chat_id=channel_id, user_id=user_id, **_ROLE_TG_REVOKE))
    except Exception as e:
        logger.warning(f"Не вдалося зняти Telegram-права user_id={user_id} у каналі {channel_id}: {e}")


# Порядок і підписи — точно як у нативному екрані Telegram "Возможности администратора",
# щоб власнику не довелось перевчатись. can_promote_members НАВМИСНО відсутній у списку
# редагованих прав (див. коментар вище _ROLE_TG_PERMISSIONS_FULL) — його показуємо окремо,
# завжди заблокованим.
_TG_PERMISSION_LABELS = [
    ("can_change_info", "Зміна профілю каналу"),
    ("can_post_messages", "Публікація дописів"),
    ("can_edit_messages", "Редагування дописів"),
    ("can_delete_messages", "Видалення дописів"),
    ("can_post_stories", "Публікація історій"),
    ("can_edit_stories", "Редагування історій"),
    ("can_delete_stories", "Видалення історій"),
    ("can_invite_users", "Додавання учасників"),
    ("can_manage_video_chats", "Керування трансляціями"),
    ("can_manage_chat", "Доступ до повідомлень каналу"),
    ("can_restrict_members", "Блокування користувачів"),
    ("can_pin_messages", "Закріплення повідомлень"),
]


@app.route("/api/channels/team/permissions", methods=["GET"])
def api_channel_team_permissions_get():
    """Поточні права user_id у САМОМУ Telegram-каналі — якщо людина ще не має там
    admin-статусу (Telegram ще не підтвердив promote_chat_member), показуємо
    дефолтний набір з ролі в нашій панелі, щоб тумблери не стартували порожніми."""
    channel_id = request.args.get("channel_id", type=int)
    user_id = request.args.get("user_id", type=int)
    admin_id, err = require_role(request, channel_id, "owner")
    if err:
        return err
    role = storage.get_channel_role(user_id, channel_id)
    permissions = dict(_ROLE_TG_PERMISSIONS.get(role, _ROLE_TG_PERMISSIONS_FULL))
    live = True
    try:
        member = asyncio.run(Bot(token=BOT_TOKEN).get_chat_member(chat_id=channel_id, user_id=user_id))
        if member.status == "administrator":
            for key, _ in _TG_PERMISSION_LABELS:
                permissions[key] = bool(getattr(member, key, False))
        else:
            live = False
    except Exception as e:
        logger.warning(f"Не вдалося отримати поточні права user_id={user_id} у каналі {channel_id}: {e}")
        live = False
    return jsonify({
        "ok": True, "live": live,
        "labels": [{"key": k, "label": l, "value": permissions.get(k, False)} for k, l in _TG_PERMISSION_LABELS],
    })


@app.route("/api/channels/team/permissions", methods=["POST"])
def api_channel_team_permissions_set():
    data = request.json or {}
    channel_id = data.get("channel_id")
    user_id = data.get("user_id")
    admin_id, err = require_role(request, channel_id, "owner")
    if err:
        return err
    permitted_keys = {k for k, _ in _TG_PERMISSION_LABELS}
    incoming = data.get("permissions") or {}
    permissions = {k: bool(v) for k, v in incoming.items() if k in permitted_keys}
    permissions["can_promote_members"] = False  # ніколи не через нашу панель — див. коментар вище
    try:
        asyncio.run(Bot(token=BOT_TOKEN).promote_chat_member(chat_id=channel_id, user_id=user_id, **permissions))
        return jsonify({"ok": True})
    except Exception as e:
        logger.warning(f"Не вдалося зберегти права user_id={user_id} у каналі {channel_id}: {e}")
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/channels/team", methods=["GET"])
def api_channel_team_list():
    channel_id = request.args.get("id", type=int)
    admin_id, err = require_role(request, channel_id, "owner")
    if err:
        return err
    members = storage.get_channel_members(channel_id)
    user_ids = [m["user_id"] for m in members]
    profiles = storage.get_user_profiles(user_ids)
    # Учасник міг ще ЖОДНОГО разу не відкривати нашу панель (кеш профілю наповнюється
    # лише через presence-пінг), але бот УЖЕ бачить його — щойно власник додав людину
    # в команду каналу (get_chat працює для будь-якого user_id зі спільним чатом).
    # Тож для тих, кого немає в кеші, підтягуємо ім'я напряму з Telegram і кешуємо.
    for uid in user_ids:
        if uid in profiles:
            continue
        try:
            chat = asyncio.run(Bot(token=BOT_TOKEN).get_chat(uid))
            first_name, username = chat.first_name, chat.username
        except Exception as e:
            logger.warning(f"Не вдалося отримати профіль учасника {uid}: {e}")
            first_name = username = None
        if first_name:
            storage.cache_user_profile(uid, first_name, username, None)
            profiles[uid] = {"first_name": first_name, "username": username, "photo_url": None}
    for m in members:
        m["profile"] = profiles.get(m["user_id"])
    return jsonify({"ok": True, "members": members})


@app.route("/api/channels/team/stats", methods=["GET"])
def api_channel_team_stats():
    """Дашборд ефективності команди каналу (вкладка «Команда», лише Owner):
    скільки схвалень/відхилень зробив кожен і середній час реакції. "Охват"
    (перегляди/реакції) сюди свідомо не входить — Telegram Bot API не віддає
    статистику перегляду окремих постів каналу, тільки MTProto (Telethon) міг
    би це дати, а це вже окрема, набагато важча інтеграція."""
    channel_id = request.args.get("id", type=int)
    admin_id, err = require_role(request, channel_id, "owner")
    if err:
        return err
    return jsonify({"ok": True, "stats": storage.get_editor_stats(channel_id)})


@app.route("/api/user-avatar/<int:user_id>", methods=["GET"])
def api_user_avatar(user_id):
    """Аватарка користувача (учасника команди каналу) — проксується так само, як
    /api/channel-avatar, щоб не світити токен бота в браузері. Працює для будь-
    якого user_id, з яким бот має спільний чат — а щойно доданий у команду
    учасник каналу якраз такий (bot.get_chat бачить його через сам канал)."""
    if not check_admin(request):
        return _auth_error_response()
    try:
        image_bytes = asyncio.run(bot_module.get_avatar_bytes_smart(Bot(token=BOT_TOKEN), user_id, user_id))
    except Exception as e:
        logger.warning(f"Не вдалося отримати аватарку користувача {user_id}: {e}")
        image_bytes = None
    if image_bytes is None:
        return jsonify({"error": "no_photo"}), 404
    return Response(image_bytes, mimetype="image/jpeg", headers={"Cache-Control": "no-cache"})


@app.route("/api/user-lookup/<int:user_id>", methods=["GET"])
def api_user_lookup(user_id):
    """Прев'ю особи ПЕРЕД додаванням у команду каналу (кнопка «Додати учасника»
    у вкладці «Команда») — щоб адмін бачив ім'я/@username, а не додавав наосліп
    за голим числом. Працює лише якщо бот вже "бачив" цього user_id (спільний
    чат чи людина хоч раз писала боту) — той самий природний ліміт Telegram
    Bot API, що й у /api/user-avatar. Якщо ні — ok:false, не помилка додавання."""
    if not check_admin(request):
        return _auth_error_response()
    try:
        chat = asyncio.run(Bot(token=BOT_TOKEN).get_chat(user_id))
    except Exception:
        chat = None
    if not chat or chat.type != "private":
        return jsonify({"ok": False, "error": "unknown"}), 404
    return jsonify({
        "ok": True,
        "first_name": chat.first_name or "",
        "last_name": chat.last_name or "",
        "username": chat.username or "",
    })


@app.route("/api/user-lookup-by-username/<username>", methods=["GET"])
def api_user_lookup_by_username(username):
    """Додавання учасника команди за @username (на додачу до user_id). Спершу
    шукає в локальному кеші профілів — усі, хто хоч раз відкривав панель
    (storage.cache_user_profile) — швидко й надійно. Якщо там немає, пробує
    напряму через Telegram (bot.get_chat), що працює лише за тим самим
    природним обмеженням Bot API, що й у /api/user-lookup за id: бот має вже
    "бачити" цього користувача. Якщо ні — чесна відповідь ok:false, а не
    вигадана помилка, щоб фронт міг підказати "хай спершу напише боту"."""
    if not check_admin(request):
        return _auth_error_response()
    uname = username.lstrip("@").strip()
    if not uname:
        return jsonify({"ok": False, "error": "empty"}), 400

    uid = storage.find_user_by_username(uname)
    if uid:
        profile = storage.get_user_profiles([uid]).get(uid, {})
        return jsonify({
            "ok": True, "user_id": uid,
            "first_name": profile.get("first_name") or "",
            "username": profile.get("username") or uname,
        })

    try:
        chat = asyncio.run(Bot(token=BOT_TOKEN).get_chat(f"@{uname}"))
    except Exception:
        chat = None
    if not chat or chat.type != "private":
        return jsonify({"ok": False, "error": "not_found"}), 404
    return jsonify({
        "ok": True, "user_id": chat.id,
        "first_name": chat.first_name or "", "last_name": chat.last_name or "",
        "username": chat.username or uname,
    })


@app.route("/api/channels/team/add", methods=["POST"])
def api_channel_team_add():
    data = request.json or {}
    channel_id = data.get("channel_id")
    admin_id, err = require_role(request, channel_id, "owner")
    if err:
        return err
    user_id = data.get("user_id")
    role = data.get("role")
    if not isinstance(user_id, int) or role not in ("editor", "moderator"):
        return jsonify({"ok": False, "error": "Некоректний user_id або роль"}), 400
    if user_id == admin_id:
        return jsonify({"ok": False, "error": "Не можна додати самого себе"}), 400
    member = storage.add_channel_member(channel_id, user_id, role, added_by=admin_id)
    tg_error = _apply_telegram_role(channel_id, user_id, role) if member else None
    return jsonify({"ok": bool(member), "member": member, "tg_warning": tg_error})


@app.route("/api/channels/team/update-role", methods=["POST"])
def api_channel_team_update_role():
    data = request.json or {}
    channel_id = data.get("channel_id")
    admin_id, err = require_role(request, channel_id, "owner")
    if err:
        return err
    role = data.get("role")
    if role not in ("editor", "moderator"):
        return jsonify({"ok": False, "error": "Некоректна роль"}), 400
    user_id = data.get("user_id")
    ok = storage.update_channel_member_role(channel_id, user_id, role)
    tg_error = _apply_telegram_role(channel_id, user_id, role) if ok else None
    return jsonify({"ok": ok, "tg_warning": tg_error})


@app.route("/api/channels/team/remove", methods=["POST"])
def api_channel_team_remove():
    data = request.json or {}
    channel_id = data.get("channel_id")
    admin_id, err = require_role(request, channel_id, "owner")
    if err:
        return err
    user_id = data.get("user_id")
    ok = storage.remove_channel_member(channel_id, user_id)
    if ok:
        _revoke_telegram_role(channel_id, user_id)
    return jsonify({"ok": ok})


# ---------- Моніторинг повітряних тривог (NEPTUN, neptun.in.ua) — п.1-3 ТЗ ----------

@app.route("/api/alerts/oblasts", methods=["GET"])
def api_alerts_oblasts():
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    return jsonify({"oblasts": bot_module.UKRAINE_OBLASTS, "types": storage.ALERT_THREAT_TYPES})


@app.route("/api/channels/alert-settings", methods=["GET"])
def api_channel_alert_settings_get():
    chat_id = request.args.get("id", type=int)
    admin_id, err = require_role(request, chat_id, "owner")
    if err:
        return err
    return jsonify(storage.get_channel_alert_settings(chat_id))


@app.route("/api/channels/alert-settings", methods=["POST"])
def api_channel_alert_settings_set():
    data = request.json or {}
    chat_id = data.get("id")
    admin_id, err = require_role(request, chat_id, "owner")
    if err:
        return err

    oblasts = data.get("oblasts")
    if oblasts is not None:
        oblasts = [o for o in oblasts if o in bot_module.UKRAINE_OBLASTS]
    types = data.get("types")
    if types is not None:
        types = [t for t in types if t in storage.ALERT_THREAT_TYPES]

    entry = storage.set_channel_alert_settings(
        chat_id,
        enabled=data.get("enabled"),
        oblasts=oblasts,
        types=types,
        notify_siren=data.get("notify_siren"),
        notify_threats=data.get("notify_threats"),
        show_threat_map=data.get("show_threat_map"),
    )
    return jsonify({"ok": True, "settings": entry})


@app.route("/api/alerts/test", methods=["POST"])
def api_alerts_test():
    chat_id = (request.json or {}).get("id")
    admin_id, err = require_role(request, chat_id, "owner")
    if err:
        return err
    try:
        asyncio.run(bot_module.send_test_alert(Bot(token=BOT_TOKEN), chat_id))
        return jsonify({"ok": True})
    except Exception as e:
        logger.warning(f"Не вдалося надіслати тестову тривогу в {chat_id}: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/channels/folders", methods=["GET"])
def api_channels_folders():
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    known = set(storage.get_channel_folders(admin_id))
    known.update(
        (c.get("category") or "").strip()
        for c in storage.get_channels_for_admin(admin_id) if (c.get("category") or "").strip()
    )
    return jsonify(sorted(known, key=str.lower))


@app.route("/api/channels/folders/add", methods=["POST"])
def api_channels_folders_add():
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    name = (request.json or {}).get("name", "")
    ok = storage.add_channel_folder(admin_id, name)
    return jsonify({"ok": ok})


@app.route("/api/channels/folders/remove", methods=["POST"])
def api_channels_folders_remove():
    """Видаляє категорію з таб-бару папок (п. "додай можливість видалити категорію").
    Канали з цієї категорії переносяться в "Без категорії", самі канали не чіпаються."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    name = (request.json or {}).get("name", "")
    ok = storage.remove_channel_folder(admin_id, name)
    return jsonify({"ok": ok})


@app.route("/api/channels/post-submit-button", methods=["POST"])
def api_channels_post_submit_button():
    """Бот сам публікує в канал повідомлення з кнопкою «Надіслати новину» (deep-link предложки)."""
    chat_id = request.json.get("id")
    admin_id, err = require_role(request, chat_id, "editor")
    if err:
        return err

    if not BOT_USERNAME:
        return jsonify({"ok": False, "error": "Username бота ще не завантажено, спробуй за хвилину"}), 400

    submit_link = f"https://t.me/{BOT_USERNAME}?start=channel_{chat_id}"

    async def _post():
        from telegram import InlineKeyboardButton as IKB, InlineKeyboardMarkup as IKM
        local_bot = Bot(token=BOT_TOKEN)
        keyboard = IKM([[IKB("📤 Надіслати новину", url=submit_link)]])
        await local_bot.send_message(
            chat_id=chat_id,
            text="📬 Побачив цікаву новину? Поділись нею з нами — тисни кнопку нижче!",
            reply_markup=keyboard,
        )

    try:
        asyncio.run(_post())
    except Exception as e:
        logger.warning(f"Не вдалося опублікувати кнопку в канал {chat_id}: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

    return jsonify({"ok": True})


@app.route("/api/channels/keywords", methods=["POST"])
def api_channels_keywords():
    chat_id = request.json.get("id")
    admin_id, err = require_role(request, chat_id, "editor")
    if err:
        return err
    raw = request.json.get("keywords", "")
    keywords = [w.strip().lower() for w in raw.split(",") if w.strip()]
    storage.set_channel_keywords(chat_id, keywords)
    return jsonify({"ok": True})


@app.route("/api/channels/remove", methods=["POST"])
def api_channels_remove():
    chat_id = request.json.get("id")
    admin_id, err = require_role(request, chat_id, "owner")
    if err:
        return err
    ok = storage.remove_channel(chat_id)

    async def _leave():
        try:
            await Bot(token=BOT_TOKEN).leave_chat(chat_id)
        except Exception as e:
            logger.warning(f"Не вдалося вийти з каналу {chat_id}: {e}")

    asyncio.run(_leave())
    return jsonify({"ok": ok})


@app.route("/api/channels/test", methods=["POST"])
def api_channels_test():
    chat_id = request.json.get("id")
    admin_id, err = require_role(request, chat_id, "editor")
    if err:
        return err

    async def _send():
        await Bot(token=BOT_TOKEN).send_message(chat_id=chat_id, text="🔔 Тестове повідомлення від бота.")

    try:
        asyncio.run(_send())
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# ---------- Джерела новин ----------

def _resolve_own_source(admin_id: int, data: dict):
    """Знаходить власне джерело адміна за id (новий формат) або, якщо id немає/не знайдено, —
    за name (сумісність зі старим фронтендом, поки він не перейшов на id повністю)."""
    own_sources = storage.get_sources_for_admin(admin_id)
    source_id = data.get("id")
    if source_id is not None:
        found = next((s for s in own_sources if s["id"] == source_id), None)
        if found:
            return found
    name = data.get("name")
    if name:
        return next((s for s in own_sources if s["name"] == name), None)
    return None


@app.route("/api/presence/ping", methods=["POST"])
def api_presence_ping():
    """Серцебиття з фронтенду — фіксує, що адмін зараз у панелі (застосунок
    відкритий). Викликається періодично, поки сторінка відкрита (див. app.js).
    Заразом (тут, а не на КОЖНОМУ запиті) оновлює кеш профілю (ім'я/аватарка) —
    щоб "Команда каналу" могла показати не голий user_id, а ім'я й фото."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    storage.touch_admin_presence(admin_id)
    user = _parse_init_data_user(request)
    if user:
        storage.cache_user_profile(admin_id, user.get("first_name"), user.get("username"), user.get("photo_url"))
    return jsonify({"ok": True})


# ==================== Кастомні емодзі в редакторі ====================

def _parse_emoji_set_name(raw: str) -> str:
    """Приймає і повне посилання (t.me/addemoji/<name> чи /addstickers/<name>),
    і просто голу назву паку — повертає лише short name."""
    name = (raw or "").strip()
    for prefix in ("https://t.me/addemoji/", "http://t.me/addemoji/", "t.me/addemoji/",
                   "https://t.me/addstickers/", "http://t.me/addstickers/", "t.me/addstickers/"):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    return name.split("?")[0].split("/")[0].strip()


@app.route("/api/custom-emoji/set", methods=["GET"])
def api_custom_emoji_set_get():
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    return jsonify({"ok": True, "set_name": storage.get_custom_emoji_set_name(admin_id)})


@app.route("/api/custom-emoji/set", methods=["POST"])
def api_custom_emoji_set_set():
    """Прив'язує до адміна конкретний пак кастомних емодзі — перевіряє одразу
    (fetch через бота), щоб не зберегти биту назву."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    name = _parse_emoji_set_name((request.json or {}).get("set_name", ""))
    if not name:
        return jsonify({"ok": False, "error": "Вкажи посилання або назву паку"}), 400

    try:
        emoji_list = asyncio.run(bot_module.fetch_custom_emoji_set(Bot(token=BOT_TOKEN), name))
    except Exception as e:
        logger.warning(f"Не вдалося перевірити емодзі-пак {name}: {e}")
        emoji_list = None
    if emoji_list is None:
        return jsonify({"ok": False, "error": "Пак не знайдено — перевір посилання чи назву"}), 404
    if not emoji_list:
        return jsonify({"ok": False, "error": "У цьому паку немає кастомних емодзі"}), 400

    storage.set_custom_emoji_set_name(admin_id, name)
    return jsonify({"ok": True, "set_name": name, "count": len(emoji_list)})


@app.route("/api/custom-emoji/list", methods=["GET"])
def api_custom_emoji_list():
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    set_name = storage.get_custom_emoji_set_name(admin_id)
    if not set_name:
        return jsonify({"ok": True, "set_name": None, "items": []})
    try:
        emoji_list = asyncio.run(bot_module.fetch_custom_emoji_set(Bot(token=BOT_TOKEN), set_name))
    except Exception as e:
        logger.warning(f"Не вдалося оновити список кастомних емодзі {set_name}: {e}")
        emoji_list = None
    if emoji_list is None:
        return jsonify({"ok": False, "error": "Не вдалося завантажити пак — перевір посилання ще раз"}), 502
    return jsonify({"ok": True, "set_name": set_name, "items": emoji_list})


@app.route("/api/custom-emoji/thumb/<file_id>", methods=["GET"])
def api_custom_emoji_thumb(file_id):
    """Проксує прев'ю кастомного емодзі через сервер (той самий підхід, що й
    /api/channel-avatar — щоб не світити токен бота в браузері)."""
    if not check_admin(request):
        return _auth_error_response()
    try:
        image_bytes = asyncio.run(bot_module.fetch_telegram_file_bytes(Bot(token=BOT_TOKEN), file_id))
    except Exception:
        image_bytes = None
    if image_bytes is None:
        return jsonify({"error": "not_found"}), 404
    return Response(image_bytes, mimetype="image/webp", headers={"Cache-Control": "public, max-age=86400"})


@app.route("/api/sources/recommended", methods=["GET"])
def api_sources_recommended():
    """Список рекомендованих публічних джерел про війну й політику — з поміткою,
    які з них цей адмін уже додав (щоб не пропонувати додати вдруге)."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    own_usernames = {
        s.get("username", "").lower()
        for s in storage.get_sources_for_admin(admin_id)
        if s.get("type") == "telegram_public"
    }
    result = [
        {**rec, "already_added": rec["username"].lower() in own_usernames}
        for rec in RECOMMENDED_WAR_POLITICS_SOURCES
    ]
    return jsonify(result)


@app.route("/api/sources", methods=["GET"])
def api_sources():
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    return jsonify(storage.get_sources_for_admin(admin_id))


@app.route("/api/sources/toggle", methods=["POST"])
def api_sources_toggle():
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    current = _resolve_own_source(admin_id, request.json or {})
    if not current:
        return jsonify({"ok": False, "error": "Джерело не знайдено або належить не тобі"}), 404
    storage.set_source_enabled(admin_id, current["id"], not current.get("enabled", True))
    return jsonify({"ok": True})


@app.route("/api/sources/category", methods=["POST"])
def api_sources_category():
    """Перемикає тип джерела: public_channel (зовнішнє, повна дедуплікація) /
    editorial_chat (власний редакційний чат — без суворої перевірки на дублі,
    п.3 ТЗ)."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    data = request.json or {}
    source_id = data.get("id")
    category = data.get("category")
    if not storage.is_source_owner(admin_id, source_id):
        return jsonify({"ok": False, "error": "Джерело не знайдено або належить не тобі"}), 404
    ok = storage.set_source_category(admin_id, source_id, category)
    if not ok:
        return jsonify({"ok": False, "error": "Невідома категорія"}), 400
    return jsonify({"ok": True})


@app.route("/api/sources/add-public-tg", methods=["POST"])
def api_sources_add_public_tg():
    """Додає публічний Telegram-канал як джерело за ПОСИЛАННЯМ (без вступу бота),
    прив'язане до адміна, який його додав.
    План оптимізації (п.1, "Умні інпути для джерел"): назва каналу — необов'язкова.
    Якщо її не передали, підтягуємо справжню назву через Telegram API (bot.get_chat),
    щоб не змушувати адміна вручну вписувати те, що бот і сам може дізнатись."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    name = (request.json.get("name") or "").strip()
    raw = (request.json.get("link") or "").strip()
    if not raw:
        return jsonify({"ok": False, "error": "Вкажи посилання або username каналу"}), 400

    # Витягуємо username з різних форматів: t.me/name, https://t.me/name, @name, просто name
    username = raw
    for prefix in ("https://t.me/", "http://t.me/", "t.me/", "@"):
        if username.startswith(prefix):
            username = username[len(prefix):]
            break
    username = username.split("/")[0].split("?")[0].strip()

    if not username:
        return jsonify({"ok": False, "error": "Не вдалося розпізнати username каналу"}), 400

    if not name:
        try:
            chat = asyncio.run(Bot(token=BOT_TOKEN).get_chat(f"@{username}"))
            name = chat.title or username
        except Exception as e:
            logger.warning(f"Не вдалося автоматично визначити назву каналу @{username}: {e}")
            return jsonify({"ok": False, "error": "Канал не знайдено або він приватний — перевір username"}), 404

    try:
        ok = storage.add_public_telegram_source(admin_id, name, username)
        return jsonify({"ok": ok, "username": username, "name": name})
    except Exception as e:
        logger.warning(f"Помилка додавання публічного TG-джерела {name}: {e}")
        storage.log_error(f"Додавання публічного TG-джерела {name}: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/sources/test", methods=["POST"])
def api_sources_test():
    """Бере найсвіжішу новину з конкретного (СВОГО) джерела і надсилає в ОБРАНІ канали
    (один чи кілька одразу) — кожному своя підпис (назва+посилання+персональне
    "Надіслати новину"), у ТОЧНО такому ж форматі, як реальна авторозсилка."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()

    data = request.json or {}
    channel_ids = data.get("channel_ids")
    if not channel_ids and data.get("channel_id"):
        channel_ids = [data.get("channel_id")]  # сумісність зі старим форматом (одне значення)
    if not channel_ids:
        return jsonify({"ok": False, "error": "Оберіть хоча б один канал для тесту"}), 400

    for cid in channel_ids:
        if not storage.is_channel_owner(admin_id, cid):
            return jsonify({"ok": False, "error": f"403 Forbidden: канал {cid} не твій"}), 403

    source = _resolve_own_source(admin_id, data)
    if not source:
        return jsonify({"ok": False, "error": "Джерело не знайдено або належить не тобі"}), 404
    source_name = source["name"]
    source_type = source.get("type")
    if source_type == "telegram":
        # "editorial_chat"-джерело: бот є учасником чату, але Bot API НЕ дає способу
        # запросити історію повідомлень на вимогу — новини звідти приходять лише
        # push-подіями (channel_post), тому "взяти останній пост і протестувати" тут
        # структурно неможливо, а не просто "не реалізовано".
        return jsonify({
            "ok": False,
            "error": "Тест недоступний для типу 'telegram' (редакційний чат): Telegram Bot API "
                     "не дозволяє запитати історію повідомлень — новини звідти надходять лише "
                     "у реальному часі, коли їх публікують. Спробуй опублікувати тестове "
                     "повідомлення в чат і перевір автопостинг у черзі.",
        }), 400
    if source_type not in ("rss", "telegram_public"):
        return jsonify({"ok": False, "error": f"Невідомий тип джерела: '{source_type}'"}), 400

    # Готуємо контент ОДИН РАЗ — так само, як реальна авторозсилка: фетч спільний,
    # підпис під кожен канал свій (додається нижче, окремо для кожного).
    if source.get("type") == "rss":
        try:
            feed = feedparser.parse(source["url"])
            if not feed.entries:
                return jsonify({"ok": False, "error": "У цього RSS зараз немає жодної новини"}), 400
            entry = feed.entries[0]
            base_text, image_url = asyncio.run(bot_module._format_news_post(entry))
            media_source_items = [{"type": "photo", "url": image_url}] if image_url else []
        except Exception as e:
            return jsonify({"ok": False, "error": f"Не вдалося розібрати RSS: {e}"}), 500
    else:  # telegram_public
        try:
            posts = asyncio.run(bot_module._fetch_public_channel_posts(source["username"], limit=1))
            if not posts:
                return jsonify({"ok": False, "error": "У цього каналу зараз немає постів з текстом чи медіа"}), 400
            post = posts[0]
            title = asyncio.run(bot_module._translate_plain_to_uk(post["title"]))
            body_html = asyncio.run(bot_module._translate_html_to_uk(post["body_html"])) if post["body_html"] else ""
            base_text = f"⚡ <b>{bot_module.html_lib.escape(title)}</b>" if title else "⚡"
            if body_html:
                base_text += f"\n\n{body_html}"
            media_source_items = post["media"]  # може бути кілька, якщо пост — альбом (фото і/або відео)
        except Exception as e:
            return jsonify({"ok": False, "error": f"Не вдалося прочитати канал: {e}"}), 500

    channels = storage.get_channels_for_admin(admin_id)

    async def _publish_all():
        local_bot = Bot(token=BOT_TOKEN)
        # Завантажуємо медіа ОДИН РАЗ (спільний фетч), а підпис/водяний знак — окремо
        # для кожного каналу нижче (у кожного своя назва, посилання й submit-лінк).
        media_items = await bot_module._download_media_items(media_source_items)
        results = {}
        for cid in channel_ids:
            channel = next((c for c in channels if c["id"] == cid), None)
            channel_title = channel["title"] if channel else str(cid)
            try:
                chat = await local_bot.get_chat(cid)
                link = await bot_module._get_channel_link(local_bot, cid, chat.username)
            except Exception:
                link = None
            submit_link = f"https://t.me/{BOT_USERNAME}?start=channel_{cid}" if BOT_USERNAME else None
            footer = bot_module._build_channel_footer(channel_title, link, submit_link)
            text = f"{base_text}\n\n{footer}"
            try:
                await bot_module._send_news_post(local_bot, cid, text, media_items, watermark_text=channel_title)
                results[str(cid)] = True
            except Exception as e:
                logger.warning(f"Не вдалося надіслати тест джерела {source_name} у канал {cid}: {e}")
                storage.log_error(f"Тест джерела {source_name} у канал {cid}: {e}")
                results[str(cid)] = False
        return results

    try:
        results = asyncio.run(_publish_all())
    except Exception as e:
        logger.warning(f"Не вдалося надіслати тест джерела {source_name}: {e}")
        storage.log_error(f"Тест джерела {source_name}: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

    ok_count = sum(1 for v in results.values() if v)
    return jsonify({"ok": ok_count > 0, "sent": ok_count, "total": len(channel_ids), "results": results})


@app.route("/api/sources/remove", methods=["POST"])
def api_sources_remove():
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    source = _resolve_own_source(admin_id, request.json or {})
    if not source:
        return jsonify({"ok": False, "error": "Джерело не знайдено або належить не тобі"}), 404
    ok = storage.remove_source(admin_id, source["id"])
    return jsonify({"ok": ok})


@app.route("/api/sources/edit", methods=["POST"])
def api_sources_edit():
    """Редагування картки джерела (назва і/або посилання) — тільки власного."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    data = request.json or {}
    source_id = data.get("id")
    name = data.get("name")
    link = data.get("link")
    if not storage.is_source_owner(admin_id, source_id):
        return jsonify({"ok": False, "error": "Джерело не знайдено або належить не тобі"}), 403
    ok = storage.edit_source(admin_id, source_id, name=name, link=link)
    return jsonify({"ok": ok})


def _discover_rss_url(url: str) -> str:
    """Якщо посилання вже валідний RSS — повертає як є. Інакше пробує знайти RSS-фід
    на звичайній сторінці сайту (шукає <link rel="alternate" type="application/rss+xml">)."""
    try:
        feed = feedparser.parse(url)
        if feed.entries:
            return url
    except Exception:
        pass

    try:
        resp = httpx.get(url, timeout=10, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        html = resp.text
        import re
        matches = re.findall(
            r'<link[^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]*>', html, re.IGNORECASE
        )
        for tag in matches:
            href_match = re.search(r'href=["\']([^"\']+)["\']', tag, re.IGNORECASE)
            if href_match:
                found = href_match.group(1)
                if found.startswith("//"):
                    found = "https:" + found
                elif found.startswith("/"):
                    from urllib.parse import urljoin
                    found = urljoin(url, found)
                return found
    except Exception:
        pass

    return url  # нічого не знайшли — повертаємо оригінал, хай спробує як є


@app.route("/api/sources/add", methods=["POST"])
def api_sources_add():
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    name = request.json.get("name", "").strip()
    url = request.json.get("url", "").strip()
    if not name or not url:
        return jsonify({"ok": False, "error": "Вкажи назву і посилання"}), 400

    try:
        resolved_url = _discover_rss_url(url)
        ok = storage.add_source(admin_id, name, resolved_url)
        return jsonify({"ok": ok, "resolved_url": resolved_url if resolved_url != url else None})
    except Exception as e:
        logger.warning(f"Помилка додавання джерела {name}: {e}")
        storage.log_error(f"Додавання джерела {name}: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/me", methods=["GET"])
def api_me():
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    return jsonify({
        "user_id": admin_id,
        "channels_count": len(storage.get_channels_for_admin(admin_id)),
        "sources_count": len(storage.get_sources()),
        "bot_username": BOT_USERNAME,
        "bot_name": BOT_NAME,
        "is_superadmin": admin_id in SUPERADMIN_IDS,
        "language": storage.get_admin_language(admin_id),
    })


@app.route("/api/settings/language", methods=["POST"])
def api_settings_language():
    """Перемикач мови (UA/RU/EN) — впливає і на інтерфейс WebApp, і на мову, якою
    перекладаються новини для каналів цього адміна (п.3 патчу ТЗ)."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    lang = (request.json or {}).get("language")
    if lang not in ("ua", "ru", "en"):
        return jsonify({"ok": False, "error": "Мова має бути 'ua', 'ru' або 'en'"}), 400
    storage.set_admin_language(admin_id, lang)
    return jsonify({"ok": True, "language": lang})


@app.route("/api/push/vapid-public-key", methods=["GET"])
def api_push_vapid_public_key():
    """Публічний VAPID-ключ для PushManager.subscribe() на фронті. ok:false,
    якщо на бекенді не задано VAPID_PRIVATE_KEY/VAPID_PUBLIC_KEY — фронт тоді
    ховає перемикач push-сповіщень у профілі замість кнопки, що завжди валиться."""
    if not push_module.PUSH_AVAILABLE:
        return jsonify({"ok": False, "error": "Push не налаштовано на сервері"}), 503
    return jsonify({"ok": True, "key": push_module.VAPID_PUBLIC_KEY})


@app.route("/api/push/subscribe", methods=["POST"])
def api_push_subscribe():
    """Фронт шле сюди об'єкт підписки одразу після успішного PushManager.subscribe()."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    data = request.json or {}
    subscription = data.get("subscription")
    if not subscription or not subscription.get("endpoint"):
        return jsonify({"ok": False, "error": "Некоректна підписка"}), 400
    storage.add_push_subscription(admin_id, subscription)
    return jsonify({"ok": True})


@app.route("/api/push/unsubscribe", methods=["POST"])
def api_push_unsubscribe():
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    endpoint = (request.json or {}).get("endpoint")
    if endpoint:
        storage.remove_push_subscription(admin_id, endpoint)
    return jsonify({"ok": True})


@app.route("/api/push/test", methods=["POST"])
def api_push_test():
    """Тестовий push із самого профілю — переконатись, що дозвіл і підписка
    справді працюють, не чекаючи реальної тривоги чи нової новини в черзі."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    push_module.send_push_to_admin(
        admin_id, "Тестове сповіщення", "Push-сповіщення налаштовано і працює ✅", url="/", tag="test",
    )
    return jsonify({"ok": True})


# ---------- Предложка (модерація) ----------

@app.route("/api/submissions", methods=["GET"])
def api_submissions():
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    status = request.args.get("status")
    items = storage.get_submissions_for_admin(admin_id, status)
    for it in items:
        it["viewer_role"] = storage.get_channel_role(admin_id, it.get("target_channel_id"))
    items = sorted(items, key=lambda it: it["id"], reverse=True)
    return jsonify(items)


@app.route("/api/submissions/status", methods=["POST"])
def api_submissions_status():
    sid = request.json.get("id")
    status = request.json.get("status")

    item = next((it for it in storage.get_submissions() if it["id"] == sid), None)
    if not item:
        return jsonify({"ok": False, "error": "403 Forbidden"}), 403
    admin_id, err = require_role(request, item.get("target_channel_id"), "moderator")
    if err:
        return err

    ok = storage.set_submission_status(sid, status, decided_by=admin_id)
    if ok and status == "rejected" and item.get("target_channel_id"):
        _log_editor_action_for_channels(admin_id, [item["target_channel_id"]], "submission_reject", _reaction_seconds_since(item.get("created_at")))
    return jsonify({"ok": ok})


@app.route("/api/submissions/approve-with-media", methods=["POST"])
def api_submissions_approve_with_media():
    """Публікує фото з накладеним на клієнті водяним знаком (нові байти зображення, не file_id)."""
    sid = request.form.get("id", type=int)
    channel_id = request.form.get("channel_id", type=int)
    content = request.form.get("content", "")
    append_footer = request.form.get("append_footer") == "true"
    image_file = request.files.get("image")

    if not channel_id or not image_file:
        return jsonify({"ok": False, "error": "Бракує каналу або зображення"}), 400
    admin_id, err = require_role(request, channel_id, "moderator")
    if err:
        return err

    MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20 МБ — окрема перевірка понад глобальний MAX_CONTENT_LENGTH
    content_length = image_file.content_length or 0
    if content_length and content_length > MAX_IMAGE_BYTES:
        return jsonify({"ok": False, "error": "Зображення завелике (макс. 20 МБ)"}), 413

    items = storage.get_submissions_for_admin(admin_id)
    item = next((it for it in items if it["id"] == sid), None)
    if not item:
        return jsonify({"ok": False, "error": "Пропозицію не знайдено"}), 404
    lock = storage.get_edit_lock("submission", sid)
    if lock and lock.get("admin_id") != admin_id:
        return jsonify({"ok": False, "error": f"Зараз редагує {lock.get('admin_name') or 'інший адмін'} — збереження заблоковано"}), 409

    try:
        image_bytes = image_file.read(MAX_IMAGE_BYTES + 1)
    except MemoryError:
        return jsonify({"ok": False, "error": "Зображення завелике — не вдалося обробити"}), 413
    if len(image_bytes) > MAX_IMAGE_BYTES:
        return jsonify({"ok": False, "error": "Зображення завелике (макс. 20 МБ)"}), 413
    storage.edit_submission(sid, caption=content)

    async def _enqueue():
        local_bot = Bot(token=BOT_TOKEN)
        return await bot_module.enqueue_submission_for_publish(
            local_bot, item, [channel_id], content,
            append_footer=append_footer, extra_media_bytes=image_bytes,
        )

    try:
        asyncio.run(_enqueue())
        asyncio.run(bot_module._process_publish_queue(Bot(token=BOT_TOKEN)))  # негайно, якщо канал вільний
    except Exception as e:
        logger.warning(f"Не вдалося поставити в чергу предложку {sid} з водяним знаком: {e}")
        storage.log_error(f"Постановка в чергу з водяним знаком {sid}: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

    storage.approve_submission(sid, [channel_id], decided_by=admin_id)
    _log_editor_action_for_channels(admin_id, [channel_id], "submission_approve", _reaction_seconds_since(item.get("created_at")))
    return jsonify({"ok": True})


@app.route("/api/submissions/approve", methods=["POST"])
def api_submissions_approve():
    """Зберігає відредагований текст, публікує в ОБРАНІ (одне чи кілька) канали і позначає предложку схваленою.
    Кожен канал отримує СВІЙ власний підпис (назва+посилання саме цього каналу), якщо append_footer увімкнено.
    Guard Check: усі канали публікації обов'язково мають належати цьому admin_id."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()

    data = request.json or {}
    sid = data.get("id")
    raw_channel_ids = data.get("channel_ids") or data.get("channel_id")
    channel_ids = raw_channel_ids if isinstance(raw_channel_ids, list) else [raw_channel_ids]
    channel_ids = [c for c in channel_ids if c]
    content = data.get("content", "")
    append_footer = bool(data.get("append_footer"))

    if not channel_ids:
        return jsonify({"ok": False, "error": "Оберіть хоча б один канал для публікації"}), 400

    for cid in channel_ids:
        if not storage.role_at_least(storage.get_channel_role(admin_id, cid), "moderator"):
            return jsonify({"ok": False, "error": "403 Forbidden: недостатньо прав на один з обраних каналів"}), 403

    items = storage.get_submissions_for_admin(admin_id)
    item = next((it for it in items if it["id"] == sid), None)
    if not item:
        return jsonify({"ok": False, "error": "Пропозицію не знайдено"}), 404
    lock = storage.get_edit_lock("submission", sid)
    if lock and lock.get("admin_id") != admin_id:
        return jsonify({"ok": False, "error": f"Зараз редагує {lock.get('admin_name') or 'інший адмін'} — збереження заблоковано"}), 409

    if item["type"] == "text":
        storage.edit_submission(sid, content=content)
    else:
        storage.edit_submission(sid, caption=content)

    async def _enqueue():
        local_bot = Bot(token=BOT_TOKEN)
        return await bot_module.enqueue_submission_for_publish(
            local_bot, item, channel_ids, content, append_footer=append_footer,
        )

    try:
        asyncio.run(_enqueue())
        asyncio.run(bot_module._process_publish_queue(Bot(token=BOT_TOKEN)))  # негайно, якщо канал вільний (п.2 ТЗ)
    except Exception as e:
        logger.warning(f"Не вдалося поставити в чергу предложку {sid}: {e}")
        storage.log_error(f"Постановка в чергу предложки {sid}: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

    storage.approve_submission(sid, channel_ids, decided_by=admin_id)
    _log_editor_action_for_channels(admin_id, channel_ids, "submission_approve", _reaction_seconds_since(item.get("created_at")))
    return jsonify({"ok": True})


# ---------- Шаблони адміна ----------

@app.route("/api/templates", methods=["GET"])
def api_templates_list():
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    return jsonify(storage.get_templates(admin_id))


@app.route("/api/templates", methods=["POST"])
def api_templates_add():
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    title = (request.json or {}).get("title", "").strip()
    text_pattern = (request.json or {}).get("text_pattern", "").strip()
    if not title or not text_pattern:
        return jsonify({"ok": False, "error": "Вкажи назву і текст шаблону"}), 400
    entry = storage.add_template(admin_id, title, text_pattern)
    return jsonify({"ok": True, "template": entry})


@app.route("/api/templates/<int:template_id>", methods=["DELETE"])
def api_templates_delete(template_id):
    if not check_admin(request):
        return _auth_error_response()
    ok = storage.remove_template(template_id)
    return jsonify({"ok": ok})


@app.route("/api/submissions/remove-album-item", methods=["POST"])
def api_submissions_remove_album_item():
    """Видаляє один файл з альбому (мінімум 1 файл має залишитись)."""
    sid = request.json.get("id")
    index = request.json.get("index")

    item = next((it for it in storage.get_submissions() if it["id"] == sid), None)
    if not item:
        return jsonify({"ok": False, "error": "403 Forbidden"}), 403
    admin_id, err = require_role(request, item.get("target_channel_id"), "editor")
    if err:
        return err

    updated = storage.remove_album_item(sid, index)
    if updated is None:
        return jsonify({"ok": False, "error": "Не вдалося видалити (можливо, це останній файл в альбомі)"}), 400
    return jsonify({"ok": True, "item": updated})


@app.route("/api/submissions/edit", methods=["POST"])
def api_submissions_edit():
    sid = request.json.get("id")

    item = next((it for it in storage.get_submissions() if it["id"] == sid), None)
    if not item:
        return jsonify({"ok": False, "error": "403 Forbidden"}), 403
    admin_id, err = require_role(request, item.get("target_channel_id"), "editor")
    if err:
        return err

    content = request.json.get("content")
    caption = request.json.get("caption")
    ok = storage.edit_submission(sid, content=content, caption=caption)
    return jsonify({"ok": ok})


@app.route("/api/submission-media/<int:submission_id>", methods=["GET"])
def api_submission_media(submission_id):
    """Проксирует фото/відео предложки. Для альбомів (type=album) — параметр ?index=N
    вибирає конкретний елемент зі списку content."""
    items = storage.get_submissions()
    item = next((it for it in items if it["id"] == submission_id), None)
    if not item or item.get("type") not in ("photo", "video", "album"):
        return jsonify({"error": "not_found"}), 404
    admin_id, err = require_role(request, item.get("target_channel_id"), "moderator")
    if err:
        return err

    if item["type"] == "album":
        index = request.args.get("index", 0, type=int)
        album_items = item.get("content") or []
        if index < 0 or index >= len(album_items):
            return jsonify({"error": "index_out_of_range"}), 404
        file_id = album_items[index]["file_id"]
        media_type = album_items[index]["type"]
    else:
        file_id = item["content"]
        media_type = item["type"]

    async def _fetch():
        try:
            file = await Bot(token=BOT_TOKEN).get_file(file_id)
        except Exception as e:
            raise RuntimeError(f"get_file не спрацював (можливо, невірний file_id): {e}")
        file_url = file.file_path if file.file_path.startswith("http") else f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(file_url, timeout=15)
                resp.raise_for_status()
                return resp.content
        except Exception as e:
            raise RuntimeError(f"Файл знайдено (file_path={file.file_path}), але завантаження не вдалося: {e}")

    try:
        media_bytes = asyncio.run(_fetch())
    except Exception as e:
        logger.warning(f"Не вдалося отримати медіа предложки {submission_id}: {e}")
        storage.log_error(f"Медіа предложки {submission_id}: {e}")
        return jsonify({"error": str(e) or "fetch_failed"}), 500

    mimetype = "video/mp4" if media_type == "video" else "image/jpeg"
    return Response(media_bytes, mimetype=mimetype, headers={"Cache-Control": "public, max-age=3600"})


# ---------- Тех. Розділ (суперадмін) ----------

@app.route("/api/dev/channels", methods=["GET"])
def api_dev_channels():
    if not check_superadmin(request):
        return _auth_error_response()
    return jsonify(storage.get_channels())


@app.route("/api/dev/reassign-channel", methods=["POST"])
def api_dev_reassign_channel():
    if not check_superadmin(request):
        return _auth_error_response()
    data = request.json or {}
    channel_id = data.get("channel_id")
    new_admin_id = data.get("new_admin_id")
    if not channel_id or not new_admin_id:
        return jsonify({"ok": False, "error": "Вкажи channel_id і new_admin_id"}), 400
    ok = storage.reassign_channel(channel_id, new_admin_id)
    return jsonify({"ok": ok})


@app.route("/api/dev/add-channel", methods=["POST"])
def api_dev_add_channel():
    if not check_superadmin(request):
        return _auth_error_response()
    data = request.json or {}
    chat_id = data.get("chat_id")
    title = data.get("title", "").strip()
    admin_id = data.get("admin_id")
    if not chat_id or not title or not admin_id:
        return jsonify({"ok": False, "error": "Вкажи chat_id, title і admin_id"}), 400
    ok = storage.manual_add_channel(chat_id, title, admin_id)
    return jsonify({"ok": ok})


@app.route("/api/dev/ban-channel", methods=["POST"])
def api_dev_ban_channel():
    if not check_superadmin(request):
        return _auth_error_response()
    data = request.json or {}
    channel_id = data.get("channel_id")
    banned = bool(data.get("banned"))
    ok = storage.set_channel_banned(channel_id, banned)
    return jsonify({"ok": ok})


@app.route("/api/dev/users", methods=["GET"])
def api_dev_users():
    if not check_superadmin(request):
        return _auth_error_response()
    query = request.args.get("query", "")
    if not query:
        return jsonify([])
    return jsonify(storage.search_users(query))


@app.route("/api/dev/stats", methods=["GET"])
def api_dev_stats():
    if not check_superadmin(request):
        return _auth_error_response()
    stats = storage.get_platform_stats()
    stats["maintenance_mode"] = storage.is_maintenance_mode()
    return jsonify(stats)


@app.route("/api/dev/maintenance", methods=["POST"])
def api_dev_maintenance():
    if not check_superadmin(request):
        return _auth_error_response()
    enabled = bool((request.json or {}).get("enabled"))
    storage.set_setting("maintenance_mode", enabled)
    return jsonify({"ok": True, "maintenance_mode": enabled})


@app.route("/api/dev/errors", methods=["GET"])
def api_dev_errors():
    if not check_superadmin(request):
        return _auth_error_response()
    return jsonify(storage.get_errors())


# ---------- Відкладена публікація (планувальник, POST /api/schedule) ----------

@app.route("/api/schedule", methods=["POST"])
def api_schedule():
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    publish_at = (data.get("publish_at") or "").strip()
    if not title:
        return jsonify({"error": "title_required"}), 400
    if not publish_at:
        return jsonify({"error": "publish_at_required"}), 400
    try:
        datetime.fromisoformat(publish_at)
    except ValueError:
        return jsonify({"error": "bad_publish_at", "hint": "ISO 8601, напр. 2026-08-02T15:30:00"}), 400

    channel_ids = data.get("channel_ids") or []
    if channel_ids:
        admin_channel_ids = {c["id"] for c in storage.get_channels_for_admin(admin_id)}
        channel_ids = [cid for cid in channel_ids if cid in admin_channel_ids]

    item = storage.add_scheduled_post(
        title=title,
        publish_at=publish_at,
        text=data.get("text") or "",
        channel_ids=channel_ids,
    )
    return jsonify(item), 201


# ---------- Черга публікації новин (кожен адмін бачить лише свою частину) ----------

@app.route("/api/queue", methods=["GET"])
def api_queue():
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    items = storage.get_queue_for_admin(admin_id)
    channels = storage.get_channels_with_role_for_admin(admin_id, "moderator")
    cd_minutes = storage.get_setting("autopost_cd_minutes", 15)
    now = datetime.now()

    for it in items:
        it["viewer_role"] = _queue_item_role(admin_id, it)
        delivered = set(it.get("delivered_channel_ids", []))
        channel_status = []
        for c in channels:
            if c["id"] not in it.get("channel_ids", []):
                continue
            is_delivered = c["id"] in delivered
            seconds_left = 0
            if not is_delivered:
                last_pub = storage.get_channel_last_published(c["id"])
                if last_pub:
                    try:
                        elapsed = (now - datetime.fromisoformat(last_pub)).total_seconds()
                        seconds_left = max(0, int(cd_minutes * 60 - elapsed))
                    except Exception:
                        seconds_left = 0
            channel_status.append({"id": c["id"], "title": c["title"], "delivered": is_delivered, "seconds_left": seconds_left})
        it["channel_titles"] = [c["title"] for c in channels if c["id"] in it.get("channel_ids", [])]
        it["channel_status"] = channel_status

        # Тип контенту для іконки в списку (щоб адмін бачив фото/відео/альбом, не
        # відкриваючи кожну новину) — визначаємо по розширенню збережених на диску файлів.
        media_paths = it.get("media_paths") or []
        media_types = ["video" if p.lower().endswith(".mp4") else "photo" for p in media_paths]
        has_photo = "photo" in media_types
        has_video = "video" in media_types
        if has_photo and has_video:
            media_kind = "mixed"
        elif has_video:
            media_kind = "video"
        elif has_photo:
            media_kind = "photo"
        else:
            media_kind = "none"
        it["media_kind"] = media_kind
        it["media_count"] = len(media_paths)
        it["media_types"] = media_types
        it.pop("media_paths", None)  # локальні шляхи на диску сервера — фронту не потрібні й не варто світити
    items.sort(key=lambda it: it.get("created_at", ""), reverse=True)  # новини — новіші зверху
    items.sort(key=lambda it: not it.get("priority"))  # а над усім — пріоритетні (редакційні) зверху
    return jsonify(items)


def _queue_item_role(admin_id: int, item: dict) -> str | None:
    """Найвища роль адміна серед усіх каналів-цілей цього запису черги."""
    best = None
    for cid in item.get("channel_ids", []):
        role = storage.get_channel_role(admin_id, cid)
        if role and (best is None or storage.ROLE_RANK[role] > storage.ROLE_RANK[best]):
            best = role
    return best


def _admin_has_queue_role(admin_id: int, item: dict, min_role: str = "moderator") -> bool:
    return storage.role_at_least(_queue_item_role(admin_id, item), min_role)


def _reaction_seconds_since(created_at: str | None) -> float | None:
    if not created_at:
        return None
    try:
        return (datetime.now() - datetime.fromisoformat(created_at)).total_seconds()
    except Exception:
        return None


def _log_editor_action_for_channels(admin_id: int, channel_ids: list, kind: str, reaction_seconds: float | None) -> None:
    """Дашборд ефективності команди (get_editor_stats) рахує по каналах —
    один запис на кожен канал, куди справді йшла ця дія (queue-новина може
    йти в кілька каналів одразу)."""
    for cid in channel_ids or []:
        storage.log_editor_action(admin_id, cid, kind, reaction_seconds)


@app.route("/api/queue/remove", methods=["POST"])
def api_queue_remove():
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    item_id = (request.json or {}).get("id")
    item = storage.get_queue_item(item_id)
    if not item or not _admin_has_queue_role(admin_id, item, "editor"):
        return jsonify({"ok": False, "error": "Новину не знайдено або бракує прав"}), 404
    removed = storage.remove_queue_item(item_id)
    if removed:
        bot_module._delete_queue_media_files(removed.get("media_paths"))
    return jsonify({"ok": bool(removed)})


@app.route("/api/queue/approve", methods=["POST"])
def api_queue_approve():
    """Схвалення новини з черги: переводить pending -> queued. Тільки після цього
    новина потрапляє в цикл автопостингу і вийде по настанню КД каналу — без
    цього виклику вона так і лишиться чекати в черзі й ніколи не опублікується."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    item_id = (request.json or {}).get("id")
    item = storage.get_queue_item(item_id)
    if not item or not _admin_has_queue_role(admin_id, item, "moderator"):
        return jsonify({"ok": False, "error": "Новину не знайдено або бракує прав"}), 404
    if item.get("status") != "pending":
        return jsonify({"ok": False, "error": "Новина вже схвалена або оброблена"}), 400
    reaction_seconds = _reaction_seconds_since(item.get("created_at"))
    ok = storage.approve_queue_item(item_id, approved_by=admin_id)
    if ok:
        _pin_approved_queue_item(item_id)
        _log_editor_action_for_channels(admin_id, item.get("channel_ids", []), "queue_approve", reaction_seconds)
    return jsonify({"ok": ok})


def _pin_approved_queue_item(item_id: int) -> None:
    """Службове повідомлення-пін у чаті редакції (п.2.3 ТЗ) — best-effort, не валить
    основний запит, якщо пін не вдався (наприклад, бот не адмін у тому чаті)."""
    item = storage.get_queue_item(item_id)
    if not item:
        return
    try:
        asyncio.run(bot_module.pin_queue_item_notice(Bot(token=BOT_TOKEN), item))
    except Exception as e:
        logger.warning(f"Не вдалося запінити новину {item_id}: {e}")



@app.route("/api/queue/add-media", methods=["POST"])
def api_queue_add_media():
    """Кнопка "+" в редагуванні черги — адмін вручну докидає фото/відео до новини
    (навіть якщо вона спершу була текстовою). Файл приймається як multipart/form-data."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    item_id = request.form.get("id", type=int)
    item = storage.get_queue_item(item_id)
    if not item or not _admin_has_queue_role(admin_id, item, "editor"):
        return jsonify({"ok": False, "error": "Новину не знайдено або бракує прав"}), 404

    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"ok": False, "error": "Файл не передано"}), 400

    content_type = file.content_type or ""
    is_video = content_type.startswith("video/")
    is_photo = content_type.startswith("image/")
    if not (is_video or is_photo):
        return jsonify({"ok": False, "error": "Підтримуються лише зображення і відео"}), 400

    ext = "mp4" if is_video else "jpg"
    os.makedirs(storage.QUEUE_MEDIA_DIR, exist_ok=True)
    filename = f"{item_id}_add_{uuid.uuid4().hex[:8]}.{ext}"
    path = os.path.join(storage.QUEUE_MEDIA_DIR, filename)
    file.save(path)

    updated = storage.add_queue_media_item(item_id, path)
    if not updated:
        return jsonify({"ok": False, "error": "Не вдалося додати файл"}), 400

    media_paths = updated.get("media_paths") or []
    media_types = ["video" if p.lower().endswith(".mp4") else "photo" for p in media_paths]
    return jsonify({"ok": True, "media_count": len(media_paths), "media_types": media_types})


@app.route("/api/queue/remove-media", methods=["POST"])
def api_queue_remove_media():
    """Прибирає одне фото/відео з новини в черзі за індексом (кнопка "✕" на
    мініатюрі в редагуванні) — назавжди стирає файл із диска, не лише посилання."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    data = request.json or {}
    item_id = data.get("id")
    index = data.get("index")
    item = storage.get_queue_item(item_id)
    if not item or not _admin_has_queue_role(admin_id, item, "editor"):
        return jsonify({"ok": False, "error": "Новину не знайдено або бракує прав"}), 404
    if not isinstance(index, int):
        return jsonify({"ok": False, "error": "Некоректний індекс"}), 400
    result = storage.remove_queue_media_item(item_id, index)
    if not result:
        return jsonify({"ok": False, "error": "Індекс поза межами"}), 400
    removed_path = result.get("removed_path")
    if removed_path and os.path.exists(removed_path):
        try:
            os.remove(removed_path)
        except Exception as e:
            logger.warning(f"Не вдалося стерти файл {removed_path}: {e}")
    media_paths = result["item"].get("media_paths") or []
    media_types = ["video" if p.lower().endswith(".mp4") else "photo" for p in media_paths]
    return jsonify({"ok": True, "media_count": len(media_paths), "media_types": media_types})


@app.route("/api/queue-media/<int:item_id>", methods=["GET"])
def api_queue_media(item_id):
    """Віддає медіафайл новини з черги (для прев'ю прямо в панелі редагування) —
    на відміну від submission-media, тут файли вже лежать НА ДИСКУ (queue_media/),
    завантажені заздалегідь під час постановки в чергу, тож проксити через
    Telegram get_file не треба. ?index=N вибирає конкретний елемент альбому."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    item = storage.get_queue_item(item_id)
    if not item or not _admin_has_queue_role(admin_id, item, "moderator"):
        return jsonify({"error": "not_found"}), 404

    media_paths = item.get("media_paths") or []
    index = request.args.get("index", 0, type=int)
    if index < 0 or index >= len(media_paths):
        return jsonify({"error": "index_out_of_range"}), 404

    path = media_paths[index]
    if not os.path.exists(path):
        return jsonify({"error": "file_missing"}), 404

    mimetype = "video/mp4" if path.lower().endswith(".mp4") else "image/jpeg"
    with open(path, "rb") as f:
        data = f.read()
    return Response(data, mimetype=mimetype, headers={"Cache-Control": "no-store"})


@app.route("/api/queue/set-channels", methods=["POST"])
def api_queue_set_channels():
    """Дозволяє адміну самому обрати, у які З ЙОГО каналів піде ця новина — на
    додачу чи замість тих, що потрапили туди автоматично за збігом джерела й
    ключових слів. Приймає тільки канали, якими адмін реально володіє — навіть
    якщо хтось підмінить запит, чужий канал сюди не потрапить."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    data = request.json or {}
    item_id = data.get("id")
    item = storage.get_queue_item(item_id)
    if not item or not _admin_has_queue_role(admin_id, item, "editor"):
        return jsonify({"ok": False, "error": "Новину не знайдено або бракує прав"}), 404
    requested_ids = data.get("channel_ids")
    if not isinstance(requested_ids, list) or not requested_ids:
        return jsonify({"ok": False, "error": "Потрібно обрати хоча б один канал"}), 400
    admin_channel_ids = {c["id"] for c in storage.get_channels_with_role_for_admin(admin_id, "editor")}
    valid_ids = [cid for cid in requested_ids if cid in admin_channel_ids]
    if not valid_ids:
        return jsonify({"ok": False, "error": "Жоден з обраних каналів вам не належить"}), 400
    storage.update_queue_item(item_id, channel_ids=valid_ids)
    return jsonify({"ok": True})


@app.route("/api/ai-rewrite", methods=["POST"])
def api_ai_rewrite():
    """Ручний ІІ-рерайт тексту прямо в редакторі (кнопка на тулбарі) — той самий
    _ai_rewrite_html, що й в автопостингу, але за явним запитом адміна, а не
    автоматично для кожної новини. Приймає HTML-текст (з тегами <b>/<i>/... —
    вони збережуться), повертає переписаний варіант тією ж мовою."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    data = request.json or {}
    text = data.get("text", "")
    if not text.strip():
        return jsonify({"ok": False, "error": "Текст порожній"}), 400
    style = data.get("style") or "neutral"
    if style not in ("neutral", "official", "urgent", "summary"):
        style = "neutral"
    lang = storage.get_admin_language(admin_id) or "ua"
    try:
        rewritten = asyncio.run(bot_module._ai_rewrite_html(text, lang, style))
    except Exception as e:
        logger.warning(f"Не вдалося виконати ручний ІІ-рерайт: {e}")
        return jsonify({"ok": False, "error": "ІІ зараз недоступний, спробуй пізніше"}), 502
    if rewritten.strip() == text.strip():
        return jsonify({"ok": False, "error": "ІІ не налаштовано (немає GEMINI_API_KEY) або рерайт не вдався"}), 503
    return jsonify({"ok": True, "text": rewritten})


@app.route("/api/ai-title-tags", methods=["POST"])
def api_ai_title_tags():
    """Генерація заголовка+хештегів одним кліком (кнопка «Заголовок» у редакторі,
    п.1.1 ТЗ) — окремий виклик Gemini, результат додається адміном у текст вручну."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    data = request.json or {}
    text = data.get("text", "")
    if not text.strip():
        return jsonify({"ok": False, "error": "Текст порожній"}), 400
    lang = storage.get_admin_language(admin_id) or "ua"
    try:
        result = asyncio.run(bot_module._ai_suggest_title_tags(text, lang))
    except Exception as e:
        logger.warning(f"Не вдалося згенерувати заголовок/хештеги: {e}")
        return jsonify({"ok": False, "error": "ІІ зараз недоступний, спробуй пізніше"}), 502
    if not result.get("title") and not result.get("hashtags"):
        return jsonify({"ok": False, "error": "ІІ не налаштовано (немає GEMINI_API_KEY) або генерація не вдалася"}), 503
    return jsonify({"ok": True, "title": result.get("title", ""), "hashtags": result.get("hashtags", "")})


@app.route("/api/edit-lock/acquire", methods=["POST"])
def api_edit_lock_acquire():
    """Проста pessimistic-блокування посту в редакторі: хто відкрив першим —
    той редагує, решта бачать банер і не можуть зберегти (не realtime-merge,
    просто щоб два редактори не затерли правки один одного)."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    data = request.json or {}
    kind = data.get("kind")
    item_id = data.get("id")
    admin_name = (data.get("admin_name") or "").strip()
    if kind not in ("queue", "submission") or not item_id:
        return jsonify({"ok": False, "error": "Некоректні параметри"}), 400
    return jsonify(storage.acquire_edit_lock(kind, item_id, admin_id, admin_name))


@app.route("/api/edit-lock/heartbeat", methods=["POST"])
def api_edit_lock_heartbeat():
    """Пінг раз на ~20с, поки редактор відкритий — без нього лок згасне за
    EDIT_LOCK_TIMEOUT_SECONDS і хтось інший зможе перехопити пост."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    data = request.json or {}
    kind = data.get("kind")
    item_id = data.get("id")
    if kind not in ("queue", "submission") or not item_id:
        return jsonify({"ok": False, "error": "Некоректні параметри"}), 400
    return jsonify({"ok": storage.refresh_edit_lock(kind, item_id, admin_id)})


@app.route("/api/edit-lock/release", methods=["POST"])
def api_edit_lock_release():
    """Явний реліз при закритті редактора — щоб наступний не чекав тайм-аута."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    data = request.json or {}
    kind = data.get("kind")
    item_id = data.get("id")
    if kind in ("queue", "submission") and item_id:
        storage.release_edit_lock(kind, item_id, admin_id)
    return jsonify({"ok": True})


@app.route("/api/queue/edit", methods=["POST"])
def api_queue_edit():
    """Редагування тексту новини прямо в черзі, перед тим як вона вийде (п.5.Б ТЗ).
    Заодно приймає skip_watermark — вимкнути водяний знак САМЕ для цієї новини."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    data = request.json or {}
    item_id = data.get("id")
    item = storage.get_queue_item(item_id)
    if not item or not _admin_has_queue_role(admin_id, item, "editor"):
        return jsonify({"ok": False, "error": "Новину не знайдено або бракує прав"}), 404
    lock = storage.get_edit_lock("queue", item_id)
    if lock and lock.get("admin_id") != admin_id:
        return jsonify({"ok": False, "error": f"Зараз редагує {lock.get('admin_name') or 'інший адмін'} — збереження заблоковано"}), 409
    text = data.get("text")
    if text is None or not text.strip():
        return jsonify({"ok": False, "error": "Текст не може бути порожнім"}), 400
    fields = {"text": text}
    if "skip_watermark" in data:
        fields["skip_watermark"] = bool(data["skip_watermark"])
    if "append_footer" in data:
        fields["append_footer"] = bool(data["append_footer"])
    storage.update_queue_item(item_id, **fields)

    was_pending = item.get("status") == "pending"
    if was_pending:
        # п.2 ТЗ: "Зберегти" в редакторі одразу схвалює пост і ставить його в чергу —
        # окремо тиснути "Схвалити" більше не треба.
        reaction_seconds = _reaction_seconds_since(item.get("created_at"))
        storage.approve_queue_item(item_id, approved_by=admin_id)
        _pin_approved_queue_item(item_id)
        _log_editor_action_for_channels(admin_id, item.get("channel_ids", []), "queue_approve", reaction_seconds)
        try:
            asyncio.run(bot_module._process_publish_queue(Bot(token=BOT_TOKEN)))
        except Exception as e:
            logger.warning(f"Не вдалося одразу опублікувати новину {item_id} після збереження: {e}")

    return jsonify({"ok": True, "approved": was_pending})


@app.route("/api/queue/publish-now", methods=["POST"])
def api_queue_publish_now():
    """Публікує новину з черги негайно, скидаючи поточний КД (п.5.Б ТЗ, кнопка 🚀)."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    item_id = (request.json or {}).get("id")
    item = storage.get_queue_item(item_id)
    if not item or item.get("status") != "queued" or not _admin_has_queue_role(admin_id, item, "moderator"):
        return jsonify({"ok": False, "error": "Новину не знайдено в черзі, або бракує прав"}), 404

    async def _go():
        local_bot = Bot(token=BOT_TOKEN)
        await bot_module._force_publish_item(local_bot, item)

    try:
        asyncio.run(_go())
    except Exception as e:
        logger.warning(f"Не вдалося опублікувати чергу {item_id} негайно: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
    return jsonify({"ok": True})


@app.route("/api/queue/publish-now-nocd", methods=["POST"])
def api_queue_publish_now_nocd():
    """"⚡ Без КД" (п.3 ТЗ) — те саме, що publish-now, але НЕ скидає таймер КД
    каналу, тож розклад решти черги лишається незмінним."""
    admin_id = check_admin(request)
    if not admin_id:
        return _auth_error_response()
    item_id = (request.json or {}).get("id")
    item = storage.get_queue_item(item_id)
    if not item or item.get("status") != "queued" or not _admin_has_queue_role(admin_id, item, "moderator"):
        return jsonify({"ok": False, "error": "Новину не знайдено в черзі, або бракує прав"}), 404

    async def _go():
        local_bot = Bot(token=BOT_TOKEN)
        await bot_module._force_publish_item(local_bot, item, reset_cooldown=False)

    try:
        asyncio.run(_go())
    except Exception as e:
        logger.warning(f"Не вдалося опублікувати чергу {item_id} без КД: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
    return jsonify({"ok": True, "published_at": datetime.now().isoformat()})


# ---------- Тех.розділ: глобальні налаштування автопостингу + лог відхилених дублів ----------
# Це загальнобот-платформна настройка (одна черга й один КД на весь інстанс бота), тому
# доступна лише суперадміну — звичайний адмін не може випадково призупинити автопостинг
# усім іншим адмінам платформи.

@app.route("/api/dev/autopost", methods=["GET"])
def api_dev_autopost_get():
    if not check_superadmin(request):
        return _auth_error_response()
    return jsonify({
        "enabled": storage.get_setting("autopost_enabled", True),
        "cd_minutes": storage.get_setting("autopost_cd_minutes", 15),
        "paused_until": storage.get_setting("autopost_paused_until"),
        "last_autopost_at": storage.get_setting("last_autopost_at"),
        "queue_length": len([it for it in storage.get_queue() if it.get("status") == "queued"]),
    })


@app.route("/api/dev/autopost", methods=["POST"])
def api_dev_autopost_set():
    if not check_superadmin(request):
        return _auth_error_response()
    data = request.json or {}
    if "enabled" in data:
        storage.set_setting("autopost_enabled", bool(data["enabled"]))
    if "cd_minutes" in data:
        try:
            cd = max(5, min(60, int(data["cd_minutes"])))
            storage.set_setting("autopost_cd_minutes", cd)
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "КД має бути числом від 5 до 60"}), 400
    return jsonify({"ok": True})


@app.route("/api/debug/pipeline", methods=["GET"])
def api_debug_pipeline():
    """Health-check конвеєра новин: де саме він застряг, якщо застряг."""
    if not check_superadmin(request):
        return _auth_error_response()

    active_sources = [s for s in storage.get_sources() if s.get("enabled", True)]
    queued = [it for it in storage.get_queue() if it.get("status") == "queued"]
    cooldowns = storage.get_all_channel_last_published()
    last_published = max(cooldowns.values(), default=None)
    active_news_channels = [c for c in storage.get_channels() if c.get("news_enabled") and c.get("enabled", True)]

    return jsonify({
        "active_sources_count": len(active_sources),
        "active_news_channels_count": len(active_news_channels),
        "queued_news_count": len(queued),
        "last_parsed_post_time": storage.get_setting("last_check_news_run_at"),
        "last_published_post_time": last_published,
        "autopost_enabled": storage.get_setting("autopost_enabled", True),
        "autopost_paused_until": storage.get_setting("autopost_paused_until"),
        "autopost_cd_minutes": storage.get_setting("autopost_cd_minutes", 15),
    })


if __name__ == "__main__":
    _fetch_bot_username()
    # За замовчуванням (як і завжди) app.py сам піднімає бота у фоновому потоці —
    # зручно для деплою одним процесом (напр. Render). Якщо ж bot.py запускається
    # ОКРЕМИМ процесом (systemd, два сервіси і т.п.) — обидва почнуть polling з
    # тим самим токеном і Telegram відповість Conflict. RUN_BOT_IN_APP=false в
    # .env вимикає внутрішній потік саме для такого випадку.
    if os.environ.get("RUN_BOT_IN_APP", "true").strip().lower() not in ("0", "false", "no"):
        threading.Thread(target=run_bot_in_background, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    # threaded=True — критично: без цього вбудований Flask-сервер обробляє запити
    # СТРОГО по одному. Аватарки каналів (і не тільки) роблять власний похід у
    # Telegram API всередині обробника запиту (asyncio.run(...)) — якщо фронтенд
    # паралельно шле кілька таких запитів (по одному на кожен канал у списку),
    # без threaded=True вони чекають один одного в черзі замість паралельної
    # обробки, і при повільній мережі це виглядає як "запит завис назавжди".
    app.run(host="0.0.0.0", port=port, threaded=True)