"""Тонкий лаунчер, що лишився в корені після переносу коду в core/services/data/ —
щоб команда `python bot.py` (запуск лише бота, без Flask-панелі) продовжувала
працювати без змін. Реальний код тепер у core/bot.py."""
import runpy

if __name__ == "__main__":
    runpy.run_module("core.bot", run_name="__main__")
