from pathlib import Path

from conf import COOKIES_DIR

try:
    COOKIES_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass