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

def _detect_chrome_path() -> str:
    env_p = os.environ.get("LOCAL_CHROME_PATH")
    if env_p and Path(env_p).exists():
        return env_p
    if sys.platform == "win32":
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
        local_app = os.environ.get("LOCALAPPDATA")
        if local_app:
            candidates.append(str(Path(local_app) / "Google" / "Chrome" / "Application" / "chrome.exe"))
            candidates.append(str(Path(local_app) / "Microsoft" / "Edge" / "Application" / "msedge.exe"))
        for cand in candidates:
            if Path(cand).exists():
                return cand
    elif sys.platform == "darwin":
        for cand in [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]:
            if Path(cand).exists():
                return cand
    return ""

def _get_cookies_dir(base_dir: Path) -> Path:
    env_c = os.environ.get("SAU_COOKIES_DIR")
    if env_c and env_c.strip():
        p = Path(env_c.strip()).resolve()
        try:
            p.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        return p
    # 便携模式兼容：如果当前工作目录下有 cookies 或父目录（主程序同级）有 cookies
    cwd_cookies = Path.cwd().resolve() / "cookies"
    if cwd_cookies.exists():
        return cwd_cookies
    if getattr(sys, "frozen", False):
        exe_parent_cookies = Path(sys.executable).parent.parent.resolve() / "cookies"
        if exe_parent_cookies.exists():
            return exe_parent_cookies
    p = base_dir / "cookies"
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p

def _get_data_dir(base_dir: Path) -> Path:
    env_d = os.environ.get("SAU_DATA_DIR")
    if env_d and env_d.strip():
        p = Path(env_d.strip()).resolve()
        try:
            p.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        return p
    cwd_data = Path.cwd().resolve() / "data"
    if cwd_data.exists():
        return cwd_data
    if getattr(sys, "frozen", False):
        exe_parent_data = Path(sys.executable).parent.parent.resolve() / "data"
        if exe_parent_data.exists():
            return exe_parent_data
    p = base_dir / "data"
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p

BASE_DIR = _get_base_dir()
COOKIES_DIR = _get_cookies_dir(BASE_DIR)
DATA_DIR = _get_data_dir(BASE_DIR)
XHS_SERVER = "http://127.0.0.1:11901"  # only used by xhs-related flows
LOCAL_CHROME_PATH = _detect_chrome_path()
LOCAL_CHROME_HEADLESS = True  # default headless behavior for uploader/examples
DEBUG_MODE = True  # default debug behavior
# Optional proxy for the YouTube uploader. Where youtube.com is blocked, direct
# connections time out and the (patchright) chromium does NOT use the system proxy.
# Point this at your local proxy port, e.g. "http://127.0.0.1:7890". None = no proxy.
YT_PROXY = None

