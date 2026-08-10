"""
Захист від дублювання сповіщень про тривоги/відбої (п.5.5 ТЗ).

Проблема, яку це вирішує: `check_air_alerts` (bot.py) опитує NEPTUN раз на ~10с.
Якщо один тік працює довше за інтервал планувальника (повільна мережа,
багато каналів → багато bot.get_chat всередині цього ж тіку) або сервіс
запущено в кількох процесах, тіки можуть накластись один на одного. Обидва
накладені тіки бачать те саме "старе" відоме состояние (ще не встигло
записатись) — і обидва шлють те саме сповіщення. Звідси й скарга з ТЗ:
"по 4-5 разів поспіль" одне й те саме повідомлення про тривогу/відбій.

Рішення — два незалежні захисти:

1. `tick_lock()` — глобальний lock на ЧАС ВИКОНАННЯ одного тіку моніторингу.
   Якщо попередній тік ще не завершився (лежить лок), новий тік просто
   пропускається (не намагається виконатись поверх старого) — це прибирає
   саму причину накладання.

2. `is_duplicate(chat_id, text)` — точковий страховий дедуп на рівні
   конкретного повідомлення: (chat_id, hash(text)) кладеться в кеш з TTL;
   якщо той самий текст для того самого каналу вже надсилався за останні
   `DEDUP_TTL_SECONDS` — виклик каже "це дублікат", і `_safe_send_alert`
   в bot.py просто не відправляє повторно. Це ловить дублі навіть якщо
   причина не в накладанні тіків (напр. ручний retry, кілька воркерів).

Обидва механізми йдуть через Redis (`REDIS_URL`), якщо він доступний
(саме такий бекенд і вимагає п.5.5 ТЗ: "Cache / Redis lock"). Якщо Redis
недоступний (не піднятий / бібліотека не встановлена) — автоматичний
фолбек на SQLite (через storage.kv_store, вже й так є в проєкті), з тим
самим TTL-семантикою, щоб захист працював навіть без окремого Redis-сервера.
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
DEDUP_TTL_SECONDS = 120  # той самий текст того самого каналу вважаємо дублем протягом 2 хв
TICK_LOCK_TTL_SECONDS = 30  # довше за очікувану тривалість одного тіку check_air_alerts

_redis_client = None
_redis_unavailable = False


def _get_redis():
    """Лінива ініціалізація Redis-клієнта. Якщо `redis` не встановлено або
    сервер недоступний — фіксуємо це один раз і надалі одразу йдемо у фолбек,
    щоб не бити мережу на кожен виклик."""
    global _redis_client, _redis_unavailable
    if _redis_unavailable:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        import redis  # noqa: локальний імпорт — щоб requirements.txt-залежність
        # не була обов'язковою для роботи всього іншого бота, якщо Redis не піднятий.
        client = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis недоступний ({e}) — дедуп сповіщень працює через SQLite-фолбек")
        _redis_unavailable = True
        return None


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


# ==================== SQLite-фолбек (та сама api/database.db, через storage) ====================

def _fallback_set_nx(key: str, ttl_seconds: int) -> bool:
    """Емуляція Redis SET NX EX на kv_store: повертає True, якщо ключ ВСТАНОВЛЕНО
    щойно (тобто раніше його не було або він прострочився), False — якщо він
    вже активний (== "зайнято іншим"/"дублікат")."""
    from data import storage
    now = time.time()
    existing = storage.get_setting(f"dedup:{key}", None)
    if existing is not None and isinstance(existing, (int, float)) and now - existing < ttl_seconds:
        return False
    storage.set_setting(f"dedup:{key}", now)
    return True


def _fallback_delete(key: str) -> None:
    from data import storage
    storage.set_setting(f"dedup:{key}", None)


# ==================== Публічне API ====================

def is_duplicate(chat_id: int, text: str) -> bool:
    """True, якщо таке саме повідомлення для цього каналу вже надсилалось
    протягом останніх DEDUP_TTL_SECONDS. Побічний ефект: якщо це НЕ дублікат,
    одразу позначає (chat_id, text) як надіслані — окремого підтвердження
    не потрібно, виклик є одночасно і перевіркою, і "заявкою" на відправку."""
    key = f"alert:{chat_id}:{_text_hash(text)}"
    client = _get_redis()
    if client is not None:
        try:
            was_set = client.set(key, "1", nx=True, ex=DEDUP_TTL_SECONDS)
            return not bool(was_set)
        except Exception as e:
            logger.warning(f"Redis SET NX помилка ({e}) — переходимо на SQLite-фолбек для цього виклику")
            return not _fallback_set_nx(key, DEDUP_TTL_SECONDS)
    return not _fallback_set_nx(key, DEDUP_TTL_SECONDS)


@contextmanager
def tick_lock(name: str = "air_alerts_tick"):
    """Контекстний менеджер: `with deduplicator.tick_lock() as acquired:` — якщо
    acquired == False, значить попередній тік моніторингу ще виконується
    (лок не звільнено) і поточний виклик має просто вийти, нічого не роблячи,
    щоб не накладатись і не дублювати сповіщення (п.5.5 ТЗ)."""
    key = f"lock:{name}"
    client = _get_redis()
    acquired = False
    used_fallback = False
    try:
        if client is not None:
            try:
                acquired = bool(client.set(key, "1", nx=True, ex=TICK_LOCK_TTL_SECONDS))
            except Exception as e:
                logger.warning(f"Redis lock помилка ({e}) — фолбек на SQLite для {name}")
                used_fallback = True
                acquired = _fallback_set_nx(key, TICK_LOCK_TTL_SECONDS)
        else:
            used_fallback = True
            acquired = _fallback_set_nx(key, TICK_LOCK_TTL_SECONDS)

        if not acquired:
            logger.info(f"{name}: попередній тік ще виконується — пропускаємо цей запуск (анти-дубль, п.5.5 ТЗ)")
        yield acquired
    finally:
        if acquired:
            try:
                if client is not None and not used_fallback:
                    client.delete(key)
                else:
                    _fallback_delete(key)
            except Exception as e:
                logger.warning(f"Не вдалося звільнити лок {name}: {e}")
