from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID = 38351666
API_HASH = "688ede58e6a6024372751971cd7efef1"

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print(client.session.save())