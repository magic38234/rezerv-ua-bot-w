import json
import os
from datetime import datetime, timedelta

from data.db import get_connection, init_db

init_db()  # п.1 ТЗ: гарантує api/database.db + всі таблиці ще до першого виклику нижче

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # data/ -> корінь проекту (watermarks/, channel_avatars/, queue_media/ лежать там)


# ==================== Generic-хелпери над SQLite ====================
# Кожна "колекція" (channels/sources/queue/submissions/templates/scheduled_posts) —
# одна таблиця (id, added_by, status, data JSON). added_by/status продубльовані
# окремими індексованими колонками для швидких вибірок, повний запис лежить у data.
# kv_store — одиночні значення (те, що раніше було окремими dict/list JSON-файлами).

def _collection_all(table: str) -> list:
    conn = get_connection()
    rows = conn.execute(f"SELECT data FROM {table} ORDER BY id").fetchall()
    return [json.loads(r["data"]) for r in rows]


def _collection_get(table: str, item_id) -> dict | None:
    conn = get_connection()
    row = conn.execute(f"SELECT data FROM {table} WHERE id=?", (item_id,)).fetchone()
    return json.loads(row["data"]) if row else None


def _collection_insert_autoid(table: str, item: dict, added_by=None, status=None) -> dict:
    """Вставляє новий запис, id генерує сама БД (AUTOINCREMENT) — і одразу
    записує id назад у сам JSON (код скрізь читає item["id"])."""
    conn = get_connection()
    with conn:
        cur = conn.execute(
            f"INSERT INTO {table} (added_by, status, data) VALUES (?,?,?)",
            (added_by, status, json.dumps(item, ensure_ascii=False)),
        )
        new_id = cur.lastrowid
        item = {**item, "id": new_id}
        conn.execute(f"UPDATE {table} SET data=? WHERE id=?", (json.dumps(item, ensure_ascii=False), new_id))
    return item


def _collection_insert_explicit_id(table: str, item: dict, added_by=None, status=None) -> None:
    """Вставляє запис з ВЖЕ заданим id (канали — id = реальний Telegram chat_id)."""
    conn = get_connection()
    with conn:
        conn.execute(
            f"INSERT INTO {table} (id, added_by, status, data) VALUES (?,?,?,?)",
            (item["id"], added_by, status, json.dumps(item, ensure_ascii=False)),
        )


def _collection_replace(table: str, item_id, item: dict, added_by=None, status=None) -> bool:
    conn = get_connection()
    with conn:
        cur = conn.execute(
            f"UPDATE {table} SET data=?, added_by=?, status=? WHERE id=?",
            (json.dumps(item, ensure_ascii=False), added_by, status, item_id),
        )
    return cur.rowcount > 0


def _collection_mutate(table: str, item_id, fn) -> dict | None:
    """Читає запис, дає fn змінити його на місці, зберігає назад в ОДНІЙ транзакції
    (SQLite сам серіалізує паралельний запис — і в межах процесу, і між процесами).
    Повертає оновлений item, або None якщо запису не існує."""
    conn = get_connection()
    with conn:
        row = conn.execute(f"SELECT data FROM {table} WHERE id=?", (item_id,)).fetchone()
        if row is None:
            return None
        item = json.loads(row["data"])
        fn(item)
        conn.execute(
            f"UPDATE {table} SET data=?, added_by=?, status=? WHERE id=?",
            (json.dumps(item, ensure_ascii=False), item.get("added_by"), item.get("status"), item_id),
        )
        return item


def _collection_delete(table: str, item_id) -> bool:
    conn = get_connection()
    with conn:
        cur = conn.execute(f"DELETE FROM {table} WHERE id=?", (item_id,))
    return cur.rowcount > 0


def _kv_get(key: str, default=None):
    conn = get_connection()
    row = conn.execute("SELECT value FROM kv_store WHERE key=?", (key,)).fetchone()
    return json.loads(row["value"]) if row else default


def _kv_set(key: str, value) -> None:
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO kv_store (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value, ensure_ascii=False)),
        )


# ==================== Канали ====================

def get_channels() -> list:
    return _collection_all("channels")


def add_channel(chat_id: int, title: str, added_by: int | None = None, rights: dict | None = None) -> bool:
    """Регистрирует канал или реактивирует существующий. Возвращает True, якщо канал новий."""
    existing = _collection_get("channels", chat_id)
    if existing:
        def _mut(ch):
            ch["title"] = title
            ch["status"] = "active"
            if added_by is not None:
                ch["added_by"] = added_by
            if rights is not None:
                ch["rights"] = rights
        _collection_mutate("channels", chat_id, _mut)
        return False
    item = {
        "id": chat_id,
        "title": title,
        "enabled": True,
        "status": "active",
        "added_by": added_by,
        "added_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "banned": False,
        "category": "",
        "rights": rights or {},
    }
    _collection_insert_explicit_id("channels", item, added_by=added_by, status="active")
    return True


def set_channel_status(chat_id: int, status: str) -> bool:
    return _collection_mutate("channels", chat_id, lambda ch: ch.update(status=status)) is not None


def set_channel_rights(chat_id: int, rights: dict) -> bool:
    return _collection_mutate("channels", chat_id, lambda ch: ch.update(rights=rights)) is not None


def get_active_channels() -> list:
    return [ch for ch in get_channels() if ch.get("status", "active") == "active"]


def get_channels_for_admin(admin_id: int) -> list:
    return [ch for ch in get_channels() if ch.get("added_by") == admin_id]


def is_channel_owner(admin_id: int, channel_id: int) -> bool:
    ch = _collection_get("channels", channel_id)
    return bool(ch) and ch.get("added_by") == admin_id


def get_channel_invite_link(channel_id: int) -> str | None:
    ch = _collection_get("channels", channel_id)
    return ch.get("invite_link") if ch else None


def set_channel_invite_link(channel_id: int, link: str) -> None:
    _collection_mutate("channels", channel_id, lambda ch: ch.update(invite_link=link))


def set_channel_enabled(chat_id: int, enabled: bool) -> bool:
    return _collection_mutate("channels", chat_id, lambda ch: ch.update(enabled=enabled)) is not None


def is_channel_enabled(chat_id: int) -> bool:
    ch = _collection_get("channels", chat_id)
    return ch.get("enabled", True) if ch else False


def set_channel_news_enabled(chat_id: int, enabled: bool) -> bool:
    return _collection_mutate("channels", chat_id, lambda ch: ch.update(news_enabled=enabled)) is not None


def is_channel_news_enabled(chat_id: int) -> bool:
    ch = _collection_get("channels", chat_id)
    return ch.get("news_enabled", False) if ch else False


def set_channel_keywords(chat_id: int, keywords: list) -> bool:
    return _collection_mutate("channels", chat_id, lambda ch: ch.update(news_keywords=keywords)) is not None


def get_channel_keywords(chat_id: int) -> list:
    ch = _collection_get("channels", chat_id)
    return ch.get("news_keywords", []) if ch else []


def remove_channel(chat_id: int) -> bool:
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM channel_members WHERE channel_id=?", (chat_id,))
    return _collection_delete("channels", chat_id)


def reassign_channel(channel_id: int, new_admin_id: int) -> bool:
    return _collection_mutate("channels", channel_id, lambda ch: ch.update(added_by=new_admin_id)) is not None


def manual_add_channel(chat_id: int, title: str, admin_id: int) -> bool:
    return add_channel(chat_id, title, added_by=admin_id)


def set_channel_banned(channel_id: int, banned: bool) -> bool:
    return _collection_mutate("channels", channel_id, lambda ch: ch.update(banned=banned)) is not None


def is_channel_banned(channel_id: int) -> bool:
    ch = _collection_get("channels", channel_id)
    return ch.get("banned", False) if ch else False


def set_channel_category(channel_id: int, category: str) -> bool:
    return _collection_mutate("channels", channel_id, lambda ch: ch.update(category=category.strip())) is not None


