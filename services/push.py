"""
Web Push-сповіщення (справжній PWA push, не через самого бота) — для
критичних подій (тривоги, нові елементи черги), коли адмін явно увімкнув
сповіщення у профілі й дав дозвіл браузеру.

## Важливе обмеження (свідомий вибір користувача, не помилка)

Усередині вбудованого WebView самого Telegram push здебільшого НЕ працює
(особливо на iOS) — Service Worker/Push API там ненадійні чи вимкнені за
умовчанням. Реально спрацює лише якщо адмін відкрив ТУ САМУ адресу панелі в
звичайному браузері (Chrome/Edge/Safari), встановив її як PWA ("Додати на
головний екран" / "Встановити застосунок") і дозволив сповіщення. Для решти
(хто заходить лише через кнопку в Telegram) send_push_to_admin просто нічого
не надсилає — тихо й безпечно, без жодних помилок в основному потоці бота.

## Ізоляція

Модуль читає лише свої власні дані (push_subscriptions у storage.py) і
конфігурацію VAPID з середовища. Виклики send_push_to_admin(s) розкидані по
bot.py в точках, де вже й так існують критичні події (тривоги/нові елементи
черги) — сам модуль ніде не вирішує, ЩО вважати критичним.
"""
from __future__ import annotations

import json
import logging
import os

from pywebpush import webpush, WebPushException

from data import storage

logger = logging.getLogger(__name__)

VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY")
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY")
VAPID_CLAIMS_SUB = os.environ.get("VAPID_CLAIMS_SUB", "mailto:admin@example.com")

PUSH_AVAILABLE = bool(VAPID_PRIVATE_KEY and VAPID_PUBLIC_KEY)
if not PUSH_AVAILABLE:
    logger.warning("VAPID_PRIVATE_KEY/VAPID_PUBLIC_KEY не задано — Web Push сповіщення вимкнені (лише лог, не критично).")


def send_push_to_admin(admin_id: int, title: str, body: str, url: str = "/", tag: str = "") -> None:
    """Найкраще зусилля: помилка ОКРЕМОЇ підписки (протухла, браузер закрито
    назавжди) ніколи не повинна зупиняти розсилку решті чи ламати виклик, що
    її ініціював (check_air_alerts/check_news тощо) — тому жодних except-less
    ділянок, усе проковтується з логом."""
    if not PUSH_AVAILABLE or not admin_id:
        return
    try:
        subs = storage.get_push_subscriptions(admin_id)
    except Exception as e:
        logger.warning(f"[PUSH] Не вдалося прочитати підписки адміна {admin_id}: {e}")
        return
    if not subs:
        return

    payload = json.dumps({"title": title, "body": body, "url": url, "tag": tag})
    for sub in subs:
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_CLAIMS_SUB},
            )
        except WebPushException as e:
            status = getattr(e.response, "status_code", None)
            if status in (404, 410):
                # Підписка відкликана/протухла (браузер видалив, PWA видалено) — прибираємо,
                # інакше кожна наступна тривога намарно ретраїла б той самий мертвий endpoint.
                storage.remove_push_subscription(admin_id, sub.get("endpoint", ""))
            else:
                logger.warning(f"[PUSH] Не вдалося надіслати push адміну {admin_id}: {e}")
        except Exception as e:
            logger.warning(f"[PUSH] Несподівана помилка відправки push адміну {admin_id}: {e}")


def send_push_to_admins(admin_ids, title: str, body: str, url: str = "/", tag: str = "") -> None:
    for admin_id in set(admin_ids):
        send_push_to_admin(admin_id, title, body, url, tag)
