"""Тонкий лаунчер, що лишився в корені після переносу коду в core/services/data/ —
щоб команда `python app.py` (і всі існуючі звички/скрипти) продовжували працювати
без жодних змін. Реальний код тепер у core/app.py."""
import runpy

if __name__ == "__main__":
    runpy.run_module("core.app", run_name="__main__")
