import sys
from pathlib import Path
from typing import List

from conf import BASE_DIR

SOCIAL_MEDIA_DOUYIN = "douyin"
SOCIAL_MEDIA_TENCENT = "tencent"
SOCIAL_MEDIA_TIKTOK = "tiktok"
SOCIAL_MEDIA_BILIBILI = "bilibili"
SOCIAL_MEDIA_KUAISHOU = "kuaishou"


def get_supported_social_media() -> List[str]:
    return [SOCIAL_MEDIA_DOUYIN, SOCIAL_MEDIA_TENCENT, SOCIAL_MEDIA_TIKTOK, SOCIAL_MEDIA_KUAISHOU]


def get_cli_action() -> List[str]:
    return ["upload", "login", "watch"]


async def set_init_script(context):
    candidates = [
        Path(BASE_DIR) / "utils" / "stealth.min.js",
        Path(__file__).parent / "stealth.min.js",
    ]
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        candidates.extend([
            exe_dir / "utils" / "stealth.min.js",
            exe_dir / "_internal" / "utils" / "stealth.min.js",
            Path(getattr(sys, "_MEIPASS", "")) / "utils" / "stealth.min.js"
        ])

    for p in candidates:
        try:
            if p and p.exists():
                await context.add_init_script(path=str(p))
                return context
        except Exception:
            pass

    return context
