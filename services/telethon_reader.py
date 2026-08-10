"""Reliable Telegram public-channel reader based on Telethon.

Reads real Telegram messages and groups albums by Message.grouped_id, so all
photo/video items are preserved in original order. Configuration comes only
from environment variables:
  TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION
"""
from __future__ import annotations

import asyncio
import logging
import os
from collections import OrderedDict
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto
    from telethon.extensions import html as telethon_html
    TELETHON_AVAILABLE = True
except Exception:
    TELETHON_AVAILABLE = False

_client = None
_client_lock: asyncio.Lock | None = None


def configured() -> bool:
    return bool(
        TELETHON_AVAILABLE
        and os.getenv("TELEGRAM_API_ID")
        and os.getenv("TELEGRAM_API_HASH")
        and os.getenv("TELEGRAM_SESSION")
    )


async def _get_client():
    global _client, _client_lock
    if not configured():
        return None
    if _client_lock is None:
        _client_lock = asyncio.Lock()
    async with _client_lock:
        if _client is None:
            _client = TelegramClient(
                StringSession(os.environ["TELEGRAM_SESSION"]),
                int(os.environ["TELEGRAM_API_ID"]),
                os.environ["TELEGRAM_API_HASH"],
                connection_retries=3,
                request_retries=3,
                auto_reconnect=True,
            )
        if not _client.is_connected():
            await _client.connect()
        if not await _client.is_user_authorized():
            raise RuntimeError("TELEGRAM_SESSION is not authorized as a user account")
        return _client


def _media_kind(msg) -> str | None:
    if isinstance(getattr(msg, "media", None), MessageMediaPhoto):
        return "photo"
    if isinstance(getattr(msg, "media", None), MessageMediaDocument):
        mime = getattr(getattr(msg.media, "document", None), "mime_type", "") or ""
        if mime.startswith("video/") or getattr(msg, "video", None):
            return "video"
        if mime.startswith("image/"):
            return "photo"
    return None


def _message_html(msg) -> str:
    """Renders a message's text with real Telegram formatting (bold/italic/underline/
    strike/links) preserved as HTML, using the same entities Telegram itself sends —
    unlike a plain-text dump, this keeps the source's actual emphasis. Line breaks are
    turned into <br> so downstream HTML-node-based cleanup (title/body split, trailing
    signature stripping in bot.py) can walk it exactly like the t.me/s scraper's DOM."""
    text = getattr(msg, "message", "") or ""
    if not text.strip():
        return ""
    rendered = telethon_html.unparse(text, getattr(msg, "entities", None) or [])
    return rendered.replace("\n", "<br>")


async def fetch_public_channel_posts(username: str, limit: int = 5) -> list[dict]:
    """Return newest logical posts. Albums are one post with up to 10 media items.

    Media is returned as {type, bytes}; this avoids temporary Telegram CDN URLs
    expiring while the item waits in the publication queue.
    """
    client = await _get_client()
    if client is None:
        return []

    username = username.lstrip("@")
    # Fetch extra messages because one logical album may occupy up to 10 messages.
    raw = await client.get_messages(username, limit=max(30, limit * 12))
    raw = sorted(raw, key=lambda m: m.id)  # chronological while grouping

    groups: "OrderedDict[tuple, list]" = OrderedDict()
    for msg in raw:
        if getattr(msg, "action", None):
            continue
        key = ("album", msg.grouped_id) if getattr(msg, "grouped_id", None) else ("single", msg.id)
        groups.setdefault(key, []).append(msg)

    # Downloading media is expensive (real network transfer per photo/video), and the
    # caller only ever uses the newest few logical posts. Walk groups newest-first and
    # stop as soon as we have `limit` of them, so we never download media for the dozens
    # of older messages fetched just to detect album boundaries.
    logical = []
    for (_kind, _gid), messages in reversed(groups.items()):
        if len(logical) >= limit:
            break
        messages.sort(key=lambda m: m.id)
        caption_msg = next((m for m in messages if (getattr(m, "message", None) or "").strip()), messages[0])
        full_html = _message_html(caption_msg)

        media = []
        for msg in messages[:10]:
            kind = _media_kind(msg)
            if not kind:
                continue
            try:
                data = await client.download_media(msg, file=bytes)
            except Exception as exc:
                logger.warning("[TELETHON] Cannot download @%s/%s media: %s", username, msg.id, exc)
                continue
            if data:
                media.append({"type": kind, "bytes": data})

        if not full_html and not media:
            continue
        first = messages[0]
        last = messages[-1]
        logical.append({
            "full_html": full_html,
            "link": f"https://t.me/{username}/{first.id}",
            "media": media,
            "post_id": str(first.id),
            "post_dt": getattr(first, "date", None),
            "grouped_id": getattr(first, "grouped_id", None),
            "message_ids": [m.id for m in messages],
        })
        if len(messages) > 1:
            logger.info(
                "[TELETHON-ALBUM] @%s grouped_id=%s messages=%s media=%s",
                username, getattr(first, "grouped_id", None),
                [m.id for m in messages], len(media),
            )

    return logical
