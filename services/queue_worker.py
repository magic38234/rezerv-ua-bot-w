"""
Фонова задача автосхвалення предложок читачів.

Інфраструктура для цього вже існувала в storage.py (touch_admin_presence /
is_admin_present — heartbeat з панелі раз на ~20с), а сам перемикач
автосхвалення тепер персональний для кожного каналу (storage.get_channel_auto_approve
— переїхав з Тех.розділу у вкладку «Головна» модалки каналу).

Правило: якщо в ЦЬОГО КАНАЛУ увімкнено автосхвалення І адмін, що його додав,
зараз НЕ в панелі (>60с без heartbeat — це і є "після закриття застосунку"),
усі "нові" предложки читачів цього каналу автоматично публікуються в нього
(target_channel_id), без підпису каналу (append_footer=False — безпечний
дефолт для автоматики без участі людини).

Публікацію в чергу автопостингу (з per-канальним КД, паузою на FloodWait/429)
чіпати не довелось — вона вже надійно реалізована в bot.py._process_publish_queue;
цей модуль відповідає лише за самі ПРЕДЛОЖКИ читачів (submissions), а не за
чергу спарсених новин (queue).
"""
from __future__ import annotations

import logging

from telegram import InputMediaPhoto, InputMediaVideo

from data import storage

logger = logging.getLogger(__name__)

AUTO_APPROVE_CHECK_INTERVAL_SECONDS = 60
AUTO_APPROVE_IDLE_SECONDS = 60  # "довше N хвилин після закриття" — за замовчуванням 1 хв (п.3.1 ТЗ)


async def _publish_submission(bot, item: dict, channel_id: int) -> None:
    """Той самий набір send_* / sendMediaGroup, що й ручне схвалення в
    app.py:api_submissions_approve — тут без підпису каналу і без
    водяного знаку (для автоматики без участі людини)."""
    content = item.get("content") if item["type"] == "text" else item.get("caption")

    if item["type"] == "text":
        await bot.send_message(chat_id=channel_id, text=item["content"], parse_mode="HTML")
    elif item["type"] == "photo":
        await bot.send_photo(chat_id=channel_id, photo=item["content"], caption=content or None, parse_mode="HTML")
    elif item["type"] == "video":
        await bot.send_video(chat_id=channel_id, video=item["content"], caption=content or None, parse_mode="HTML")
    elif item["type"] == "location":
        lat_str, lon_str = item["content"].split(",")
        await bot.send_location(chat_id=channel_id, latitude=float(lat_str), longitude=float(lon_str))
    elif item["type"] == "album":
        media_list = []
        for i, media_item in enumerate(item["content"]):
            caption_for_this = content if i == 0 else None
            cls = InputMediaVideo if media_item["type"] == "video" else InputMediaPhoto
            media_list.append(cls(media_item["file_id"], caption=caption_for_this, parse_mode="HTML"))
        await bot.send_media_group(chat_id=channel_id, media=media_list)
    else:
        raise ValueError(f"Невідомий тип предложки: {item['type']}")


async def auto_approve_worker(context) -> None:
    """Job для application.job_queue.run_repeating(interval=AUTO_APPROVE_CHECK_INTERVAL_SECONDS)."""
    pending = storage.get_submissions(status="new")
    if not pending:
        return

    channels_by_id = {c["id"]: c for c in storage.get_channels()}

    for item in pending:
        channel_id = item.get("target_channel_id")
        channel = channels_by_id.get(channel_id)
        if not channel:
            continue  # канал видалено — нема куди публікувати, лишаємо адміну розібратись вручну

        admin_id = channel.get("added_by")
        if admin_id is None:
            continue
        if not storage.get_channel_auto_approve(channel_id):
            continue
        if storage.is_admin_present(admin_id, timeout_seconds=AUTO_APPROVE_IDLE_SECONDS):
            continue  # адмін зараз у панелі — не чіпаємо, хай вирішує сам

        try:
            await _publish_submission(context.bot, item, channel_id)
            storage.approve_submission(item["id"], [channel_id])
            logger.info(f"Автосхвалено предложку {item['id']} → канал {channel_id}")
        except Exception as e:
            logger.warning(f"Не вдалося автосхвалити предложку {item['id']}: {e}")
            storage.log_error(f"Автосхвалення предложки {item['id']}: {e}")