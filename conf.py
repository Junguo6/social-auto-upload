import os
import sys
from pathlib import Path

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        # 优先使用当前工作目录（如果其包含 conf.py 或 uploader 目录）
        cwd = Path.cwd().resolve()
        if (cwd / "conf.py").exists() or (cwd / "uploader").exists():
            return cwd
        # 否则寻找可执行文件所在目录或其上级目录
        exe_dir = Path(sys.executable).parent.resolve()
        if (exe_dir / "conf.py").exists() or (exe_dir / "uploader").exists():
            return exe_dir
        if (exe_dir.parent / "conf.py").exists() or (exe_dir.parent / "uploader").exists():
            return exe_dir.parent.resolve()
        if (exe_dir.parent.parent / "conf.py").exists() or (exe_dir.parent.parent / "uploader").exists():
            return exe_dir.parent.parent.resolve()
        return exe_dir
    return Path(__file__).parent.resolve()

BASE_DIR = _get_base_dir()
XHS_SERVER = "http://127.0.0.1:11901"  # only used by xhs-related flows
LOCAL_CHROME_PATH = ""  # optional, e.g. C:/Program Files/Google/Chrome/Application/chrome.exe
LOCAL_CHROME_HEADLESS = True  # default headless behavior for uploader/examples
DEBUG_MODE = True  # default debug behavior
# Optional proxy for the YouTube uploader. Where youtube.com is blocked, direct
# connections time out and the (patchright) chromium does NOT use the system proxy.
# Point this at your local proxy port, e.g. "http://127.0.0.1:7890". None = no proxy.
YT_PROXY = None