# ==================== Команда каналу (Owner / Editor / Moderator) ====================
# Owner ніде окремо не зберігається — він завжди виводиться з channels.added_by
# (це і дає нульову міграцію: у всіх існуючих каналів added_by вже є). У таблиці
# channel_members лежать тільки Editor/Moderator, яких власник додав додатково.
ROLE_RANK = {"moderator": 1, "editor": 2, "owner": 3}


def role_at_least(role: str | None, min_role: str) -> bool:
    if role is None:
        return False
    return ROLE_RANK.get(role, 0) >= ROLE_RANK.get(min_role, 0)


def get_channel_role(user_id: int, channel_id: int) -> str | None:
    ch = _collection_get("channels", channel_id)
    if not ch:
        return None
    if ch.get("added_by") == user_id:
        return "owner"
    conn = get_connection()
    row = conn.execute(
        "SELECT role FROM channel_members WHERE channel_id=? AND user_id=?",
        (channel_id, user_id),
    ).fetchone()
    return row["role"] if row else None


def get_channel_members(channel_id: int) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT user_id, role, added_by, added_at FROM channel_members WHERE channel_id=? ORDER BY added_at",
        (channel_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_admin_ids_for_channel(channel_id: int) -> list:
    """Owner + вся команда (editor/moderator) цього каналу — для розсилки
    push-сповіщень про критичні події (тривоги, нові елементи черги) усім,
    хто має доступ до каналу, а не лише власнику."""
    ch = _collection_get("channels", channel_id)
    ids = set()
    if ch and ch.get("added_by"):
        ids.add(ch["added_by"])
    for m in get_channel_members(channel_id):
        ids.add(m["user_id"])
    return list(ids)


def add_channel_member(channel_id: int, user_id: int, role: str, added_by: int) -> dict | None:
    if role not in ("editor", "moderator"):
        return None
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO channel_members (channel_id, user_id, role, added_by, added_at) VALUES (?,?,?,?,?) "
            "ON CONFLICT(channel_id, user_id) DO UPDATE SET role=excluded.role",
            (channel_id, user_id, role, added_by, datetime.now().isoformat()),
        )
    return {"user_id": user_id, "role": role}


def update_channel_member_role(channel_id: int, user_id: int, role: str) -> bool:
    if role not in ("editor", "moderator"):
        return False
    conn = get_connection()
    with conn:
        cur = conn.execute(
            "UPDATE channel_members SET role=? WHERE channel_id=? AND user_id=?",
            (role, channel_id, user_id),
        )
    return cur.rowcount > 0


def remove_channel_member(channel_id: int, user_id: int) -> bool:
    conn = get_connection()
    with conn:
        cur = conn.execute("DELETE FROM channel_members WHERE channel_id=? AND user_id=?", (channel_id, user_id))
    return cur.rowcount > 0


def _member_roles_for_admin(user_id: int) -> dict:
    conn = get_connection()
    rows = conn.execute("SELECT channel_id, role FROM channel_members WHERE user_id=?", (user_id,)).fetchall()
    return {r["channel_id"]: r["role"] for r in rows}


def cache_user_profile(user_id: int, first_name: str | None, username: str | None, photo_url: str | None) -> None:
    """Легкий кеш "хто є хто" — наповнюється органічно щоразу, коли будь-хто
    відкриває панель (беремо дані прямо з Telegram WebApp initData цього ж
    запиту). Дозволяє показувати в списку "Команда каналу" ім'я й аватарку
    замість голого user_id — але лише для тих, хто хоч раз відкривав панель
    (а щоб скористатись виданою роллю, це однаково треба зробити)."""
    if not user_id:
        return
    profiles = _kv_get("user_profiles", {}) or {}
    profiles[str(user_id)] = {"first_name": first_name, "username": username, "photo_url": photo_url}
    _kv_set("user_profiles", profiles)


def get_user_profiles(user_ids: list) -> dict:
    profiles = _kv_get("user_profiles", {}) or {}
    return {uid: profiles[str(uid)] for uid in user_ids if str(uid) in profiles}


def find_user_by_username(username: str) -> int | None:
    """Шукає user_id серед закешованих профілів (усі, хто хоч раз відкривав
    панель — див. cache_user_profile) за @username, БЕЗ звернення до Telegram
    API. Регістронезалежно. Не знайде того, хто панель ще жодного разу не
    відкривав, — для цього є фолбек на bot.get_chat("@username") в app.py."""
    username = (username or "").lstrip("@").strip().lower()
    if not username:
        return None
    profiles = _kv_get("user_profiles", {}) or {}
    for uid_str, profile in profiles.items():
        if (profile.get("username") or "").lower() == username:
            try:
                return int(uid_str)
            except ValueError:
                continue
    return None


def get_channels_with_role_for_admin(user_id: int, min_role: str = "moderator") -> list:
    """Розширена версія get_channels_for_admin: включає не тільки свої канали,
    а й ті, де user_id має роль Editor/Moderator (>= min_role). Кожен канал
    у відповіді отримує додаткове поле "role" — для гейтингу на фронтенді."""
    member_roles = _member_roles_for_admin(user_id)
    result = []
    for ch in get_channels():
        if ch.get("added_by") == user_id:
            result.append({**ch, "role": "owner"})
        else:
            role = member_roles.get(ch["id"])
            if role_at_least(role, min_role):
                result.append({**ch, "role": role})
    return result


# ---------- Кастомний водяний знак каналу (бінарний файл — лишається на диску) ----------
WATERMARKS_DIR = os.path.join(BASE_DIR, "watermarks")


def get_channel_watermark_path(channel_id: int) -> str | None:
    path = os.path.join(WATERMARKS_DIR, f"{channel_id}.png")
    return path if os.path.exists(path) else None


def set_channel_watermark(channel_id: int, image_bytes: bytes) -> None:
    os.makedirs(WATERMARKS_DIR, exist_ok=True)
    path = os.path.join(WATERMARKS_DIR, f"{channel_id}.png")
    with open(path, "wb") as f:
        f.write(image_bytes)


def remove_channel_watermark(channel_id: int) -> bool:
    path = os.path.join(WATERMARKS_DIR, f"{channel_id}.png")
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


WATERMARK_POSITIONS = ["center", "top-left", "top-right", "bottom-left", "bottom-right"]


def get_channel_watermark_settings(channel_id: int) -> dict:
    """Прозорість (0.1-1.0), список позицій (мультивибір, п.2.2 ТЗ) і масштаб
    (0.1-0.5 частки ширини фото, п.2.3 ТЗ) — окремо від самого файлу знака, щоб
    можна було міняти без перезавантаження картинки."""
    data = _kv_get("channel_watermark_settings", {}) or {}
    entry = data.get(str(channel_id), {})
    positions = entry.get("positions")
    if positions is None:
        # Міграція зі старого одиничного "position" (до мультивибору) — якщо є
        # старий запис, переносимо його як список з одного елемента.
        positions = [entry["position"]] if entry.get("position") else ["center"]
    return {
        "opacity": entry.get("opacity", 0.5),
        "positions": positions,
        "scale": entry.get("scale", 0.4),
    }


def set_channel_watermark_settings(channel_id: int, opacity: float | None = None,
                                    positions: list | None = None, scale: float | None = None) -> dict:
    data = _kv_get("channel_watermark_settings", {}) or {}
    current = get_channel_watermark_settings(channel_id)  # вже враховує міграцію зі старого формату
    entry = {"opacity": current["opacity"], "positions": current["positions"], "scale": current["scale"]}
    if opacity is not None:
        entry["opacity"] = max(0.1, min(1.0, float(opacity)))
    if positions is not None:
        valid = [p for p in positions if p in WATERMARK_POSITIONS]
        entry["positions"] = valid or ["center"]  # порожній вибір безглуздий — лишаємо хоч центр
    if scale is not None:
        entry["scale"] = max(0.1, min(0.5, float(scale)))
    data[str(channel_id)] = entry
    _kv_set("channel_watermark_settings", data)
    return entry


# ---------- Кеш аватарок каналів (бінарні файли на диску + метадані в kv_store) ----------
CHANNEL_AVATARS_DIR = os.path.join(BASE_DIR, "channel_avatars")
QUEUE_MEDIA_DIR = os.path.join(BASE_DIR, "queue_media")
os.makedirs(QUEUE_MEDIA_DIR, exist_ok=True)


