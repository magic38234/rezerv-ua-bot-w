import json
import os
import sqlite3
import threading

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # data/ -> корінь проекту
DB_DIR = os.path.join(PROJECT_ROOT, "api")
DB_PATH = os.path.join(DB_DIR, "database.db")

_local = threading.local()
_init_lock = threading.Lock()
_initialized = False

# Колекції (списки записів з власним id). Для "channels" id — це реальний Telegram
# chat_id (задається явно при вставці), для решти — AUTOINCREMENT самої БД.
COLLECTIONS = ["channels", "sources", "queue", "submissions", "templates", "scheduled_posts"]

# Старі JSON-файли колекцій -> (назва таблиці,) для одноразової міграції
_LEGACY_COLLECTION_FILES = {
    "channels.json": "channels",
    "sources.json": "sources",
    "news_queue.json": "queue",
    "submissions.json": "submissions",
    "admin_templates.json": "templates",
    "scheduled_posts.json": "scheduled_posts",
}

# Старі JSON-файли одиночних значень (dict/list) -> ключ у kv_store
_LEGACY_KV_FILES = {
    "reader_channel_map.json": "reader_channel_map",
    "seen_news.json": "seen_news",
    "seen_image_hashes.json": "seen_image_hashes",
    "primed_feeds.json": "primed_feeds",
    "recent_titles.json": "recent_titles",
    "channel_published_titles.json": "channel_titles",
    "approved_titles.json": "approved_titles",
    "channel_styles.json": "channel_styles",
    "channel_folders.json": "channel_folders",
    "channel_cooldowns.json": "channel_cooldowns",
    "admin_language.json": "admin_language",
    "error_log.json": "errors",
}
# system_settings.json — особливий випадок: кожен ключ верхнього рівня стає ОКРЕМИМ
# записом kv_store (а не одним великим блобом) — так get_setting/set_setting
# лишаються простими точковими SQL-запитами.
_SETTINGS_FILE = "system_settings.json"


def get_connection() -> sqlite3.Connection:
    """Одне з'єднання на потік (Flask-потоки + окремий потік бота-планувальника).
    WAL-режим + busy_timeout дають реальну потокобезпеку і безпеку між процесами
    (SQLite сам серіалізує запис на рівні файлу) — на відміну від Python
    threading.Lock, який захищав лише в межах ОДНОГО процесу."""
    if not hasattr(_local, "conn"):
        os.makedirs(DB_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return _local.conn


def init_db() -> None:
    """п.1 ТЗ: створює api/ і api/database.db (якщо їх нема), ініціалізує ВСІ таблиці
    й одноразово переносить дані з усіх старих JSON-файлів у БД. Ідемпотентно —
    безпечно викликати на кожному старті сервера, реальна міграція відбувається
    лише один раз (перевіряється по кожній таблиці/ключу окремо)."""
    global _initialized
    with _init_lock:
        if _initialized:
            return
        os.makedirs(DB_DIR, exist_ok=True)
        conn = get_connection()
        with conn:
            for table in COLLECTIONS:
                conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        added_by INTEGER,
                        status TEXT,
                        data TEXT NOT NULL
                    )
                """)
                conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_added_by ON {table}(added_by)")
                conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_status ON {table}(status)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kv_store (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            # Роль Owner ніде не зберігається окремо — вона завжди виводиться з
            # channels.added_by. Тут лежать тільки Editor/Moderator, додані власником.
            conn.execute("""
                CREATE TABLE IF NOT EXISTS channel_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('editor', 'moderator')),
                    added_by INTEGER,
                    added_at TEXT NOT NULL,
                    UNIQUE(channel_id, user_id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_channel_members_channel_id ON channel_members(channel_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_channel_members_user_id ON channel_members(user_id)")
        _migrate_legacy_json(conn)
        _initialized = True


def _find_legacy_file(filename: str) -> str | None:
    """Старі JSON-файли теоретично можуть лежати як поряд зі storage.py (як було
    спочатку), так і вже всередині api/ (якщо хтось вручну переніс їх туди) —
    перевіряємо обидва місця, а не тільки одне."""
    for candidate in (os.path.join(PROJECT_ROOT, filename), os.path.join(DB_DIR, filename)):
        if os.path.exists(candidate):
            return candidate
    return None


def _migrate_legacy_json(conn: sqlite3.Connection) -> None:
    for filename, table in _LEGACY_COLLECTION_FILES.items():
        path = _find_legacy_file(filename)
        if not path:
            continue
        already = conn.execute(f"SELECT COUNT(*) c FROM {table}").fetchone()["c"]
        if already:
            continue  # вже мігровано (або дані вже з'явились іншим шляхом) — не затираємо
        try:
            with open(path, "r", encoding="utf-8") as f:
                items = json.load(f)
        except Exception:
            continue
        if not items:
            continue
        seen_ids = set()
        for item in items:
            item_id = item.get("id")
            # Захист від биту в старих JSON-файлах: дублікати id чи None — переприсвоюємо
            # id автоматично (AUTOINCREMENT), замість того щоб валити всю міграцію.
            use_explicit_id = item_id is not None and item_id not in seen_ids
            try:
                with conn:
                    if use_explicit_id:
                        conn.execute(
                            f"INSERT INTO {table} (id, added_by, status, data) VALUES (?,?,?,?)",
                            (item_id, item.get("added_by"), item.get("status"), json.dumps(item, ensure_ascii=False)),
                        )
                        seen_ids.add(item_id)
                    else:
                        cur = conn.execute(
                            f"INSERT INTO {table} (added_by, status, data) VALUES (?,?,?)",
                            (item.get("added_by"), item.get("status"), json.dumps(item, ensure_ascii=False)),
                        )
                        new_id = cur.lastrowid
                        item = {**item, "id": new_id}
                        conn.execute(f"UPDATE {table} SET data=? WHERE id=?", (json.dumps(item, ensure_ascii=False), new_id))
                        seen_ids.add(new_id)
            except sqlite3.IntegrityError:
                # id зайнятий (дублікат у вихідному JSON) — вставляємо той самий запис
                # ще раз, але вже без явного id, щоб дані не загубились.
                with conn:
                    cur = conn.execute(
                        f"INSERT INTO {table} (added_by, status, data) VALUES (?,?,?)",
                        (item.get("added_by"), item.get("status"), json.dumps(item, ensure_ascii=False)),
                    )
                    new_id = cur.lastrowid
                    item = {**item, "id": new_id}
                    conn.execute(f"UPDATE {table} SET data=? WHERE id=?", (json.dumps(item, ensure_ascii=False), new_id))
                    seen_ids.add(new_id)

    for filename, kv_key in _LEGACY_KV_FILES.items():
        path = _find_legacy_file(filename)
        if not path:
            continue
        row = conn.execute("SELECT 1 FROM kv_store WHERE key=?", (kv_key,)).fetchone()
        if row:
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = json.load(f)
        except Exception:
            continue
        with conn:
            conn.execute("INSERT INTO kv_store (key, value) VALUES (?,?)", (kv_key, json.dumps(content, ensure_ascii=False)))

    settings_path = _find_legacy_file(_SETTINGS_FILE)
    if settings_path:
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except Exception:
            settings = {}
        for key, value in (settings or {}).items():
            row = conn.execute("SELECT 1 FROM kv_store WHERE key=?", (key,)).fetchone()
            if row:
                continue
            with conn:
                conn.execute("INSERT INTO kv_store (key, value) VALUES (?,?)", (key, json.dumps(value, ensure_ascii=False)))
