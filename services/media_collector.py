"""
Універсальний буфер для збирання Telegram-медіагруп (альбомів) із серії
окремих апдейтів в один пакет.

## Проблема (з ТЗ)

Telegram НІКОЛИ не надсилає альбом одним апдейтом — кожне фото/відео
приходить ОКРЕМИМ повідомленням з однаковим media_group_id, без гарантії
порядку доставки і без явного маркера "це останній елемент". Щоб зібрати
альбом і переслати його одним пакетом, потрібно: буферизувати частини,
почекати "тишу" певної тривалості (debounce), відсортувати за id, і
відправити не більше 10 елементів за раз.

## Чому тут немає Telethon/Pyrogram

Технічне завдання, за яким писався цей модуль, орієнтувалось на userbot-
парсинг через Telethon/Pyrogram (сканування історії чужого чату під
користувацьким акаунтом). У ЦЬОМУ проєкті бот працює інакше й надійніше:
адміністратор додає бота учасником у канал-джерело (bot.py:
on_forwarded_from_channel), і Telegram САМ надсилає боту channel_post-
апдейт на кожен новий пост каналу — жодного user-акаунту, логіну чи
порушення ToS Telegram не потрібно. Сама проблема буферизації медіагруп
та її розв'язання (debounce + сортування + батчі по 10) — точно та сама,
що описана в ТЗ, просто побудована на python-telegram-bot's
Application.job_queue замість Telethon-івського asyncio.sleep-циклу.

## Використання

Один екземпляр MediaGroupCollector на кожен незалежний потік буферизації
(проєкт використовує ДВА: читацькі предложки в особисті боту, і парсинг
постів з каналів-джерел — див. bot.py). Окремі екземпляри тримають окремі
буфери і окремі debounce-таймери, тож переповнений/завислий буфер одного
потоку ніяк не може зачепити інший.

    collector = MediaGroupCollector(name="reader_submissions", on_ready=_my_callback)

    # на кожен апдейт з media_group_id:
    collector.add(
        job_queue=context.job_queue,
        group_id=msg.media_group_id,
        message_id=msg.message_id,
        kind="photo",              # або "video"
        file_id=msg.photo[-1].file_id,
        caption_html=msg.caption_html,
        context_data={"user_id": user.id, ...},   # довільні дані, що знадобляться в on_ready
    )

    # колбек викликається, коли Telegram перестав присилати нові частини
    # довше DEBOUNCE_SECONDS:
    async def _my_callback(batches, caption_html, context_data, ptb_context):
        # batches — список БАТЧІВ (кожен ≤10 елементів), майже завжди рівно один,
        # бо Telegram сам не дає користувачу зібрати альбом довше 10 в оригіналі;
        # список все одно ОДИН елемент-список, а не список items, саме тому,
        # що довший гіпотетичний альбом ріжеться на кілька окремих відправок.
        for batch in batches:
            for item in batch:               # item.message_id / item.kind / item.file_id
                ...
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

# Тиша такої тривалості = усі частини альбому точно надійшли (п. 2Б.2 ТЗ).
# 3с — свідомо з запасом: приватні повідомлення Telegram зазвичай доставляє
# частинами з інтервалом у десятки-сотні мс, а от channel_post-апдейти з
# каналів-джерел на практиці іноді йдуть з помітно більшими паузами між
# частинами одного альбому (спостережувана поведінка: 1.5с виявилось замало —
# альбом встигав розбитись на кілька окремих публікацій до приходу решти
# частин). 3с — компроміс: помітно довше за типовий розкид доставки, і все
# одно непомітно для читача (публікація в чергу все одно йде не миттєво).
DEBOUNCE_SECONDS = 3.0

# Жорсткий ліміт Telegram на кількість елементів в одній медіагрупі (п. 2В.4 ТЗ).
MAX_ALBUM_SIZE = 10


@dataclass
class AlbumItem:
    message_id: int
    kind: str            # "photo" | "video"
    file_id: str


@dataclass
class _AlbumBucket:
    items: list = field(default_factory=list)
    caption_html: "str | None" = None
    context_data: dict = field(default_factory=dict)


OnReadyCallback = Callable[[list, "str | None", dict, object], Awaitable[None]]


class MediaGroupCollector:
    """Буфер+debounce для ОДНОГО незалежного потоку медіагруп. Не є async-safe
    для конкурентного виклику add() з різних потоків подій одного й того ж
    group_id (у боті це не трапляється — апдейти одного чату обробляються
    послідовно), тож додаткового locking не потрібно."""

    def __init__(self, name: str, on_ready: OnReadyCallback, debounce_seconds: float = DEBOUNCE_SECONDS):
        self._name = name
        self._on_ready = on_ready
        self._debounce_seconds = debounce_seconds
        self._buckets: dict = {}

    def _job_name(self, group_id: str) -> str:
        # Префікс іменем колектора — щоб job_queue.get_jobs_by_name() з двох
        # різних потоків (читачі / джерела) ніколи не перетнулись одне з одним,
        # навіть якщо Telegram колись видасть однаковий media_group_id обом.
        return f"media_group__{self._name}__{group_id}"

    def add(self, job_queue, group_id: str, message_id: int, kind: str, file_id: str,
            caption_html, context_data: dict) -> None:
        """Додає один елемент альбому в буфер і (пере)запускає debounce-таймер.

        п. 2Б.1 ТЗ: КОЖНА нова частина альбому ОНОВЛЮЄ таймер — це справжній
        debounce ("тиша N секунд"), а не фіксована затримка від першої частини.
        Це відрізняється від попередньої реалізації в bot.py (run_once один раз
        при першому елементі) — при повільній чи нерівномірній доставці частин
        стара версія могла фіналізувати альбом ДО того, як прийшли всі частини."""
        bucket = self._buckets.get(group_id)
        if bucket is None:
            bucket = _AlbumBucket(context_data=context_data)
            self._buckets[group_id] = bucket

        bucket.items.append(AlbumItem(message_id=message_id, kind=kind, file_id=file_id))
        if caption_html and not bucket.caption_html:
            bucket.caption_html = caption_html

        logger.info(f"[{self._name}] media_group {group_id}: зібрано {len(bucket.items)} частин(и), таймер скинуто")

        # Знімаємо попередній таймер (якщо є) і ставимо новий — саме це і робить
        # затримку "ковзною" замість фіксованої.
        for job in job_queue.get_jobs_by_name(self._job_name(group_id)):
            job.schedule_removal()
        job_queue.run_once(
            self._finalize, when=self._debounce_seconds,
            data={"group_id": group_id}, name=self._job_name(group_id),
        )

    async def _finalize(self, ptb_context) -> None:
        group_id = ptb_context.job.data["group_id"]
        # Прибираємо з буфера ОДРАЗУ, до будь-якої мережевої роботи — навіть якщо
        # on_ready впаде з винятком, буфер для цього group_id вже не займає
        # пам'ять (п. 2Г.2 ТЗ: захист від memory leak).
        bucket = self._buckets.pop(group_id, None)
        if not bucket or not bucket.items:
            return

        # Сортування за внутрішнім id повідомлення — гарантує початковий порядок
        # файлів, навіть якщо мережа доставила апдейти не по порядку (п. 2В.1 ТЗ).
        ordered = sorted(bucket.items, key=lambda it: it.message_id)

        # Ліміт Telegram — не більше 10 елементів в одній медіагрупі; довший
        # альбом ріжеться на послідовні батчі (п. 2В.4 ТЗ). У цьому проєкті
        # це практично недосяжний кейс (Telegram сам не дає користувачу зібрати
        # оригінальний альбом довше 10), але захист лишається на майбутнє —
        # наприклад, якщо джерело колись стане агрегувати кілька постів в один.
        batches = [ordered[i:i + MAX_ALBUM_SIZE] for i in range(0, len(ordered), MAX_ALBUM_SIZE)]

        logger.info(
            f"[{self._name}] media_group {group_id}: фіналізовано, "
            f"{len(bucket.items)} елемент(ів) у {len(batches)} батч(ах) "
            f"(message_id: {[it.message_id for it in ordered]})"
        )

        try:
            await self._on_ready(batches, bucket.caption_html, bucket.context_data, ptb_context)
        except Exception as e:
            # п. 2Г.1 ТЗ: збій відправки не повинен ронити джобу планувальника —
            # логуємо і йдемо далі, буфер вже прибрано вище.
            logger.warning(f"[{self._name}] Не вдалося фіналізувати медіагрупу {group_id}: {e}")