def get_channel_avatar_path(channel_id) -> str | None:
    path = os.path.join(CHANNEL_AVATARS_DIR, f"{channel_id}.jpg")
    return path if os.path.exists(path) else None


def save_channel_avatar(channel_id, image_bytes: bytes) -> None:
    os.makedirs(CHANNEL_AVATARS_DIR, exist_ok=True)
    path = os.path.join(CHANNEL_AVATARS_DIR, f"{channel_id}.jpg")
    with open(path, "wb") as f:
        f.write(image_bytes)


def clear_channel_avatar_cache(channel_id) -> bool:
    path = os.path.join(CHANNEL_AVATARS_DIR, f"{channel_id}.jpg")
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def get_avatar_unique_id(key) -> str | None:
    return (_kv_get("avatar_unique_ids", {}) or {}).get(str(key))


def set_avatar_unique_id(key, unique_id: str) -> None:
    data = _kv_get("avatar_unique_ids", {}) or {}
    data[str(key)] = unique_id
    _kv_set("avatar_unique_ids", data)


# ==================== users: прив'язка читача до каналу ====================

def set_active_channel(user_id: int, channel_id: int, ts: str) -> None:
    data = _kv_get("reader_channel_map", {}) or {}
    data[str(user_id)] = {"active_channel_id": channel_id, "updated_at": ts}
    _kv_set("reader_channel_map", data)


def get_active_channel(user_id: int) -> int | None:
    data = _kv_get("reader_channel_map", {}) or {}
    entry = data.get(str(user_id))
    return entry["active_channel_id"] if entry else None


# ==================== Дедуплікація ====================

def get_seen_news() -> list:
    return _kv_get("seen_news", []) or []


def add_seen_news(link: str) -> None:
    # 300 було замало: тепер Telethon реально тягне 20+ джерел, і за годину-дві
    # список вимивається — старий (але й досі "найновіший" для тихого каналу) пост
    # знову виглядає "непереглянутим" і повторно потрапляє в перевірку свіжості,
    # даючи хибний спам "Пропущено як застарілий" замість того, щоб просто мовчати.
    seen = get_seen_news()
    seen.append(link)
    _kv_set("seen_news", seen[-5000:])


def get_seen_image_hashes(hours: int = 12) -> list:
    items = _kv_get("seen_image_hashes", []) or []
    cutoff = datetime.now() - timedelta(hours=hours)
    fresh = []
    for it in items:
        try:
            if datetime.fromisoformat(it["ts"]) >= cutoff:
                fresh.append(it)
        except Exception:
            continue
    return fresh


def add_seen_image_hash(image_hash: str) -> None:
    if not image_hash:
        return
    items = get_seen_image_hashes()
    items.append({"hash": image_hash, "ts": datetime.now().isoformat()})
    _kv_set("seen_image_hashes", items[-500:])


def get_primed_feeds() -> list:
    return _kv_get("primed_feeds", []) or []


def mark_feed_primed(feed_url: str) -> None:
    primed = get_primed_feeds()
    if feed_url not in primed:
        primed.append(feed_url)
        _kv_set("primed_feeds", primed)


def get_recent_titles() -> list:
    return _kv_get("recent_titles", []) or []


def add_recent_title(title: str) -> None:
    titles = get_recent_titles()
    titles.append(title)
    _kv_set("recent_titles", titles[-150:])


CHANNEL_TITLES_LIMIT = 30
APPROVED_TITLES_LIMIT = 500


def get_approved_titles() -> list:
    return _kv_get("approved_titles", []) or []


def add_approved_title(norm_title: str) -> None:
    if not norm_title:
        return
    titles = get_approved_titles()
    titles.append(norm_title)
    _kv_set("approved_titles", titles[-APPROVED_TITLES_LIMIT:])


def get_channel_recent_titles(channel_id: int) -> list:
    data = _kv_get("channel_titles", {}) or {}
    return data.get(str(channel_id), [])


def add_channel_published_title(channel_id: int, norm_title: str) -> None:
    if not norm_title:
        return
    data = _kv_get("channel_titles", {}) or {}
    titles = data.get(str(channel_id), [])
    titles.append(norm_title)
    data[str(channel_id)] = titles[-CHANNEL_TITLES_LIMIT:]
    _kv_set("channel_titles", data)


def get_channel_queued_titles(channel_id: int) -> list:
    titles = []
    for it in get_queue():
        if it.get("status") not in ("queued", "pending"):
            continue
        if channel_id not in it.get("channel_ids", []):
            continue
        if channel_id in set(it.get("delivered_channel_ids", [])):
            continue
        if it.get("norm_title"):
            titles.append(it["norm_title"])
    return titles


# ==================== Джерела новин ====================

_DEFAULT_SOURCES = [
    {"name": "УНІАН", "type": "rss", "url": "https://rss.unian.net/site/news_ukr.rss", "enabled": True},
    {"name": "Українська правда", "type": "rss", "url": "https://www.pravda.com.ua/rss/", "enabled": True},
    {"name": "РБК-Україна", "type": "rss", "url": "https://www.rbc.ua/static/rss/all.ukr.rss.xml", "enabled": True},
    {"name": "НВ", "type": "rss", "url": "https://nv.ua/rss/all.xml", "enabled": True},
]


def _ensure_default_sources() -> None:
    if not _collection_all("sources"):
        for s in _DEFAULT_SOURCES:
            _collection_insert_autoid("sources", dict(s))


def get_sources() -> list:
    _ensure_default_sources()
    return _collection_all("sources")


def get_sources_for_admin(admin_id: int) -> list:
    return [s for s in get_sources() if s.get("added_by") == admin_id]


def get_sources_for_owner_ids(owner_ids: set) -> list:
    """Джерела зберігаються з added_by = власник каналу (щоб _enqueue_source_news
    у bot.py продовжував матчити added_by джерела == added_by каналу, навіть коли
    джерело фактично додав Editor від імені власника) — тож для показу списку
    Editor'у потрібен пошук по множині "власників, чиї канали йому доступні",
    а не по власному user_id виклику."""
    return [s for s in get_sources() if s.get("added_by") in owner_ids]


def get_source_by_id(source_id: int):
    return _collection_get("sources", source_id)


def is_source_owner(admin_id: int, source_id: int) -> bool:
    s = get_source_by_id(source_id)
    return bool(s) and s.get("added_by") == admin_id


def set_source_category(admin_id: int, source_id: int, category: str) -> bool:
    if category not in ("public_channel", "editorial_chat"):
        return False
    s = get_source_by_id(source_id)
    if not s or s.get("added_by") != admin_id:
        return False
    return _collection_mutate("sources", source_id, lambda x: x.update(category=category)) is not None


def get_active_rss_sources() -> list:
    return [s for s in get_sources() if s.get("enabled", True) and s.get("type", "rss") == "rss"]


def get_active_public_tg_sources() -> list:
    return [s for s in get_sources() if s.get("enabled", True) and s.get("type") == "telegram_public"]


def get_telegram_source_by_chat_id(chat_id: int):
    for s in get_sources():
        if s.get("type") == "telegram" and s.get("chat_id") == chat_id and s.get("enabled", True):
            return s
    return None


def add_source(admin_id: int, name: str, url: str) -> bool:
    for s in get_sources():
        if s.get("added_by") == admin_id and s["name"].lower() == name.lower():
            return False
    item = {
        "name": name, "type": "rss", "url": url, "enabled": True, "added_by": admin_id,
        "category": "public_channel", "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    _collection_insert_autoid("sources", item, added_by=admin_id)
    return True


def add_telegram_source(admin_id: int, name: str, chat_id: int) -> bool:
    for s in get_sources():
        if s.get("type") == "telegram" and s.get("chat_id") == chat_id and s.get("added_by") == admin_id:
            return False
    item = {
        "name": name, "type": "telegram", "chat_id": chat_id, "enabled": True, "added_by": admin_id,
        "category": "editorial_chat", "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    _collection_insert_autoid("sources", item, added_by=admin_id)
    return True


def add_public_telegram_source(admin_id: int, name: str, username: str) -> bool:
    username = username.lstrip("@").strip()
    for s in get_sources():
        if (s.get("type") == "telegram_public" and s.get("username", "").lower() == username.lower()
                and s.get("added_by") == admin_id):
            return False
    item = {
        "name": name, "type": "telegram_public", "username": username, "enabled": True, "added_by": admin_id,
        "category": "public_channel", "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    _collection_insert_autoid("sources", item, added_by=admin_id)
    return True


def edit_source(admin_id: int, source_id: int, name: str | None = None, link: str | None = None) -> bool:
    s = get_source_by_id(source_id)
    if not s or s.get("added_by") != admin_id:
        return False
    if s.get("type") == "telegram" and link is not None:
        return False

    def _mut(x):
        if name is not None and name.strip():
            x["name"] = name.strip()
        if link is not None and link.strip():
            if x.get("type") == "telegram_public":
                x["username"] = link.strip().lstrip("@")
            else:
                x["url"] = link.strip()
    return _collection_mutate("sources", source_id, _mut) is not None


def remove_source(admin_id: int, source_id: int) -> bool:
    s = get_source_by_id(source_id)
    if not s or s.get("added_by") != admin_id:
        return False
    return _collection_delete("sources", source_id)


def set_source_enabled(admin_id: int, source_id: int, enabled: bool) -> bool:
    s = get_source_by_id(source_id)
    if not s or s.get("added_by") != admin_id:
        return False
    return _collection_mutate("sources", source_id, lambda x: x.update(enabled=enabled)) is not None


# ==================== Стиль каналу (футер, водяний знак, зразки постів) ====================

def _styles() -> dict:
    return _kv_get("channel_styles", {}) or {}


def _save_styles(data: dict) -> None:
    _kv_set("channel_styles", data)


def set_channel_footer(channel_id: int, footer_text: str, footer_link: str) -> None:
    data = _styles()
    entry = data.setdefault(str(channel_id), {"footer_text": "", "footer_link": "", "samples": []})
    entry["footer_text"] = footer_text
    entry["footer_link"] = footer_link
    _save_styles(data)


def set_channel_auto_watermark(channel_id: int, enabled: bool) -> None:
    data = _styles()
    entry = data.setdefault(str(channel_id), {"footer_text": "", "footer_link": "", "samples": []})
    entry["auto_watermark"] = bool(enabled)
    _save_styles(data)


def is_channel_auto_watermark_enabled(channel_id: int) -> bool:
    entry = _styles().get(str(channel_id), {})
    return entry.get("auto_watermark", True)


def add_style_sample(channel_id: int, text: str, has_bold_start: bool, has_link: bool) -> None:
    data = _styles()
    entry = data.setdefault(str(channel_id), {"footer_text": "", "footer_link": "", "samples": []})
    entry["samples"].insert(0, {
        "text": text[:200], "has_bold_start": has_bold_start, "has_link": has_link,
        "leading_char": text.strip()[:2] if text.strip() else "",
    })
    entry["samples"] = entry["samples"][:15]
    _save_styles(data)


def get_channel_style(channel_id: int) -> dict:
    entry = _styles().get(str(channel_id), {"footer_text": "", "footer_link": "", "samples": []})
    samples = entry.get("samples", [])
    stats = {"sample_count": len(samples), "top_emoji": None, "bold_start_pct": 0, "link_pct": 0}
    if samples:
        from collections import Counter
        emojis = [s["leading_char"] for s in samples if s["leading_char"] and not s["leading_char"][0].isalnum()]
        if emojis:
            stats["top_emoji"] = Counter(emojis).most_common(1)[0][0]
        stats["bold_start_pct"] = round(100 * sum(1 for s in samples if s["has_bold_start"]) / len(samples))
        stats["link_pct"] = round(100 * sum(1 for s in samples if s["has_link"]) / len(samples))
    return {
        "footer_text": entry.get("footer_text", ""),
        "footer_link": entry.get("footer_link", ""),
        "auto_watermark": entry.get("auto_watermark", True),
        "stats": stats,
    }


# ==================== Папки каналів ====================

# ==================== Моніторинг повітряних тривог (NEPTUN, neptun.in.ua) ====================
# NEPTUN — інформаційний агрегатор, НЕ офіційна система оповіщення (їхні власні умови
# використання API це прямо застерігають) — тому кожне надіслане повідомлення нижче
# в bot.py явно позначене як дані агрегатора, а не офіційний сигнал.

ALERT_THREAT_TYPES = ["uav", "recon", "missile", "ballistic", "kab", "mig31k"]


def get_channel_alert_settings(channel_id: int) -> dict:
    data = _kv_get("channel_alerts", {}) or {}
    entry = data.get(str(channel_id), {})
    return {
        "enabled": entry.get("enabled", False),
        "oblasts": entry.get("oblasts", []),          # список назв областей (як у NEPTUN "oblast"/"name")
        "types": entry.get("types", ALERT_THREAT_TYPES),  # типи загроз з /api/v1/threats для сповіщень про рух
        "notify_siren": entry.get("notify_siren", True),   # офіційна тривога/відбій по області/району
        "notify_threats": entry.get("notify_threats", False),  # конкретні цілі (шахед/ракета/КАБ) з фільтром types
        "show_threat_map": entry.get("show_threat_map", False),  # карта руху цілі (trail з NEPTUN) замість тексту
    }


def set_channel_alert_settings(channel_id: int, **fields) -> dict:
    data = _kv_get("channel_alerts", {}) or {}
    entry = data.get(str(channel_id), {
        "enabled": False, "oblasts": [], "types": ALERT_THREAT_TYPES,
        "notify_siren": True, "notify_threats": False, "show_threat_map": False,
    })
    fields.pop("alert_style", None)  # селектор стилю прибрано (п.2.1 ТЗ) — єдиний формат для всіх
    entry.pop("alert_style", None)
    entry.update({k: v for k, v in fields.items() if v is not None})
    data[str(channel_id)] = entry
    _kv_set("channel_alerts", data)
    return entry


def get_all_channel_alert_settings() -> dict:
    """{channel_id: settings} лише для каналів, де моніторинг увімкнено — щоб не
    ганяти зайве по всіх каналах на кожному тіку планувальника."""
    data = _kv_get("channel_alerts", {}) or {}
    return {int(cid): s for cid, s in data.items() if s.get("enabled")}


def get_known_active_alert_keys() -> set:
    """Ключі (raion/oblast) з /api/v1/alerts, які вже були активні на попередньому
    тіку — щоб надсилати сповіщення лише про ЗМІНУ стану (нова тривога/відбій),
    а не дублювати одне й те саме повідомлення щотіку."""
    return set(_kv_get("alert_known_keys", []) or [])


def set_known_active_alert_keys(keys: set) -> None:
    _kv_set("alert_known_keys", list(keys))


def get_seen_threat_ids() -> list:
    return _kv_get("alert_seen_threat_ids", []) or []


def add_seen_threat_id(threat_id: str) -> None:
    seen = get_seen_threat_ids()
    seen.append(threat_id)
    _kv_set("alert_seen_threat_ids", seen[-500:])


def get_threat_state(threat_id: str) -> dict | None:
    """Останній відомий стан конкретної цілі (локація/кількість/статус) — щоб
    надсилати НАСТУПНІ повідомлення про ту саму ціль лише коли щось РЕАЛЬНО
    змінилось (перемістилась/збили одну з групи/зникла), а не дублювати."""
    return (_kv_get("threat_states", {}) or {}).get(threat_id)


def set_threat_state(threat_id: str, state: dict) -> None:
    data = _kv_get("threat_states", {}) or {}
    data[threat_id] = state
    # Тримаємо лише останні ~300 активних цілей, щоб файл не ріс безмежно
    if len(data) > 300:
        for k in list(data.keys())[:len(data) - 300]:
            data.pop(k, None)
    _kv_set("threat_states", data)


def remove_threat_state(threat_id: str) -> None:
    data = _kv_get("threat_states", {}) or {}
    if data.pop(threat_id, None) is not None:
        _kv_set("threat_states", data)


def get_all_threat_state_ids() -> list:
    return list((_kv_get("threat_states", {}) or {}).keys())


# ==================== Динаміка підписників (п.2 ТЗ: графіки на вкладці «Головна») ====================

def record_member_event(channel_id: int, event_type: str, day: str | None = None) -> None:
    """+1 до лічильника «Подписались»/«Отписались» за конкретний день (п.2.2 ТЗ).
    event_type: "joined" або "left". day — YYYY-MM-DD (за замовчуванням сьогодні,
    UTC — узгоджено з тим, як позначені дати в самому ТЗ)."""
    if day is None:
        day = datetime.utcnow().strftime("%Y-%m-%d")
    data = _kv_get("channel_member_daily", {}) or {}
    ch_key = str(channel_id)
    ch_data = data.get(ch_key, {})
    day_data = ch_data.get(day, {"joined": 0, "left": 0})
    day_data[event_type] = day_data.get(event_type, 0) + 1
    ch_data[day] = day_data
    # Тримаємо тільки останні ~120 днів на канал, щоб kv-запис не ріс безмежно.
    if len(ch_data) > 120:
        for k in sorted(ch_data.keys())[:len(ch_data) - 120]:
            ch_data.pop(k, None)
    data[ch_key] = ch_data
    _kv_set("channel_member_daily", data)


def get_member_daily(channel_id: int, days: int = 30) -> list:
    """Останні `days` днів [{date, joined, left}] для каналу, відсортовано за
    зростанням дати, з нулями для днів без подій — щоб фронтенду не доводилось
    самому "дозаповнювати" пропуски в графіку."""
    data = (_kv_get("channel_member_daily", {}) or {}).get(str(channel_id), {})
    today = datetime.utcnow().date()
    result = []
    for i in range(days - 1, -1, -1):
        day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        day_data = data.get(day, {})
        result.append({"date": day, "joined": day_data.get("joined", 0), "left": day_data.get("left", 0)})
    return result


def record_growth_snapshot(channel_id: int, total: int, day: str | None = None) -> None:
    """Щоденний знімок загальної кількості підписників (для блоку «Ріст /
    Загальна динаміка», п.2.2 ТЗ) — окремо від joined/left, бо загальна
    кількість може змінюватись і з причин поза чистим підписом/відписом
    (напр. видалені/заблоковані акаунти)."""
    if day is None:
        day = datetime.utcnow().strftime("%Y-%m-%d")
    data = _kv_get("channel_growth_snapshots", {}) or {}
    ch_key = str(channel_id)
    ch_data = data.get(ch_key, {})
    ch_data[day] = total
    if len(ch_data) > 120:
        for k in sorted(ch_data.keys())[:len(ch_data) - 120]:
            ch_data.pop(k, None)
    data[ch_key] = ch_data
    _kv_set("channel_growth_snapshots", data)


def get_growth_snapshots(channel_id: int, days: int = 30, current_total: int | None = None) -> list:
    """Останні `days` днів [{date, total}]. Дні без власного знімку заповнюються
    найближчим попереднім відомим значенням (forward-fill) — так графік не
    "провалюється" в нуль для щойно доданого каналу чи в дні простою; якщо
    попередніх знімків взагалі нема, використовується current_total (поточне
    значення з Telegram API), щоб графік не був порожнім із самого початку."""
    data = (_kv_get("channel_growth_snapshots", {}) or {}).get(str(channel_id), {})
    today = datetime.utcnow().date()
    result = []
    last_known = None
    # Шукаємо найсвіжіший знімок ДО початку вікна — щоб forward-fill працював
    # правильно навіть на перший день показаного діапазону.
    window_start = today - timedelta(days=days - 1)
    for d_str, val in sorted(data.items()):
        if d_str < window_start.strftime("%Y-%m-%d"):
            last_known = val
    for i in range(days - 1, -1, -1):
        day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        if day in data:
            last_known = data[day]
        result.append({"date": day, "total": last_known if last_known is not None else current_total})
    return result


def get_channel_folders(admin_id: int) -> list:
    data = _kv_get("channel_folders", {}) or {}
    return data.get(str(admin_id), [])


def add_channel_folder(admin_id: int, name: str) -> bool:
    name = name.strip()
    if not name:
        return False
    data = _kv_get("channel_folders", {}) or {}
    folders = data.setdefault(str(admin_id), [])
    if any(f.lower() == name.lower() for f in folders):
        return False
    folders.append(name)
    _kv_set("channel_folders", data)
    return True


def remove_channel_folder(admin_id: int, name: str) -> bool:
    """Видаляє категорію зі списку папок адміна. Канали, що були в цій категорії,
    НЕ видаляються і нікуди не зникають — просто переїжджають у "Без категорії"
    (те саме, що показує UI для порожнього category), інакше видалення папки
    виглядало б як видалення каналів."""
    name = name.strip()
    if not name:
        return False
    data = _kv_get("channel_folders", {}) or {}
    folders = data.get(str(admin_id), [])
    new_folders = [f for f in folders if f.lower() != name.lower()]
    removed = len(new_folders) != len(folders)
    data[str(admin_id)] = new_folders
    _kv_set("channel_folders", data)

    for ch in get_channels_for_admin(admin_id):
        if (ch.get("category") or "").strip().lower() == name.lower():
            set_channel_category(ch["id"], "")
            removed = True
    return removed


# ==================== Глобальні налаштування (супер-адмін) ====================

def get_setting(key: str, default=None):
    return _kv_get(key, default)


def set_setting(key: str, value) -> None:
    _kv_set(key, value)


def touch_admin_presence(admin_id: int) -> None:
    presence = get_setting("admin_presence", {}) or {}
    presence[str(admin_id)] = datetime.now().isoformat()
    set_setting("admin_presence", presence)


def is_admin_present(admin_id: int, timeout_seconds: int = 90) -> bool:
    """90с (замість інтервалу пінгу 20с) — запас на випадок, якщо браузер притримав
    таймер у фоновій вкладці (Page Visibility throttling)."""
    presence = get_setting("admin_presence", {}) or {}
    last_seen = presence.get(str(admin_id))
    if not last_seen:
        return False
    try:
        elapsed = (datetime.now() - datetime.fromisoformat(last_seen)).total_seconds()
        return elapsed < timeout_seconds
    except Exception:
        return False


# ==================== Блокування одночасного редагування посту ====================
# Проста pessimistic-блокування (не realtime-merge): хто відкрив пост у
# редакторі першим — той і редагує, решта бачать банер "редагує Х" і не можуть
# зберегти. Той самий heartbeat-принцип, що й admin_presence вище — редактор
# шле пінг раз на ~20с, поки модалка відкрита, лок автоматично "згасає" за
# LOCK_TIMEOUT_SECONDS, якщо вкладку закрили без явного релізу (крах, втрата
# мережі) — інакше пост міг би лишитись заблокованим назавжди.

EDIT_LOCK_TIMEOUT_SECONDS = 90  # запас над інтервалом heartbeat (як і в presence)


def _edit_lock_key(kind: str, item_id: int) -> str:
    return f"{kind}:{item_id}"


def acquire_edit_lock(kind: str, item_id: int, admin_id: int, admin_name: str = "") -> dict:
    """Повертає {"ok": True} якщо лок узято (або він уже був наш / протух),
    інакше {"ok": False, "locked_by": {...}} з інфо про поточного власника —
    фронт показує банер і блокує збереження, не саме відкриття."""
    locks = get_setting("edit_locks", {}) or {}
    key = _edit_lock_key(kind, item_id)
    existing = locks.get(key)
    now = datetime.now()

    if existing and existing.get("admin_id") != admin_id:
        try:
            elapsed = (now - datetime.fromisoformat(existing["ts"])).total_seconds()
        except Exception:
            elapsed = EDIT_LOCK_TIMEOUT_SECONDS + 1
        if elapsed < EDIT_LOCK_TIMEOUT_SECONDS:
            return {"ok": False, "locked_by": {
                "admin_id": existing.get("admin_id"),
                "admin_name": existing.get("admin_name") or "",
            }}

    locks[key] = {"admin_id": admin_id, "admin_name": admin_name, "ts": now.isoformat()}
    set_setting("edit_locks", locks)
    return {"ok": True}


def refresh_edit_lock(kind: str, item_id: int, admin_id: int) -> bool:
    """Heartbeat, поки редактор відкритий. False — лок перехоплено кимось
    іншим (протух і хтось встиг зайти раніше) — фронт покаже банер."""
    locks = get_setting("edit_locks", {}) or {}
    key = _edit_lock_key(kind, item_id)
    existing = locks.get(key)
    if not existing or existing.get("admin_id") != admin_id:
        return False
    existing["ts"] = datetime.now().isoformat()
    set_setting("edit_locks", locks)
    return True


def release_edit_lock(kind: str, item_id: int, admin_id: int) -> None:
    locks = get_setting("edit_locks", {}) or {}
    key = _edit_lock_key(kind, item_id)
    if locks.get(key, {}).get("admin_id") == admin_id:
        del locks[key]
        set_setting("edit_locks", locks)


def get_edit_lock(kind: str, item_id: int) -> dict | None:
    """Лише для читання (наприклад, показати банер одразу при відкритті,
    до першого acquire) — не продовжує й не забирає лок."""
    locks = get_setting("edit_locks", {}) or {}
    existing = locks.get(_edit_lock_key(kind, item_id))
    if not existing:
        return None
    try:
        elapsed = (datetime.now() - datetime.fromisoformat(existing["ts"])).total_seconds()
    except Exception:
        return None
    if elapsed >= EDIT_LOCK_TIMEOUT_SECONDS:
        return None
    return existing


# ==================== Web Push підписки (PWA) ====================
# Один адмін може мати кілька підписок одразу (кілька браузерів/пристроїв,
# де він встановив панель як окремий PWA) — тому список на admin_id, а не
# одне значення. Дедуплікація по endpoint (унікальний на підписку в браузері).

def add_push_subscription(admin_id: int, subscription: dict) -> None:
    data = _kv_get("push_subscriptions", {}) or {}
    subs = data.get(str(admin_id), [])
    endpoint = subscription.get("endpoint")
    subs = [s for s in subs if s.get("endpoint") != endpoint]
    subs.append(subscription)
    data[str(admin_id)] = subs
    _kv_set("push_subscriptions", data)


def remove_push_subscription(admin_id: int, endpoint: str) -> None:
    data = _kv_get("push_subscriptions", {}) or {}
    subs = data.get(str(admin_id), [])
    new_subs = [s for s in subs if s.get("endpoint") != endpoint]
    if len(new_subs) != len(subs):
        data[str(admin_id)] = new_subs
        _kv_set("push_subscriptions", data)


def get_push_subscriptions(admin_id: int) -> list:
    data = _kv_get("push_subscriptions", {}) or {}
    return data.get(str(admin_id), [])


# ==================== Автоматизація — персонально для кожного каналу ====================
# Раніше "Автосхвалення новин" і "Автопостинг з черги" були одним перемикачем на
# ВСІ канали адміна одразу. Тепер кожен канал вмикає/вимикає це окремо —
# переїхало з Тех.розділу у вкладку «Головна» модалки самого каналу.

def get_channel_auto_approve(channel_id: int) -> bool:
    data = _kv_get("channel_auto_approve", {}) or {}
    return bool(data.get(str(channel_id), False))


def set_channel_auto_approve(channel_id: int, enabled: bool) -> None:
    data = _kv_get("channel_auto_approve", {}) or {}
    data[str(channel_id)] = bool(enabled)
    _kv_set("channel_auto_approve", data)


def get_channel_autopost_enabled(channel_id: int) -> bool:
    """Фолбек на старий глобальний "autopost_enabled" (якщо колись хтось вимкнув
    автопостинг platform-wide через Тех.розділ) — для каналів, де ще нічого
    персонально не збережено."""
    data = _kv_get("channel_autopost_enabled", {}) or {}
    val = data.get(str(channel_id))
    if val is not None:
        return val
    return get_setting("autopost_enabled", True)


def set_channel_autopost_enabled(channel_id: int, enabled: bool) -> None:
    data = _kv_get("channel_autopost_enabled", {}) or {}
    data[str(channel_id)] = bool(enabled)
    _kv_set("channel_autopost_enabled", data)


def get_channel_pending_queue_count(channel_id: int) -> int:
    """Скільки елементів черги новин ще чекають публікації саме в цей канал."""
    return sum(1 for _, cid in get_pending_queue_targets() if cid == channel_id)


# ==================== Кастомні емодзі (персонально для кожного адміна) ====================
# Адмін вказує short name стікерпаку кастомних емодзі, яким він володіє/має доступ
# (посилання виду t.me/addemoji/<name>) — і саме з нього палітра в редакторі бере
# список іконок для вставки.

def get_custom_emoji_set_name(admin_id: int) -> str | None:
    data = _kv_get("custom_emoji_sets", {}) or {}
    return data.get(str(admin_id))


def set_custom_emoji_set_name(admin_id: int, name: str) -> None:
    data = _kv_get("custom_emoji_sets", {}) or {}
    data[str(admin_id)] = name
    _kv_set("custom_emoji_sets", data)


# ==================== Модерація груп (повністю ІЗОЛЬОВАНО від джерел/каналів) ====================
# Ключова вимога ТЗ (п.А.1): жодна з цих функцій не торкається колекцій
# "channels"/"sources" і не викликається жодною функцією, що будує списки для
# інтерфейсу ("Джерела"/"Новини"/"Тривоги") — group-чат для модерації НІКОЛИ
# не потрапляє в панель керування контентом, лише в цей окремий kv-простір.

def add_moderation_warn(chat_id: int, user_id: int) -> int:
    """Повертає нову кількість попереджень (після інкременту)."""
    data = _kv_get("moderation_warns", {}) or {}
    key = f"{chat_id}:{user_id}"
    count = data.get(key, 0) + 1
    data[key] = count
    _kv_set("moderation_warns", data)
    return count


def get_moderation_warns(chat_id: int, user_id: int) -> int:
    data = _kv_get("moderation_warns", {}) or {}
    return data.get(f"{chat_id}:{user_id}", 0)


def clear_moderation_warns(chat_id: int, user_id: int) -> None:
    data = _kv_get("moderation_warns", {}) or {}
    if data.pop(f"{chat_id}:{user_id}", None) is not None:
        _kv_set("moderation_warns", data)


DEFAULT_WARN_LIMIT = 3
DEFAULT_FLOOD_LIMIT = 5
DEFAULT_FLOOD_WINDOW = 10

_MODERATION_SETTINGS_DEFAULTS = {
    "warn_limit": DEFAULT_WARN_LIMIT,
    "antispam_enabled": False,
    "bad_words": [],
    "flood_limit": DEFAULT_FLOOD_LIMIT,
    "flood_window": DEFAULT_FLOOD_WINDOW,
    "flood_action": "mute",
    "badword_action": "warn",
}


def get_moderation_settings(chat_id: int) -> dict:
    """Налаштування автомодерації для конкретної групи (ліміт попереджень,
    антиспам, список заборонених слів, поріг флуду) — той самий ізольований
    kv-простір, що й moderation_warns, жодного зв'язку з channels/sources."""
    data = _kv_get("moderation_settings", {}) or {}
    settings = dict(_MODERATION_SETTINGS_DEFAULTS)
    settings.update(data.get(str(chat_id), {}))
    return settings


def update_moderation_settings(chat_id: int, **kwargs) -> dict:
    data = _kv_get("moderation_settings", {}) or {}
    current = dict(_MODERATION_SETTINGS_DEFAULTS)
    current.update(data.get(str(chat_id), {}))
    current.update({k: v for k, v in kwargs.items() if v is not None})
    data[str(chat_id)] = current
    _kv_set("moderation_settings", data)
    return current


def add_moderation_log(chat_id: int, entry: dict) -> None:
    """Історія дій модерації (ручних і автоматичних) для команди /modlog.
    Тримаємо лише останні 50 записів на групу, щоб kv-blob не ріс необмежено."""
    data = _kv_get("moderation_log", {}) or {}
    log = data.get(str(chat_id), [])
    log.append(entry)
    data[str(chat_id)] = log[-50:]
    _kv_set("moderation_log", data)


def get_moderation_log(chat_id: int, limit: int = 10) -> list:
    data = _kv_get("moderation_log", {}) or {}
    log = data.get(str(chat_id), [])
    return list(reversed(log[-limit:]))


def is_maintenance_mode() -> bool:
    return bool(get_setting("maintenance_mode", False))


DEFAULT_LANGUAGE = "ua"


def get_admin_language(admin_id: int) -> str:
    data = _kv_get("admin_language", {}) or {}
    return data.get(str(admin_id), DEFAULT_LANGUAGE)


def set_admin_language(admin_id: int, lang: str) -> None:
    if lang not in ("ua", "ru", "en"):
        lang = DEFAULT_LANGUAGE
    data = _kv_get("admin_language", {}) or {}
    data[str(admin_id)] = lang
    _kv_set("admin_language", data)


# ==================== Лог помилок ====================

def log_error(message: str) -> None:
    errors = _kv_get("errors", []) or []
    errors.insert(0, {"message": message, "ts": datetime.now().strftime("%d.%m %H:%M:%S")})
    _kv_set("errors", errors[:100])


def get_errors(limit: int = 50) -> list:
    return (_kv_get("errors", []) or [])[:limit]


# ==================== Статистика та користувачі (супер-адмін) ====================

def get_platform_stats() -> dict:
    channels = get_channels()
    admins = {ch["added_by"] for ch in channels if ch.get("added_by")}
    subs = get_submissions()
    today = datetime.now().strftime("%d.%m")
    subs_today = sum(1 for s in subs if s.get("created_at", "").startswith(today))
    subs_week = len(subs)
    return {
        "channels_count": len(channels),
        "active_admins_count": len(admins),
        "submissions_today": subs_today,
        "submissions_total": subs_week,
    }


def search_users(query: str) -> list:
    query = query.strip().lower()
    results = {}
    for ch in get_channels():
        admin_id = ch.get("added_by")
        if admin_id and (query in str(admin_id)):
            results.setdefault(admin_id, {"user_id": admin_id, "role": "admin", "channels": 0, "submissions": 0})
            results[admin_id]["channels"] += 1
    for s in get_submissions():
        uid = s.get("author_id")
        name = (s.get("author_name") or "").lower()
        if uid and (query in str(uid) or (query and query in name)):
            results.setdefault(uid, {"user_id": uid, "role": "reader", "channels": 0, "submissions": 0,
                                      "name": s.get("author_name")})
            results[uid]["submissions"] += 1
            results[uid]["name"] = s.get("author_name")
    return list(results.values())


# ==================== Предложка от читачів ====================

def add_submission(author_id, author_name, content_type, content, caption, ts, target_channel_id=None,
                    scam_suspected: bool = False) -> dict:
    entry = {
        "author_id": author_id, "author_name": author_name, "type": content_type, "content": content,
        "caption": caption, "status": "new", "created_at": ts, "target_channel_id": target_channel_id,
        "scam_suspected": scam_suspected,
    }
    return _collection_insert_autoid("submissions", entry, status="new")


def get_submissions(status: str | None = None) -> list:
    items = _collection_all("submissions")
    if status:
        return [it for it in items if it.get("status") == status]
    return items


def get_submissions_for_admin(admin_id: int, status: str | None = None) -> list:
    accessible_channel_ids = {ch["id"] for ch in get_channels_with_role_for_admin(admin_id, "moderator")}
    items = get_submissions(status)
    return [it for it in items if it.get("target_channel_id") in accessible_channel_ids]


def set_submission_status(submission_id: int, status: str, decided_by: int | None = None) -> bool:
    def _mut(it):
        it["status"] = status
        if decided_by is not None:
            it["decided_by"] = decided_by
            it["decided_at"] = datetime.now().isoformat()
    return _collection_mutate("submissions", submission_id, _mut) is not None


def approve_submission(submission_id: int, channel_ids: list, decided_by: int | None = None) -> bool:
    def _mut(it):
        it["status"] = "approved"
        it["published_channel_ids"] = channel_ids
        if decided_by is not None:
            it["decided_by"] = decided_by
            it["decided_at"] = datetime.now().isoformat()
    return _collection_mutate("submissions", submission_id, _mut) is not None


def edit_submission(submission_id: int, content: str | None = None, caption: str | None = None) -> bool:
    def _mut(it):
        if content is not None:
            it["content"] = content
        if caption is not None:
            it["caption"] = caption
    return _collection_mutate("submissions", submission_id, _mut) is not None


def remove_album_item(submission_id: int, index: int) -> dict | None:
    result = {}

    def _mut(it):
        if it.get("type") != "album":
            result["skip"] = True
            return
        content = it.get("content") or []
        if index < 0 or index >= len(content) or len(content) <= 1:
            result["skip"] = True
            return
        content.pop(index)
        it["content"] = content

    updated = _collection_mutate("submissions", submission_id, _mut)
    if updated is None or result.get("skip"):
        return None
    return updated


# ==================== Шаблони адміна ====================

def get_templates(admin_id: int) -> list:
    return [t for t in _collection_all("templates") if t["admin_id"] == admin_id]


def add_template(admin_id: int, title: str, text_pattern: str) -> dict:
    entry = {"admin_id": admin_id, "title": title, "text_pattern": text_pattern}
    return _collection_insert_autoid("templates", entry, added_by=admin_id)


def remove_template(template_id: int) -> bool:
    return _collection_delete("templates", template_id)


# ==================== Черга автопостингу новин ====================

QUEUE_TTL_SECONDS = 2 * 60 * 60  # 2 години


def get_queue() -> list:
    return _collection_all("queue")


def get_queue_item(item_id: int):
    return _collection_get("queue", item_id)


def get_queue_for_admin(admin_id: int) -> list:
    accessible_channel_ids = {ch["id"] for ch in get_channels_with_role_for_admin(admin_id, "moderator")}
    return [
        it for it in get_queue()
        if it.get("status") in ("queued", "pending") and set(it.get("channel_ids", [])) & accessible_channel_ids
    ]


def enqueue_news(title: str, text: str, media_paths: list, source_name: str, channel_ids: list, norm_title: str = "", priority: bool = False) -> dict:
    item = {
        "title": title, "text": text, "media_paths": media_paths, "source_name": source_name,
        "channel_ids": channel_ids, "delivered_channel_ids": [], "norm_title": norm_title,
        "status": "pending", "created_at": datetime.now().isoformat(), "published_at": None,
        "skip_watermark": False, "append_footer": True, "priority": priority,
    }
    return _collection_insert_autoid("queue", item, status="pending")


def add_queue_media_item(item_id: int, file_path: str) -> dict | None:
    def _mut(it):
        media_paths = it.get("media_paths") or []
        media_paths.append(file_path)
        it["media_paths"] = media_paths
    return _collection_mutate("queue", item_id, _mut)


def remove_queue_media_item(item_id: int, index: int) -> dict | None:
    result = {}

    def _mut(it):
        media_paths = it.get("media_paths") or []
        if index < 0 or index >= len(media_paths):
            result["skip"] = True
            return
        result["removed_path"] = media_paths.pop(index)
        it["media_paths"] = media_paths

    updated = _collection_mutate("queue", item_id, _mut)
    if updated is None or result.get("skip"):
        return None
    return {"item": updated, "removed_path": result["removed_path"]}


def log_editor_action(admin_id: int, channel_id: int, kind: str, reaction_seconds: float | None = None) -> None:
    """Персистентний лог дій редактора/модератора для дашборду ефективності
    команди (Owner переглядає у вкладці «Команда»). Незалежний від самих
    queue/submissions — ті чистяться по TTL чи змінюють форму після публікації
    і не годяться як довгострокове джерело статистики. kind: "queue_approve" |
    "submission_approve" | "submission_reject". Тримаємо останні 5000 записів —
    з запасом на місяці активності, без необмеженого росту kv-blob."""
    log = _kv_get("editor_actions_log", []) or []
    log.append({
        "admin_id": admin_id, "channel_id": channel_id, "kind": kind,
        "reaction_seconds": reaction_seconds, "ts": datetime.now().isoformat(),
    })
    if len(log) > 5000:
        log = log[-5000:]
    _kv_set("editor_actions_log", log)


def get_editor_stats(channel_id: int) -> list:
    """Агрегована статистика команди ОДНОГО каналу (вкладка «Команда» у його
    модалці) — скільки схвалень/відхилень зробив кожен редактор/модератор і
    середній час реакції (від появи новини в черзі/предложці до рішення
    людини). Права перевіряються на рівні ендпоінта (require_role owner)."""
    log = _kv_get("editor_actions_log", []) or []
    stats = {}
    for entry in log:
        if entry.get("channel_id") != channel_id:
            continue
        aid = entry.get("admin_id")
        if aid is None:
            continue
        s = stats.setdefault(aid, {
            "queue_approved": 0, "submissions_approved": 0, "submissions_rejected": 0, "reaction_seconds": [],
        })
        kind = entry.get("kind")
        if kind == "queue_approve":
            s["queue_approved"] += 1
        elif kind == "submission_approve":
            s["submissions_approved"] += 1
        elif kind == "submission_reject":
            s["submissions_rejected"] += 1
        if entry.get("reaction_seconds") is not None:
            s["reaction_seconds"].append(entry["reaction_seconds"])

    profiles = get_user_profiles(list(stats.keys()))
    result = []
    for aid, s in stats.items():
        reaction_list = s["reaction_seconds"]
        avg_reaction_minutes = round((sum(reaction_list) / len(reaction_list)) / 60, 1) if reaction_list else None
        profile = profiles.get(aid, {})
        result.append({
            "admin_id": aid,
            "name": profile.get("first_name") or f"ID {aid}",
            "username": profile.get("username") or "",
            "queue_approved": s["queue_approved"],
            "submissions_approved": s["submissions_approved"],
            "submissions_rejected": s["submissions_rejected"],
            "avg_reaction_minutes": avg_reaction_minutes,
        })
    result.sort(key=lambda r: r["queue_approved"] + r["submissions_approved"], reverse=True)
    return result


def approve_queue_item(item_id: int, approved_by: int | None = None) -> bool:
    """approved_by — None означає автоматичне схвалення системою (наприклад,
    auto_approve_worker, коли адмін не в панелі) і НЕ враховується в дашборді
    ефективності редакторів (get_editor_stats) — там лише реальні дії людини."""
    result = {}

    def _mut(it):
        if it.get("status") != "pending":
            result["skip"] = True
            return
        it["status"] = "queued"
        it["approved_at"] = datetime.now().isoformat()
        it["approved_by"] = approved_by
        result["norm_title"] = it.get("norm_title")

    updated = _collection_mutate("queue", item_id, _mut)
    if updated is None or result.get("skip"):
        return False
    add_approved_title(result.get("norm_title"))
    return True


def update_queue_item(item_id: int, **fields) -> bool:
    return _collection_mutate("queue", item_id, lambda it: it.update(fields)) is not None


def remove_queue_item(item_id: int):
    item = _collection_get("queue", item_id)
    if item:
        _collection_delete("queue", item_id)
    return item


def mark_channel_delivered(item_id: int, channel_id: int):
    result = {}

    def _mut(it):
        delivered = set(it.get("delivered_channel_ids", []))
        delivered.add(channel_id)
        it["delivered_channel_ids"] = list(delivered)
        fully_done = set(it.get("channel_ids", [])) <= delivered
        if fully_done:
            it["status"] = "published"
            it["published_at"] = datetime.now().isoformat()
        result["fully_done"] = fully_done

    updated = _collection_mutate("queue", item_id, _mut)
    if updated is None:
        return None
    return updated if result.get("fully_done") else None


def get_pending_queue_targets() -> list:
    items = [it for it in get_queue() if it.get("status") == "queued"]
    items.sort(key=lambda it: it["id"])
    pairs = []
    for it in items:
        delivered = set(it.get("delivered_channel_ids", []))
        for cid in it.get("channel_ids", []):
            if cid not in delivered:
                pairs.append((it, cid))
    return pairs


def cleanup_expired_queue_items() -> list:
    now = datetime.now()
    expired = []
    for it in get_queue():
        if it.get("status") in ("queued", "pending"):
            try:
                created = datetime.fromisoformat(it["created_at"])
            except Exception:
                created = now
            if (now - created).total_seconds() > QUEUE_TTL_SECONDS:
                expired.append(it)
    for it in expired:
        _collection_delete("queue", it["id"])
    return expired


# ==================== Незалежний КД для кожного каналу ====================

def get_channel_last_published(channel_id: int) -> str | None:
    data = _kv_get("channel_cooldowns", {}) or {}
    return data.get(str(channel_id))


def get_all_channel_last_published() -> dict:
    return _kv_get("channel_cooldowns", {}) or {}


def set_channel_last_published(channel_id: int, iso_ts: str) -> None:
    data = _kv_get("channel_cooldowns", {}) or {}
    data[str(channel_id)] = iso_ts
    _kv_set("channel_cooldowns", data)


def get_channel_autopost_cd(channel_id: int) -> int:
    """Персональний КД автопостингу новин для каналу, у хвилинах (раніше було
    одне глобальне число на всі канали — тепер кожен канал налаштовує свій,
    у вкладці «Головна» модалки каналу). Якщо для каналу ще нічого не збережено —
    фолбек на старий глобальний "autopost_cd_minutes" (якщо колись був заданий)
    або 15 хв за замовчуванням."""
    data = _kv_get("channel_autopost_cd", {}) or {}
    val = data.get(str(channel_id))
    if val is not None:
        return val
    return get_setting("autopost_cd_minutes", 15)


def set_channel_autopost_cd(channel_id: int, minutes: int) -> None:
    data = _kv_get("channel_autopost_cd", {}) or {}
    data[str(channel_id)] = minutes
    _kv_set("channel_autopost_cd", data)


# ==================== Статистика надісланих тривог (п.1.3/2.1 ТЗ) ====================
# {channel_id: {"YYYY-MM-DD": count}} — компактно, легко порахувати і "сьогодні", і "за місяць".

def log_alert_sent(channel_id: int) -> None:
    data = _kv_get("channel_alert_stats", {}) or {}
    entry = data.setdefault(str(channel_id), {})
    today = datetime.now().strftime("%Y-%m-%d")
    entry[today] = entry.get(today, 0) + 1
    # тримаємо лише останні ~40 днів на канал, щоб не росло безмежно
    if len(entry) > 40:
        for day in sorted(entry.keys())[:len(entry) - 40]:
            entry.pop(day, None)
    _kv_set("channel_alert_stats", data)


def get_channel_alert_stats(channel_id: int) -> dict:
    data = _kv_get("channel_alert_stats", {}) or {}
    entry = data.get(str(channel_id), {})
    today = datetime.now().strftime("%Y-%m-%d")
    month_prefix = datetime.now().strftime("%Y-%m")
    return {
        "today": entry.get(today, 0),
        "month": sum(v for day, v in entry.items() if day.startswith(month_prefix)),
    }


# ==================== Заплановані публікації (POST /api/schedule) ====================

def get_scheduled_posts() -> list:
    return _collection_all("scheduled_posts")


def add_scheduled_post(title: str, publish_at: str, text: str = "", channel_ids: list | None = None) -> dict:
    item = {
        "title": title, "text": text, "channel_ids": channel_ids or [], "publish_at": publish_at,
        "status": "scheduled", "created_at": datetime.now().isoformat(),
    }
    return _collection_insert_autoid("scheduled_posts", item, status="scheduled")


def get_due_scheduled_posts(now_iso: str) -> list:
    return [
        it for it in get_scheduled_posts()
        if it.get("status") == "scheduled" and it.get("publish_at") and it["publish_at"] <= now_iso
    ]


def remove_scheduled_post(item_id: int) -> bool:
    return _collection_delete("scheduled_posts", item_id)
