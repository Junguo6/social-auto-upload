from __future__ import annotations

import os
import sys
import tempfile
import traceback
from pathlib import Path

def _global_unhandled_exception_handler(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    err_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    sys.stderr.write(f"\n[CRITICAL_UNHANDLED_EXCEPTION]\n{err_str}\n")
    sys.stderr.flush()
    try:
        log_file = Path(tempfile.gettempdir()) / "sau_engine_boot.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n[{sys.platform}] Command: {sys.argv}\n{err_str}\n")
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = _global_unhandled_exception_handler

def _resolve_default_browsers_path() -> str:
    # 0. 优先尊重外部已显式指定的环境变量
    custom_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if custom_path and Path(custom_path).exists():
        return custom_path

    # 1. 优先探测当前程序目录或安装包内置的绿色浏览器目录 (开箱即用，0 外部依赖)
    candidate_bundled_dirs = [
        Path.cwd() / "ms-playwright",
        Path.cwd() / "bin" / "ms-playwright",
        Path(__file__).parent / "ms-playwright",
        Path(__file__).parent / "bin" / "ms-playwright",
        Path(__file__).parent / "sau_desktop" / "bin" / "ms-playwright",
    ]
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        candidate_bundled_dirs.extend([
            exe_dir / "ms-playwright",
            exe_dir.parent / "Resources" / "ms-playwright",  # macOS .app/Contents/Resources
            exe_dir / "_internal" / "ms-playwright",
            exe_dir.parent / "ms-playwright",
        ])

    for b_dir in candidate_bundled_dirs:
        try:
            if b_dir.exists() and any(b_dir.glob("chromium*")):
                return str(b_dir.resolve())
        except Exception:
            pass

    # 2. 回退到用户系统的标准缓存目录 (~/Library/Caches/ms-playwright 或 %LOCALAPPDATA%/ms-playwright)
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Caches")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return str(Path(base) / "ms-playwright")


os.environ["PLAYWRIGHT_BROWSERS_PATH"] = _resolve_default_browsers_path()

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

from conf import BASE_DIR
DOUYIN_PUBLISH_STRATEGY_IMMEDIATE = "immediate"
DOUYIN_PUBLISH_STRATEGY_SCHEDULED = "scheduled"
KUAISHOU_PUBLISH_STRATEGY_IMMEDIATE = "immediate"
KUAISHOU_PUBLISH_STRATEGY_SCHEDULED = "scheduled"
TENCENT_PUBLISH_STRATEGY_IMMEDIATE = "immediate"
TENCENT_PUBLISH_STRATEGY_SCHEDULED = "scheduled"
XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE = "immediate"
XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED = "scheduled"

try:
    from uploader.baijiahao_uploader.main import (
        BaiJiaHaoVideo,
        baijiahao_setup,
        cookie_auth as baijiahao_cookie_auth,
    )
except Exception as _e:
    baijiahao_setup = baijiahao_cookie_auth = BaiJiaHaoVideo = None

try:
    from uploader.alipay_uploader.main import (
        AlipayVideo,
        alipay_setup,
        cookie_auth as alipay_cookie_auth,
    )
except Exception as _e:
    alipay_setup = alipay_cookie_auth = AlipayVideo = None

try:
    from uploader.bilibili_uploader.runtime import run_biliup_command
except Exception as _e:
    run_biliup_command = None

try:
    from uploader.douyin_uploader.main import (
        DouYinNote,
        DouYinVideo,
        cookie_auth as douyin_cookie_auth,
        douyin_setup,
    )
except Exception as _e:
    douyin_setup = douyin_cookie_auth = DouYinVideo = DouYinNote = None

try:
    from uploader.ks_uploader.main import (
        KSNote,
        KSVideo,
        cookie_auth as kuaishou_cookie_auth,
        ks_setup,
    )
except Exception as _e:
    ks_setup = kuaishou_cookie_auth = KSVideo = KSNote = None

try:
    from uploader.tencent_uploader.main import (
        TencentVideo,
        cookie_auth as tencent_cookie_auth,
        tencent_setup,
    )
except Exception as _e:
    tencent_setup = tencent_cookie_auth = TencentVideo = None

try:
    from uploader.weibo_uploader.main import (
        WeiBoVideo,
        weibo_setup,
        cookie_auth as weibo_cookie_auth,
    )
except Exception as _e:
    weibo_setup = weibo_cookie_auth = WeiBoVideo = None

try:
    from uploader.hupu_uploader.main import (
        HuPuVideo,
        hupu_setup,
        cookie_auth as hupu_cookie_auth,
    )
except Exception as _e:
    hupu_setup = hupu_cookie_auth = HuPuVideo = None

try:
    from uploader.xiaohongshu_uploader.main import (
        XiaoHongShuNote,
        XiaoHongShuVideo,
        cookie_auth as xiaohongshu_cookie_auth,
        xiaohongshu_setup,
    )
except Exception as _e:
    xiaohongshu_setup = xiaohongshu_cookie_auth = XiaoHongShuVideo = XiaoHongShuNote = None

try:
    from uploader.youtube_uploader.main import (
        YouTubeVideo,
        cookie_auth as youtube_cookie_auth,
        youtube_setup,
    )
except Exception as _e:
    youtube_setup = youtube_cookie_auth = YouTubeVideo = None

SCHEDULE_FORMAT = "%Y-%m-%d %H:%M"


@dataclass(slots=True)
class DouyinVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tags: list[str]
    publish_date: datetime | int
    thumbnail_file: Path | None = None
    thumbnail_landscape_file: Path | None = None
    thumbnail_portrait_file: Path | None = None
    product_link: str = ""
    product_title: str = ""
    publish_strategy: str = DOUYIN_PUBLISH_STRATEGY_IMMEDIATE
    debug: bool = True
    headless: bool = True
    declaration: str | None = None
    collection_name: str | None = None


@dataclass(slots=True)
class DouyinNoteUploadRequest:
    account_name: str
    image_files: list[Path]
    title: str
    note: str
    tags: list[str]
    publish_date: datetime | int
    publish_strategy: str = DOUYIN_PUBLISH_STRATEGY_IMMEDIATE
    debug: bool = True
    headless: bool = True
    bgm: str = ""


@dataclass(slots=True)
class KuaishouVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tags: list[str]
    publish_date: datetime | int
    thumbnail_file: Path | None = None
    publish_strategy: str = KUAISHOU_PUBLISH_STRATEGY_IMMEDIATE
    debug: bool = True
    headless: bool = True
    collection_name: str | None = None


@dataclass(slots=True)
class KuaishouNoteUploadRequest:
    account_name: str
    image_files: list[Path]
    title: str
    note: str
    tags: list[str]
    publish_date: datetime | int
    publish_strategy: str = KUAISHOU_PUBLISH_STRATEGY_IMMEDIATE
    debug: bool = True
    headless: bool = True


@dataclass(slots=True)
class XiaohongshuVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tags: list[str]
    publish_date: datetime | int
    thumbnail_file: Path | None = None
    publish_strategy: str = XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE
    debug: bool = True
    headless: bool = True


@dataclass(slots=True)
class XiaohongshuNoteUploadRequest:
    account_name: str
    image_files: list[Path]
    title: str
    note: str
    tags: list[str]
    publish_date: datetime | int
    publish_strategy: str = XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE
    debug: bool = True
    headless: bool = True


@dataclass(slots=True)
class BilibiliVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tid: int
    tags: list[str]
    publish_date: datetime | int
    thumbnail_file: Path | None = None


@dataclass(slots=True)
class TencentVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tags: list[str]
    publish_date: datetime | int
    thumbnail_file: Path | None = None
    thumbnail_landscape_file: Path | None = None
    thumbnail_portrait_file: Path | None = None
    short_title: str | None = None
    category: str | None = None
    is_draft: bool = False
    publish_strategy: str = TENCENT_PUBLISH_STRATEGY_IMMEDIATE
    debug: bool = True
    headless: bool = True
    collection_name: str | None = None


@dataclass(slots=True)
class BaijiahaoVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tags: list[str]
    thumbnail_file: Path | None = None
    collection_name: str | None = None
    debug: bool = True
    headless: bool = True


@dataclass(slots=True)
class AlipayVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tags: list[str]
    thumbnail_file: Path | None = None
    collection_name: str | None = None
    debug: bool = True
    headless: bool = True


@dataclass(slots=True)
class WeiboVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tags: list[str]
    thumbnail_file: Path | None = None
    collection_name: str | None = None
    debug: bool = True
    headless: bool = True


@dataclass(slots=True)
class HupuVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tags: list[str]
    thumbnail_file: Path | None = None
    debug: bool = True
    headless: bool = True


@dataclass(slots=True)
class YouTubeVideoUploadRequest:
    account_name: str
    video_file: Path
    title: str
    description: str
    tags: list[str]
    thumbnail_file: Path | None = None
    playlist: str | None = None
    visibility: str = "public"
    debug: bool = True
    headless: bool = False


def has_interactive_terminal() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def resolve_runtime_home() -> Path:
    return Path(BASE_DIR)


def resolve_account_file(platform: str, account_name: str) -> Path:
    base_cookies = resolve_runtime_home() / "cookies"
    base_cookies.mkdir(parents=True, exist_ok=True)
    target = base_cookies / f"{platform}_{account_name}.json"
    if target.exists():
        return target

    # 尝试当前工作目录或执行文件同级的 cookies
    for cand_dir in [Path.cwd() / "cookies", Path(sys.executable).parent / "cookies"]:
        try:
            cand_target = cand_dir / f"{platform}_{account_name}.json"
            if cand_target.exists():
                return cand_target
        except Exception:
            pass

    return target


def parse_tags(raw_tags: str | None) -> list[str]:
    if not raw_tags:
        return []

    tags: list[str] = []
    for item in raw_tags.split(","):
        cleaned = item.strip().lstrip("#")
        if cleaned:
            tags.append(cleaned)
    return tags


def parse_image_files(raw_files: Iterable[Path]) -> list[Path]:
    return [Path(file) for file in raw_files]


def parse_schedule(raw_schedule: str | None) -> datetime | int:
    if not raw_schedule:
        return 0
    return datetime.strptime(raw_schedule, SCHEDULE_FORMAT)


def _validate_cookie_file(account_file_path: str) -> bool:
    """轻量级 cookie 文件验证（不启动浏览器）。
    检查：文件存在 + JSON 合法 + 至少含 cookies 条目。
    用于 Playwright 浏览器不可用或被反爬拦截时的可靠降级方案（如 Windows 打包环境）。
    """
    import json as _json
    try:
        fp = Path(account_file_path)
        if not fp.exists():
            # 容错：如果指定文件名不存在，尝试在同级 cookies 目录匹配该平台的最新凭证
            cookies_dir = fp.parent
            if cookies_dir.exists():
                platform_prefix = fp.stem.split("_")[0] + "_"
                matches = list(cookies_dir.glob(f"{platform_prefix}*.json"))
                if matches:
                    fp = sorted(matches, key=lambda p: p.stat().st_mtime, reverse=True)[0]

        if not fp.exists() or fp.stat().st_size < 10:
            return False
        with open(fp, "r", encoding="utf-8") as f:
            data = _json.load(f)
        # Playwright storage state 必须含 cookies 列表
        cookies = data.get("cookies", [])
        if not isinstance(cookies, list) or len(cookies) == 0:
            return False
        return True
    except Exception:
        return False


async def _safe_check(browser_check_coro, account_file_path: str) -> bool:
    """安全 check 包装器：优先用浏览器验证；若浏览器验证未通过或异常（如 Windows 无头反爬拦截/驱动缺失），自动降级为本地凭证文件校验。"""
    try:
        if await browser_check_coro:
            return True
    except Exception:
        pass
    # 降级：检查本地已存盘的凭证有效性
    return _validate_cookie_file(account_file_path)


async def login_douyin_account(account_name: str, headless: bool = True) -> dict:
    account_file = resolve_account_file("douyin", account_name)
    return await douyin_setup(str(account_file), handle=True, return_detail=True, headless=headless)


async def check_douyin_account(account_name: str) -> bool:
    account_file = resolve_account_file("douyin", account_name)
    if not account_file.exists():
        return False
    return await _safe_check(douyin_cookie_auth(str(account_file)), str(account_file))



async def login_kuaishou_account(account_name: str, headless: bool = True) -> dict:
    account_file = resolve_account_file("kuaishou", account_name)
    return await ks_setup(str(account_file), handle=True, return_detail=True, headless=headless)


async def check_kuaishou_account(account_name: str) -> bool:
    account_file = resolve_account_file("kuaishou", account_name)
    if not account_file.exists():
        return False
    return await _safe_check(kuaishou_cookie_auth(str(account_file)), str(account_file))


async def login_xiaohongshu_account(account_name: str, headless: bool = True) -> dict:
    account_file = resolve_account_file("xiaohongshu", account_name)
    return await xiaohongshu_setup(str(account_file), handle=True, return_detail=True, headless=headless)


async def check_xiaohongshu_account(account_name: str) -> bool:
    account_file = resolve_account_file("xiaohongshu", account_name)
    if not account_file.exists():
        return False
    return await _safe_check(xiaohongshu_cookie_auth(str(account_file)), str(account_file))


async def login_bilibili_account(account_name: str) -> dict:
    account_file = resolve_account_file("bilibili", account_name)
    if not has_interactive_terminal():
        return {
            "success": False,
            "message": (
                "Bilibili login requires a local interactive terminal. "
                f"Please run `sau bilibili login --account {account_name}` yourself in a local terminal. "
                "If the terminal QR code does not render completely, open `./qrcode.png` and scan that image."
            ),
            "account_file": str(account_file),
        }

    result = run_biliup_command(["-u", str(account_file), "login"], interactive=True)
    success = result.returncode == 0
    return {
        "success": success,
        "message": (result.stderr or result.stdout or "").strip() or "Bilibili login completed" if success else (result.stderr or result.stdout or "").strip() or "Bilibili login failed",
        "account_file": str(account_file),
    }


async def check_bilibili_account(account_name: str) -> bool:
    account_file = resolve_account_file("bilibili", account_name)
    if not account_file.exists():
        return False
    result = run_biliup_command(["-u", str(account_file), "renew"])
    return result.returncode == 0


async def login_tencent_account(account_name: str, headless: bool = True) -> dict:
    account_file = resolve_account_file("tencent", account_name)
    return await tencent_setup(str(account_file), handle=True, return_detail=True, headless=headless)


async def check_tencent_account(account_name: str) -> bool:
    account_file = resolve_account_file("tencent", account_name)
    if not account_file.exists():
        return False
    return await _safe_check(tencent_cookie_auth(str(account_file)), str(account_file))


async def login_youtube_account(account_name: str, headless: bool = False) -> dict:
    account_file = resolve_account_file("youtube", account_name)
    return await youtube_setup(str(account_file), handle=True, return_detail=True, headless=headless)


async def check_youtube_account(account_name: str) -> bool:
    account_file = resolve_account_file("youtube", account_name)
    if not account_file.exists():
        return False
    return await _safe_check(youtube_cookie_auth(str(account_file)), str(account_file))


async def upload_youtube_video(request: YouTubeVideoUploadRequest) -> Path:
    account_file = resolve_account_file("youtube", request.account_name)
    is_ready = await youtube_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"YouTube cookie is missing or expired: {account_file}. Run `sau youtube login --account {request.account_name}` first."
        )

    app = YouTubeVideo(
        request.title,
        str(request.video_file),
        request.tags,
        str(account_file),
        description=request.description,
        thumbnail_path=str(request.thumbnail_file) if request.thumbnail_file else None,
        playlist=request.playlist,
        visibility=request.visibility,
        debug=request.debug,
        headless=request.headless,
    )
    await app.main()
    return account_file


async def upload_video(request: DouyinVideoUploadRequest) -> Path:
    account_file = resolve_account_file("douyin", request.account_name)
    is_ready = await douyin_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Douyin cookie is missing or expired: {account_file}. Run `sau douyin login --account {request.account_name}` first."
        )

    app = DouYinVideo(
        request.title,
        str(request.video_file),
        request.tags,
        request.publish_date,
        str(account_file),
        desc=request.description,
        thumbnail_landscape_path=(
            str(request.thumbnail_landscape_file) if request.thumbnail_landscape_file else None
        ),
        thumbnail_portrait_path=str(
            request.thumbnail_portrait_file or request.thumbnail_file
        ) if request.thumbnail_portrait_file or request.thumbnail_file else None,
        productLink=request.product_link,
        productTitle=request.product_title,
        declaration=request.declaration,
        publish_strategy=request.publish_strategy,
        debug=request.debug,
        headless=request.headless,
        collection_name=request.collection_name,
    )
    await app.douyin_upload_video()
    return account_file


async def upload_note(request: DouyinNoteUploadRequest) -> Path:
    account_file = resolve_account_file("douyin", request.account_name)
    is_ready = await douyin_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Douyin cookie is missing or expired: {account_file}. Run `sau douyin login --account {request.account_name}` first."
        )

    app = DouYinNote(
        image_paths=[str(path) for path in request.image_files],
        title=request.title,
        note=request.note,
        tags=request.tags,
        publish_date=request.publish_date,
        account_file=str(account_file),
        publish_strategy=request.publish_strategy,
        debug=request.debug,
        headless=request.headless,
        bgm=request.bgm,
    )
    await app.douyin_upload_note()
    return account_file


async def upload_kuaishou_video(request: KuaishouVideoUploadRequest) -> Path:
    account_file = resolve_account_file("kuaishou", request.account_name)
    is_ready = await ks_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Kuaishou cookie is missing or expired: {account_file}. Run `sau kuaishou login --account {request.account_name}` first."
        )

    app = KSVideo(
        title=request.title,
        file_path=str(request.video_file),
        desc=request.description,
        tags=request.tags,
        publish_date=request.publish_date,
        account_file=str(account_file),
        thumbnail_path=str(request.thumbnail_file) if request.thumbnail_file else None,
        publish_strategy=request.publish_strategy,
        debug=request.debug,
        headless=request.headless,
        collection_name=request.collection_name,
    )
    await app.main()
    return account_file


async def upload_kuaishou_note(request: KuaishouNoteUploadRequest) -> Path:
    account_file = resolve_account_file("kuaishou", request.account_name)
    is_ready = await ks_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Kuaishou cookie is missing or expired: {account_file}. Run `sau kuaishou login --account {request.account_name}` first."
        )

    app = KSNote(
        image_paths=[str(path) for path in request.image_files],
        title=request.title,
        note=request.note,
        tags=request.tags,
        publish_date=request.publish_date,
        account_file=str(account_file),
        publish_strategy=request.publish_strategy,
        debug=request.debug,
        headless=request.headless,
    )
    await app.main()
    return account_file


async def upload_xiaohongshu_video(request: XiaohongshuVideoUploadRequest) -> Path:
    account_file = resolve_account_file("xiaohongshu", request.account_name)
    is_ready = await xiaohongshu_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Xiaohongshu cookie is missing or expired: {account_file}. Run `sau xiaohongshu login --account {request.account_name}` first."
        )

    app = XiaoHongShuVideo(
        title=request.title,
        file_path=str(request.video_file),
        desc=request.description,
        tags=request.tags,
        publish_date=request.publish_date,
        account_file=str(account_file),
        thumbnail_path=str(request.thumbnail_file) if request.thumbnail_file else None,
        publish_strategy=request.publish_strategy,
        debug=request.debug,
        headless=request.headless,
    )
    await app.main()
    return account_file


async def upload_xiaohongshu_note(request: XiaohongshuNoteUploadRequest) -> Path:
    account_file = resolve_account_file("xiaohongshu", request.account_name)
    is_ready = await xiaohongshu_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Xiaohongshu cookie is missing or expired: {account_file}. Run `sau xiaohongshu login --account {request.account_name}` first."
        )

    app = XiaoHongShuNote(
        image_paths=[str(path) for path in request.image_files],
        title=request.title,
        desc=request.note,
        note=request.note,
        tags=request.tags,
        publish_date=request.publish_date,
        account_file=str(account_file),
        publish_strategy=request.publish_strategy,
        debug=request.debug,
        headless=request.headless,
    )
    await app.main()
    return account_file


async def upload_bilibili_video(request: BilibiliVideoUploadRequest) -> Path:
    account_file = resolve_account_file("bilibili", request.account_name)
    if not account_file.exists():
        raise RuntimeError(
            f"Bilibili account file is missing: {account_file}. Run `sau bilibili login --account {request.account_name}` first."
        )

    arguments = [
        "-u",
        str(account_file),
        "upload",
        str(request.video_file),
        "--title",
        request.title,
        "--desc",
        request.description,
        "--tid",
        str(request.tid),
    ]
    if request.tags:
        arguments.extend(["--tag", ",".join(request.tags)])
    if request.thumbnail_file:
        arguments.extend(["--cover", str(request.thumbnail_file)])
    if isinstance(request.publish_date, datetime):
        arguments.extend(["--dtime", str(int(request.publish_date.timestamp()))])

    result = run_biliup_command(arguments)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "").strip() or "Bilibili upload failed")
    return account_file


async def upload_tencent_video(request: TencentVideoUploadRequest) -> Path:
    account_file = resolve_account_file("tencent", request.account_name)
    is_ready = await tencent_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Tencent/WeChat Channels cookie is missing or expired: {account_file}. "
            f"Run `sau tencent login --account {request.account_name}` first."
        )

    app = TencentVideo(
        title=request.title,
        file_path=str(request.video_file),
        tags=request.tags,
        publish_date=request.publish_date,
        account_file=str(account_file),
        category=request.category,
        is_draft=request.is_draft,
        desc=request.description,
        thumbnail_path=str(request.thumbnail_file) if request.thumbnail_file else None,
        thumbnail_landscape_path=(
            str(request.thumbnail_landscape_file) if request.thumbnail_landscape_file else None
        ),
        thumbnail_portrait_path=(
            str(request.thumbnail_portrait_file) if request.thumbnail_portrait_file else None
        ),
        short_title=request.short_title,
        publish_strategy=request.publish_strategy,
        debug=request.debug,
        headless=request.headless,
        collection_name=request.collection_name,
    )
    await app.tencent_upload_video()
    return account_file


async def login_baijiahao_account(account_name: str, headless: bool = True, qrcode_callback=None) -> dict:
    account_file = resolve_account_file("baijiahao", account_name)
    return await baijiahao_setup(str(account_file), handle=True, return_detail=True, headless=headless, qrcode_callback=qrcode_callback)


async def check_baijiahao_account(account_name: str) -> bool:
    account_file = resolve_account_file("baijiahao", account_name)
    if not account_file.exists():
        return False
    return await _safe_check(baijiahao_cookie_auth(str(account_file)), str(account_file))


async def upload_baijiahao_video(request: BaijiahaoVideoUploadRequest) -> Path:
    account_file = resolve_account_file("baijiahao", request.account_name)
    is_ready = await baijiahao_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Baijiahao cookie is missing or expired: {account_file}. Run `sau baijiahao login --account {request.account_name}` first."
        )

    app = BaiJiaHaoVideo(
        title=request.title,
        file_path=str(request.video_file),
        tags=request.tags,
        account_file=str(account_file),
        desc=request.description,
        thumbnail_path=str(request.thumbnail_file) if request.thumbnail_file else None,
        collection_name=request.collection_name,
        debug=request.debug,
        headless=request.headless,
    )
    await app.main()
    return account_file


async def login_alipay_account(account_name: str, headless: bool = True, qrcode_callback=None) -> dict:
    account_file = resolve_account_file("alipay", account_name)
    return await alipay_setup(str(account_file), handle=True, return_detail=True, headless=headless, qrcode_callback=qrcode_callback)


async def check_alipay_account(account_name: str) -> bool:
    account_file = resolve_account_file("alipay", account_name)
    if not account_file.exists():
        return False
    return await _safe_check(alipay_cookie_auth(str(account_file)), str(account_file))


async def upload_alipay_video(request: AlipayVideoUploadRequest) -> Path:
    account_file = resolve_account_file("alipay", request.account_name)
    is_ready = await alipay_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Alipay cookie is missing or expired: {account_file}. Run `sau alipay login --account {request.account_name}` first."
        )

    app = AlipayVideo(
        title=request.title,
        file_path=str(request.video_file),
        tags=request.tags,
        account_file=str(account_file),
        desc=request.description,
        thumbnail_path=str(request.thumbnail_file) if request.thumbnail_file else None,
        collection_name=request.collection_name,
        debug=request.debug,
        headless=request.headless,
    )
    await app.main()
    return account_file


async def login_weibo_account(account_name: str, headless: bool = True, qrcode_callback=None) -> dict:
    account_file = resolve_account_file("weibo", account_name)
    return await weibo_setup(str(account_file), handle=True, return_detail=True, headless=headless, qrcode_callback=qrcode_callback)


async def check_weibo_account(account_name: str) -> bool:
    account_file = resolve_account_file("weibo", account_name)
    if not account_file.exists():
        return False
    return await _safe_check(weibo_cookie_auth(str(account_file)), str(account_file))


async def upload_weibo_video(request: WeiboVideoUploadRequest) -> Path:
    account_file = resolve_account_file("weibo", request.account_name)
    is_ready = await weibo_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Weibo cookie is missing or expired: {account_file}. Run `sau weibo login --account {request.account_name}` first."
        )

    app = WeiBoVideo(
        title=request.title,
        file_path=str(request.video_file),
        tags=request.tags,
        account_file=str(account_file),
        desc=request.description,
        thumbnail_path=str(request.thumbnail_file) if request.thumbnail_file else None,
        collection_name=request.collection_name,
        debug=request.debug,
        headless=request.headless,
    )
    await app.main()
    return account_file


async def login_hupu_account(account_name: str, headless: bool = False, qrcode_callback=None) -> dict:
    account_file = resolve_account_file("hupu", account_name)
    return await hupu_setup(str(account_file), handle=True, return_detail=True, headless=headless, qrcode_callback=qrcode_callback)


async def check_hupu_account(account_name: str) -> bool:
    account_file = resolve_account_file("hupu", account_name)
    if not account_file.exists():
        return False
    return await _safe_check(hupu_cookie_auth(str(account_file)), str(account_file))


async def upload_hupu_video(request: HupuVideoUploadRequest) -> Path:
    account_file = resolve_account_file("hupu", request.account_name)
    is_ready = await hupu_setup(str(account_file), handle=False)
    if not is_ready:
        raise RuntimeError(
            f"Hupu cookie is missing or expired: {account_file}. Run `sau hupu login --account {request.account_name}` first."
        )

    app = HuPuVideo(
        title=request.title,
        file_path=str(request.video_file),
        tags=request.tags,
        account_file=str(account_file),
        desc=request.description,
        thumbnail_path=str(request.thumbnail_file) if request.thumbnail_file else None,
        debug=request.debug,
        headless=request.headless,
    )
    await app.main()
    return account_file


def existing_file_path(value: str) -> Path:
    path = Path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"File not found: {value}")
    return path


def schedule_value(value: str):
    try:
        return parse_schedule(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid schedule '{value}'. Expected format: {SCHEDULE_FORMAT}"
        ) from exc


def add_runtime_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--screencast", action="store_true", help="Enable CDP live canvas screencast stream")
    parser.add_argument("--app-mode", action="store_true", help="Launch in clean, native Chrome App mode (borderless, 0 latency, 4K quality)")
    parser.add_argument("--task-id", default="", help="Associated task ID for screencast frame identification")
    headless_group = parser.add_mutually_exclusive_group()
    headless_group.add_argument("--headed", dest="headless", action="store_false", help="Run with browser UI")
    headless_group.add_argument("--headless", dest="headless", action="store_true", help="Run in headless mode")
    parser.set_defaults(headless=True)


def build_parser() -> argparse.ArgumentParser:
    schedule_help = SCHEDULE_FORMAT.replace("%", "%%")
    parser = argparse.ArgumentParser(
        prog="sau",
        description="CLI for social-auto-upload.",
    )
    platform_parsers = parser.add_subparsers(dest="platform", required=True)

    douyin_parser = platform_parsers.add_parser("douyin", help="Douyin operations")
    douyin_actions = douyin_parser.add_subparsers(dest="action", required=True)

    for action_name in ("login", "check"):
        action_parser = douyin_actions.add_parser(action_name, help=f"Douyin {action_name}")
        action_parser.add_argument("--account", required=True, help="Douyin user-defined account_name")
        if action_name == "login":
            add_runtime_flags(action_parser)

    upload_video_parser = douyin_actions.add_parser("upload-video", help="Upload one video to Douyin")
    upload_video_parser.add_argument("--account", required=True, help="Douyin user-defined account_name")
    upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    upload_video_parser.add_argument("--title", required=True, help="Video title")
    upload_video_parser.add_argument("--desc", default="", help="Optional video description")
    upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    upload_video_parser.add_argument("--schedule", type=schedule_value, help=f"Schedule time in {schedule_help}")
    upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional 3:4 portrait thumbnail path")
    upload_video_parser.add_argument("--thumbnail-landscape", type=existing_file_path, help="Optional 4:3 landscape thumbnail path")
    upload_video_parser.add_argument("--thumbnail-portrait", type=existing_file_path, help="Optional 3:4 portrait thumbnail path")
    upload_video_parser.add_argument("--product-link", default="", help="Optional product link")
    upload_video_parser.add_argument("--product-title", default="", help="Optional product title")
    upload_video_parser.add_argument(
        "--declaration",
        help="Exact Douyin self-declaration option text; omitted means do not set one",
    )
    upload_video_parser.add_argument("--collection", default=None, help="Optional collection name to add the work into (must already exist)")
    add_runtime_flags(upload_video_parser)

    upload_note_parser = douyin_actions.add_parser("upload-note", help="Upload one note to Douyin")
    upload_note_parser.add_argument("--account", required=True, help="Douyin user-defined account_name")
    upload_note_parser.add_argument("--images", required=True, nargs="+", type=existing_file_path, help="Image file paths")
    upload_note_parser.add_argument("--title", required=True, help="Note title")
    upload_note_parser.add_argument("--note", default="", help="Optional note content")
    upload_note_parser.add_argument("--notef", default="", help="Read note content from file (txt/md)")
    upload_note_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    upload_note_parser.add_argument("--bgm", default="", help="BGM music name to search and select")
    upload_note_parser.add_argument("--schedule", type=schedule_value, help=f"Schedule time in {schedule_help}")
    add_runtime_flags(upload_note_parser)

    kuaishou_parser = platform_parsers.add_parser("kuaishou", help="Kuaishou operations")
    kuaishou_actions = kuaishou_parser.add_subparsers(dest="action", required=True)

    for action_name in ("login", "check"):
        action_parser = kuaishou_actions.add_parser(action_name, help=f"Kuaishou {action_name}")
        action_parser.add_argument("--account", required=True, help="Kuaishou user-defined account_name")
        if action_name == "login":
            add_runtime_flags(action_parser)

    kuaishou_upload_video_parser = kuaishou_actions.add_parser("upload-video", help="Upload one video to Kuaishou")
    kuaishou_upload_video_parser.add_argument("--account", required=True, help="Kuaishou user-defined account_name")
    kuaishou_upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    kuaishou_upload_video_parser.add_argument("--title", required=True, help="Video title")
    kuaishou_upload_video_parser.add_argument("--desc", default="", help="Optional video description")
    kuaishou_upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    kuaishou_upload_video_parser.add_argument("--schedule", type=schedule_value, help=f"Schedule time in {schedule_help}")
    kuaishou_upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional thumbnail path")
    kuaishou_upload_video_parser.add_argument("--collection", default=None, help="Optional collection name to add the work into (must already exist)")
    add_runtime_flags(kuaishou_upload_video_parser)

    kuaishou_upload_note_parser = kuaishou_actions.add_parser("upload-note", help="Upload one note to Kuaishou")
    kuaishou_upload_note_parser.add_argument("--account", required=True, help="Kuaishou user-defined account_name")
    kuaishou_upload_note_parser.add_argument("--images", required=True, nargs="+", type=existing_file_path, help="Image file paths")
    kuaishou_upload_note_parser.add_argument("--title", required=True, help="Note title")
    kuaishou_upload_note_parser.add_argument("--note", default="", help="Optional note content")
    kuaishou_upload_note_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    kuaishou_upload_note_parser.add_argument("--schedule", type=schedule_value, help=f"Schedule time in {schedule_help}")
    add_runtime_flags(kuaishou_upload_note_parser)

    xiaohongshu_parser = platform_parsers.add_parser("xiaohongshu", help="Xiaohongshu operations")
    xiaohongshu_actions = xiaohongshu_parser.add_subparsers(dest="action", required=True)

    for action_name in ("login", "check"):
        action_parser = xiaohongshu_actions.add_parser(action_name, help=f"Xiaohongshu {action_name}")
        action_parser.add_argument("--account", required=True, help="Xiaohongshu user-defined account_name")
        if action_name == "login":
            add_runtime_flags(action_parser)

    xiaohongshu_upload_video_parser = xiaohongshu_actions.add_parser("upload-video", help="Upload one video to Xiaohongshu")
    xiaohongshu_upload_video_parser.add_argument("--account", required=True, help="Xiaohongshu user-defined account_name")
    xiaohongshu_upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    xiaohongshu_upload_video_parser.add_argument("--title", required=True, help="Video title")
    xiaohongshu_upload_video_parser.add_argument("--desc", default="", help="Optional video description")
    xiaohongshu_upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    xiaohongshu_upload_video_parser.add_argument("--schedule", type=schedule_value, help=f"Schedule time in {schedule_help}")
    xiaohongshu_upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional thumbnail path")
    add_runtime_flags(xiaohongshu_upload_video_parser)

    xiaohongshu_upload_note_parser = xiaohongshu_actions.add_parser("upload-note", help="Upload one note to Xiaohongshu")
    xiaohongshu_upload_note_parser.add_argument("--account", required=True, help="Xiaohongshu user-defined account_name")
    xiaohongshu_upload_note_parser.add_argument("--images", required=True, nargs="+", type=existing_file_path, help="Image file paths")
    xiaohongshu_upload_note_parser.add_argument("--title", required=True, help="Note title")
    xiaohongshu_upload_note_parser.add_argument("--note", default="", help="Optional note content")
    xiaohongshu_upload_note_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    xiaohongshu_upload_note_parser.add_argument("--schedule", type=schedule_value, help=f"Schedule time in {schedule_help}")
    add_runtime_flags(xiaohongshu_upload_note_parser)

    bilibili_parser = platform_parsers.add_parser("bilibili", help="Bilibili operations")
    bilibili_actions = bilibili_parser.add_subparsers(dest="action", required=True)

    for action_name in ("login", "check"):
        action_parser = bilibili_actions.add_parser(action_name, help=f"Bilibili {action_name}")
        action_parser.add_argument("--account", required=True, help="Bilibili user-defined account_name")
        if action_name == "login":
            add_runtime_flags(action_parser)

    bilibili_upload_video_parser = bilibili_actions.add_parser("upload-video", help="Upload one video to Bilibili")
    bilibili_upload_video_parser.add_argument("--account", required=True, help="Bilibili user-defined account_name")
    bilibili_upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    bilibili_upload_video_parser.add_argument("--title", required=True, help="Video title")
    bilibili_upload_video_parser.add_argument("--desc", required=True, help="Video description")
    bilibili_upload_video_parser.add_argument("--tid", required=True, type=int, help="Bilibili category id")
    bilibili_upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    bilibili_upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional Bilibili cover image path")
    bilibili_upload_video_parser.add_argument("--schedule", type=schedule_value, help=f"Schedule time in {schedule_help}")
    add_runtime_flags(bilibili_upload_video_parser)

    tencent_parser = platform_parsers.add_parser("tencent", help="Tencent/WeChat Channels operations")
    tencent_actions = tencent_parser.add_subparsers(dest="action", required=True)

    for action_name in ("login", "check"):
        action_parser = tencent_actions.add_parser(action_name, help=f"Tencent/WeChat Channels {action_name}")
        action_parser.add_argument("--account", default="auto", help="Tencent user-defined account_name (default: auto)")
        if action_name == "login":
            add_runtime_flags(action_parser)


    tencent_upload_video_parser = tencent_actions.add_parser("upload-video", help="Upload one video to WeChat Channels")
    tencent_upload_video_parser.add_argument("--account", required=True, help="Tencent user-defined account_name")
    tencent_upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    tencent_upload_video_parser.add_argument("--title", required=True, help="Video title")
    tencent_upload_video_parser.add_argument("--desc", default="", help="Optional video description")
    tencent_upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    tencent_upload_video_parser.add_argument("--schedule", type=schedule_value, help=f"Schedule time in {schedule_help}")
    tencent_upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional 3:4 portrait thumbnail path")
    tencent_upload_video_parser.add_argument("--thumbnail-landscape", type=existing_file_path, help="Optional 4:3 landscape thumbnail path")
    tencent_upload_video_parser.add_argument("--thumbnail-portrait", type=existing_file_path, help="Optional 3:4 portrait thumbnail path")
    tencent_upload_video_parser.add_argument("--short-title", help="Optional WeChat Channels short title")
    tencent_upload_video_parser.add_argument("--category", help="Optional original content category")
    tencent_upload_video_parser.add_argument("--draft", action="store_true", help="Save as draft instead of publishing")
    tencent_upload_video_parser.add_argument("--collection", default=None, help="Optional collection name to add the work into (must already exist)")
    add_runtime_flags(tencent_upload_video_parser)

    alipay_parser = platform_parsers.add_parser("alipay", help="Alipay life account operations")
    alipay_actions = alipay_parser.add_subparsers(dest="action", required=True)

    for action_name in ("login", "check"):
        action_parser = alipay_actions.add_parser(action_name, help=f"Alipay {action_name}")
        action_parser.add_argument("--account", required=True, help="Alipay user-defined account_name")
        if action_name == "login":
            add_runtime_flags(action_parser)

    alipay_upload_video_parser = alipay_actions.add_parser("upload-video", help="Upload one video to Alipay")
    alipay_upload_video_parser.add_argument("--account", required=True, help="Alipay user-defined account_name")
    alipay_upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    alipay_upload_video_parser.add_argument("--title", required=True, help="Video title")
    alipay_upload_video_parser.add_argument("--desc", default="", help="Optional video description")
    alipay_upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    alipay_upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional cover image path")
    alipay_upload_video_parser.add_argument("--collection", default=None, help="Optional collection name to add the work into (must already exist)")
    add_runtime_flags(alipay_upload_video_parser)

    # ── Weibo ──
    weibo_parser = platform_parsers.add_parser("weibo", help="Sina Weibo operations")
    weibo_actions = weibo_parser.add_subparsers(dest="action", required=True)

    for action_name in ("login", "check"):
        action_parser = weibo_actions.add_parser(action_name, help=f"Weibo {action_name}")
        action_parser.add_argument("--account", required=True, help="Weibo user-defined account_name")
        if action_name == "login":
            add_runtime_flags(action_parser)

    weibo_upload_video_parser = weibo_actions.add_parser("upload-video", help="Upload one video to Weibo")
    weibo_upload_video_parser.add_argument("--account", required=True, help="Weibo user-defined account_name")
    weibo_upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    weibo_upload_video_parser.add_argument("--title", required=True, help="Video title (max 30 chars)")
    weibo_upload_video_parser.add_argument("--desc", default="", help="Optional video description")
    weibo_upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    weibo_upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional cover image path (<5MB)")
    weibo_upload_video_parser.add_argument("--collection", default=None, help="Optional collection name")
    add_runtime_flags(weibo_upload_video_parser)

    # ── Hupu ──
    hupu_parser = platform_parsers.add_parser("hupu", help="Hupu (虎扑) operations")
    hupu_actions = hupu_parser.add_subparsers(dest="action", required=True)

    for action_name in ("login", "check"):
        action_parser = hupu_actions.add_parser(action_name, help=f"Hupu {action_name}")
        action_parser.add_argument("--account", required=True, help="Hupu user-defined account_name")
        if action_name == "login":
            add_runtime_flags(action_parser)

    hupu_upload_video_parser = hupu_actions.add_parser("upload-video", help="Upload one video to Hupu")
    hupu_upload_video_parser.add_argument("--account", required=True, help="Hupu user-defined account_name")
    hupu_upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    hupu_upload_video_parser.add_argument("--title", required=True, help="Video title (4-40 chars)")
    hupu_upload_video_parser.add_argument("--desc", default="", help="Optional video description")
    hupu_upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    hupu_upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional cover image path")
    add_runtime_flags(hupu_upload_video_parser)

    youtube_parser = platform_parsers.add_parser("youtube", help="YouTube operations")
    youtube_actions = youtube_parser.add_subparsers(dest="action", required=True)

    for action_name in ("login", "check"):
        action_parser = youtube_actions.add_parser(action_name, help=f"YouTube {action_name}")
        action_parser.add_argument("--account", required=True, help="YouTube user-defined account_name")
        if action_name == "login":
            add_runtime_flags(action_parser)

    youtube_upload_video_parser = youtube_actions.add_parser("upload-video", help="Upload one video to YouTube")
    youtube_upload_video_parser.add_argument("--account", required=True, help="YouTube user-defined account_name")
    youtube_upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    youtube_upload_video_parser.add_argument("--title", required=True, help="Video title (<=100 chars)")
    youtube_upload_video_parser.add_argument("--desc", default="", help="Optional video description")
    youtube_upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    youtube_upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional thumbnail image path")
    youtube_upload_video_parser.add_argument("--playlist", help="Optional playlist name to add the video to (for series)")
    youtube_upload_video_parser.add_argument(
        "--visibility", default="public", choices=["public", "unlisted", "private"], help="Video visibility")
    add_runtime_flags(youtube_upload_video_parser)

    baijiahao_parser = platform_parsers.add_parser("baijiahao", help="Baidu Baijiahao operations")
    baijiahao_actions = baijiahao_parser.add_subparsers(dest="action", required=True)

    for action_name in ("login", "check"):
        action_parser = baijiahao_actions.add_parser(action_name, help=f"Baijiahao {action_name}")
        action_parser.add_argument("--account", required=True, help="Baijiahao user-defined account_name")
        if action_name == "login":
            add_runtime_flags(action_parser)

    baijiahao_upload_video_parser = baijiahao_actions.add_parser("upload-video", help="Upload one video to Baijiahao")
    baijiahao_upload_video_parser.add_argument("--account", required=True, help="Baijiahao user-defined account_name")
    baijiahao_upload_video_parser.add_argument("--file", required=True, type=existing_file_path, help="Video file path")
    baijiahao_upload_video_parser.add_argument("--title", required=True, help="Video title")
    baijiahao_upload_video_parser.add_argument("--desc", default="", help="Optional video description")
    baijiahao_upload_video_parser.add_argument("--tags", default="", help="Comma-separated tags, such as tag1,tag2")
    baijiahao_upload_video_parser.add_argument("--thumbnail", type=existing_file_path, help="Optional cover image path")
    baijiahao_upload_video_parser.add_argument("--collection", default=None, help="Optional collection name")
    add_runtime_flags(baijiahao_upload_video_parser)

    return parser


CREATOR_PLATFORM_URLS = {
    "douyin": "https://creator.douyin.com/",
    "xiaohongshu": "https://creator.xiaohongshu.com/",
    "kuaishou": "https://cp.kuaishou.com/",
    "tencent": "https://channels.weixin.qq.com/platform",
    "bilibili": "https://member.bilibili.com/",
    "weibo": "https://weibo.com/",
    "baijiahao": "https://baijiahao.baidu.com/",
}


async def run_interactive_browser_session(platform: str, account_name: str, headless: bool = True) -> int:
    """拉起长连接浏览器会话：
    - 若 headless=False (原生模式)：拉起原生 Chrome App 沉浸式应用视窗 (4K Retina 视网膜画质，0 延迟，原生打字与手势)；
    - 若 headless=True (投屏模式)：拉起无头浏览器并通过 CDP 向前端 Canvas 实时推流。
    直到用户在桌面端手动关闭或主动退出窗口。
    """
    account_file = resolve_account_file(platform, account_name)
    creator_url = CREATOR_PLATFORM_URLS.get(platform, "https://creator.douyin.com/")

    try:
        from patchright.async_api import async_playwright
    except ImportError:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError("未检测到 patchright 或 playwright 自动化浏览器库，请先安装对应依赖")

    try:
        async with async_playwright() as playwright:
            browser = None
            from conf import LOCAL_CHROME_PATH
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--no-first-run",
                "--no-default-browser-check",
            ]
            if not headless:
                launch_args.append("--window-size=1280,820")

            # 统一策略备选链：无论是原生真机窗口还是内嵌投屏视窗，均优先使用原生 Chrome/Edge 浏览器
            # 彻底避免 headless 模式硬找缺失的 chromium_headless_shell.exe 崩溃
            strategies = []
            if LOCAL_CHROME_PATH and Path(LOCAL_CHROME_PATH).exists():
                strategies.append((f"指定路径浏览器 ({LOCAL_CHROME_PATH})", {"executable_path": LOCAL_CHROME_PATH, "headless": headless, "args": launch_args}))

            if sys.platform == "win32":
                strategies.append(("系统原生 Microsoft Edge", {"channel": "msedge", "headless": headless, "args": launch_args}))
                strategies.append(("系统原生 Google Chrome", {"channel": "chrome", "headless": headless, "args": launch_args}))
            elif sys.platform == "darwin":
                strategies.append(("系统 Google Chrome", {"channel": "chrome", "headless": headless, "args": launch_args}))
                strategies.append(("系统 Microsoft Edge", {"channel": "msedge", "headless": headless, "args": launch_args}))

            # 内置绿色 Chromium 兜底
            strategies.append(("内置绿色 Chromium 内核", {"headless": headless, "args": launch_args}))

            launch_errors = []
            for name, opts in strategies:
                try:
                    sys.stdout.write(f"[BROWSER_INIT] 正在尝试拉起: {name} (headless={headless})...\n")
                    sys.stdout.flush()
                    browser = await playwright.chromium.launch(**opts)
                    if browser:
                        sys.stdout.write(f"[BROWSER_INIT] ✅ 成功拉起: {name}\n")
                        sys.stdout.flush()
                        break
                except Exception as e:
                    err_msg = f"{name} 启动失败: {e}"
                    launch_errors.append(err_msg)
                    sys.stderr.write(f"{err_msg}\n")
                    sys.stderr.flush()

            if not browser:
                raise RuntimeError("所有浏览器启动尝试均失败:\n" + "\n".join(launch_errors))

            viewport_config = {"width": 1280, "height": 820} if not headless else {"width": 1440, "height": 900}
            context_kwargs = {
                "viewport": viewport_config
            }

            if account_file.exists():
                try:
                    context = await browser.new_context(storage_state=str(account_file), **context_kwargs)
                except Exception:
                    context = await browser.new_context(**context_kwargs)
                    try:
                        with open(account_file, "r", encoding="utf-8") as f:
                            state_data = json.load(f)
                        cookies = state_data.get("cookies", [])
                        if cookies:
                            await context.add_cookies(cookies)
                    except Exception:
                        pass
            else:
                context = await browser.new_context(**context_kwargs)

            try:
                from uploader.douyin_uploader.main import set_init_script
                context = await set_init_script(context)
            except Exception:
                pass

            page = await context.new_page()
            log_tag = "[APP_INFO] Native browser window launched" if not headless else "[CDP_INFO] Opening creator studio URL"
            sys.stdout.write(f"{log_tag} for {platform}: {creator_url}\n")
            sys.stdout.flush()
            try:
                await page.goto(creator_url, wait_until="domcontentloaded")
            except Exception as e:
                sys.stderr.write(f"Warning navigating to {creator_url}: {e}\n")

            login_notified = False
            try:
                while True:
                    # 检查页面是否已被用户手动关闭
                    if page.is_closed():
                        sys.stdout.write("[APP_INFO] Browser page was closed by user.\n")
                        sys.stdout.flush()
                        break

                    if not login_notified:
                        current_url = page.url
                        is_logged_in = False
                        extracted_nickname = ""
                        extracted_uid = ""

                        if platform == "tencent":
                            # 腾讯视频号：页面未登录时往往也是 channels.weixin.qq.com/platform 路径，但会内嵌扫码 iframe 或弹出登录框
                            has_qr_frame = any("open.weixin.qq.com/connect/qrconnect" in fr.url for fr in page.frames)
                            has_login_url = "login.html" in current_url
                            if not has_qr_frame and not has_login_url and "channels.weixin.qq.com" in current_url:
                                # 必须能查找到可见的创作者昵称元素，才确认为已成功登录态
                                try:
                                    for sel in ["h2.finder-nickname", "div.finder-nickname", "div.side-bar-footer .account-info span.name"]:
                                        el = page.locator(sel).first
                                        if await el.count() and await el.is_visible():
                                            t = (await el.inner_text()).strip()
                                            if t and len(t) < 40:
                                                extracted_nickname = t
                                                is_logged_in = True
                                                break
                                except Exception:
                                    pass
                        elif platform == "douyin":
                            if "creator.douyin.com" in current_url and "login" not in current_url:
                                try:
                                    for sel in ["div.avatar-wrap + span", "div.user-info-name", "div.name-wrap span"]:
                                        el = page.locator(sel).first
                                        if await el.count() and await el.is_visible():
                                            t = (await el.inner_text()).strip()
                                            if t:
                                                extracted_nickname = t
                                                is_logged_in = True
                                                break
                                except Exception:
                                    pass
                        elif platform == "xiaohongshu":
                            if "creator.xiaohongshu.com" in current_url and "login" not in current_url:
                                try:
                                    for sel in ["div.user-info span.name", "div.name"]:
                                        el = page.locator(sel).first
                                        if await el.count() and await el.is_visible():
                                            t = (await el.inner_text()).strip()
                                            if t:
                                                extracted_nickname = t
                                                is_logged_in = True
                                                break
                                except Exception:
                                    pass
                        elif platform == "kuaishou":
                            if "cp.kuaishou.com" in current_url and "login" not in current_url:
                                try:
                                    for sel in ["div.user-name", "span.user-name"]:
                                        el = page.locator(sel).first
                                        if await el.count() and await el.is_visible():
                                            t = (await el.inner_text()).strip()
                                            if t:
                                                extracted_nickname = t
                                                is_logged_in = True
                                                break
                                except Exception:
                                    pass
                        else:
                            # 其它平台：URL 不含 login 且有用户信息元素
                            if "login" not in current_url.lower():
                                is_logged_in = True

                        if is_logged_in:
                            try:
                                uid_el = page.locator("span.finder-uniq-id, #finder-uid-copy").first
                                if await uid_el.count():
                                    extracted_uid = (await uid_el.inner_text()).strip()
                            except Exception:
                                pass

                            try:
                                await context.storage_state(path=str(account_file))
                            except Exception:
                                pass

                            meta_dict = {
                                "success": True,
                                "nickname": extracted_nickname or account_name,
                                "finder_uid": extracted_uid,
                                "account_name": account_name,
                                "platform": platform
                            }
                            sys.stdout.write(f"{platform.capitalize()} login flow completed: {json.dumps(meta_dict, ensure_ascii=False)}\n")
                            sys.stdout.flush()
                            login_notified = True

                    await asyncio.sleep(1)
                    # 每 30 秒自动快照存盘
                    if int(asyncio.get_event_loop().time()) % 30 == 0:
                        try:
                            await context.storage_state(path=str(account_file))
                        except Exception:
                            pass
            except (asyncio.CancelledError, KeyboardInterrupt):
                pass
            finally:
                try:
                    await context.storage_state(path=str(account_file))
                except Exception:
                    pass
                try:
                    await context.close()
                except Exception:
                    pass
                if browser:
                    try:
                        await browser.close()
                    except Exception:
                        pass

    except Exception as e:
        import traceback
        err_msg = f"拉起浏览器会话异常: {e}"
        sys.stderr.write(f"{err_msg}\n{traceback.format_exc()}\n")
        sys.stdout.write(f"[ERROR] {err_msg}\n")
        sys.stdout.flush()
        return 1

    return 0


async def dispatch(args: argparse.Namespace) -> int:
    if getattr(args, "task_id", ""):
        os.environ["CURRENT_TASK_ID"] = args.task_id
    if getattr(args, "screencast", False):
        os.environ["ENABLE_SCREENCAST"] = "1"
        try:
            from myUtils.cdp_screencast import install_global_screencast_hook
            install_global_screencast_hook()
        except Exception as e:
            sys.stderr.write(f"Failed to install screencast hook: {e}\n")

    # 桌面端原生真机 App 视窗或内嵌无头长连接会话（支持扫码、自由操作、查看个人资料与数据，直到用户手动关闭）
    if (getattr(args, "screencast", False) or getattr(args, "app_mode", False)) and args.action == "login":
        return await run_interactive_browser_session(args.platform, args.account, headless=args.headless)

    if args.platform == "douyin":
        if args.action == "login":
            result = await login_douyin_account(args.account, headless=args.headless)
            if not result["success"]:
                raise RuntimeError(result["message"])
            print(f"Douyin login flow completed: {result['account_file']}")
            return 0

        if args.action == "check":
            is_valid = await check_douyin_account(args.account)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        publish_strategy = DOUYIN_PUBLISH_STRATEGY_SCHEDULED if args.schedule else DOUYIN_PUBLISH_STRATEGY_IMMEDIATE

        if args.action == "upload-video":
            request = DouyinVideoUploadRequest(
                account_name=args.account,
                video_file=args.file,
                title=args.title,
                description=args.desc,
                tags=parse_tags(args.tags),
                publish_date=args.schedule or 0,
                thumbnail_file=args.thumbnail,
                thumbnail_landscape_file=args.thumbnail_landscape,
                thumbnail_portrait_file=args.thumbnail_portrait,
                product_link=args.product_link,
                product_title=args.product_title,
                declaration=args.declaration,
                publish_strategy=publish_strategy,
                debug=args.debug,
                headless=args.headless,
                collection_name=args.collection,
            )
            await upload_video(request)
            print(f"Douyin video upload submitted: {request.video_file}")
            return 0

        if args.action == "upload-note":
            # 如果指定了 --notef，读取文件内容作为 note
            note_content = args.note
            if args.notef:
                note_file = Path(args.notef)
                if not note_file.exists():
                    print(f"错误：文件不存在: {note_file}", file=sys.stderr)
                    return 1
                note_content = note_file.read_text(encoding="utf-8")

            request = DouyinNoteUploadRequest(
                account_name=args.account,
                image_files=parse_image_files(args.images),
                title=args.title,
                note=note_content,
                tags=parse_tags(args.tags),
                publish_date=args.schedule or 0,
                publish_strategy=publish_strategy,
                debug=args.debug,
                headless=args.headless,
                bgm=args.bgm or "",
            )
            await upload_note(request)
            print(f"Douyin note upload submitted: {len(request.image_files)} images")
            return 0

        raise RuntimeError(f"Unsupported Douyin action: {args.action}")

    if args.platform == "kuaishou":
        if args.action == "login":
            result = await login_kuaishou_account(args.account, headless=args.headless)
            if not result["success"]:
                raise RuntimeError(result["message"])
            print(f"Kuaishou login flow completed: {result['account_file']}")
            return 0

        if args.action == "check":
            is_valid = await check_kuaishou_account(args.account)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        publish_strategy = KUAISHOU_PUBLISH_STRATEGY_SCHEDULED if args.schedule else KUAISHOU_PUBLISH_STRATEGY_IMMEDIATE

        if args.action == "upload-video":
            request = KuaishouVideoUploadRequest(
                account_name=args.account,
                video_file=args.file,
                title=args.title,
                description=args.desc,
                tags=parse_tags(args.tags),
                publish_date=args.schedule or 0,
                thumbnail_file=args.thumbnail,
                publish_strategy=publish_strategy,
                debug=args.debug,
                headless=args.headless,
                collection_name=args.collection,
            )
            await upload_kuaishou_video(request)
            print(f"Kuaishou video upload submitted: {request.video_file}")
            return 0

        if args.action == "upload-note":
            request = KuaishouNoteUploadRequest(
                account_name=args.account,
                image_files=parse_image_files(args.images),
                title=args.title,
                note=args.note,
                tags=parse_tags(args.tags),
                publish_date=args.schedule or 0,
                publish_strategy=publish_strategy,
                debug=args.debug,
                headless=args.headless,
            )
            await upload_kuaishou_note(request)
            print(f"Kuaishou note upload submitted: {len(request.image_files)} images")
            return 0

        raise RuntimeError(f"Unsupported Kuaishou action: {args.action}")

    if args.platform == "xiaohongshu":
        if args.action == "login":
            result = await login_xiaohongshu_account(args.account, headless=args.headless)
            if not result["success"]:
                raise RuntimeError(result["message"])
            print(f"Xiaohongshu login flow completed: {result['account_file']}")
            return 0

        if args.action == "check":
            is_valid = await check_xiaohongshu_account(args.account)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        publish_strategy = (
            XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED if args.schedule else XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE
        )

        if args.action == "upload-video":
            parsed_tags = parse_tags(args.tags)
            if len(parsed_tags) > 10:
                print(f"错误：小红书标签最多 10 个，当前提供了 {len(parsed_tags)} 个: {parsed_tags}", file=sys.stderr)
                return 1
            request = XiaohongshuVideoUploadRequest(
                account_name=args.account,
                video_file=args.file,
                title=args.title,
                description=args.desc,
                tags=parsed_tags,
                publish_date=args.schedule or 0,
                thumbnail_file=args.thumbnail,
                publish_strategy=publish_strategy,
                debug=args.debug,
                headless=args.headless,
            )
            await upload_xiaohongshu_video(request)
            print(f"Xiaohongshu video upload submitted: {request.video_file}")
            return 0

        if args.action == "upload-note":
            parsed_tags = parse_tags(args.tags)
            if len(parsed_tags) > 10:
                print(f"错误：小红书标签最多 10 个，当前提供了 {len(parsed_tags)} 个: {parsed_tags}", file=sys.stderr)
                return 1
            request = XiaohongshuNoteUploadRequest(
                account_name=args.account,
                image_files=parse_image_files(args.images),
                title=args.title,
                note=args.note,
                tags=parsed_tags,
                publish_date=args.schedule or 0,
                publish_strategy=publish_strategy,
                debug=args.debug,
                headless=args.headless,
            )
            await upload_xiaohongshu_note(request)
            print(f"Xiaohongshu note upload submitted: {len(request.image_files)} images")
            return 0

        raise RuntimeError(f"Unsupported Xiaohongshu action: {args.action}")

    if args.platform == "bilibili":
        if args.action == "login":
            result = await login_bilibili_account(args.account)
            if not result["success"]:
                raise RuntimeError(result["message"])
            print(f"Bilibili login flow completed: {result['account_file']}")
            return 0

        if args.action == "check":
            is_valid = await check_bilibili_account(args.account)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        if args.action == "upload-video":
            request = BilibiliVideoUploadRequest(
                account_name=args.account,
                video_file=args.file,
                title=args.title,
                description=args.desc,
                tid=args.tid,
                tags=parse_tags(args.tags),
                publish_date=args.schedule or 0,
                thumbnail_file=args.thumbnail,
            )
            await upload_bilibili_video(request)
            print(f"Bilibili video upload submitted: {request.video_file}")
            return 0

        raise RuntimeError(f"Unsupported Bilibili action: {args.action}")

    if args.platform == "tencent":
        if args.action == "login":
            result = await login_tencent_account(args.account, headless=args.headless)
            if not result["success"]:
                raise RuntimeError(result["message"])
            import json
            print(f"Tencent/WeChat Channels login flow completed: {json.dumps(result, ensure_ascii=False)}")
            return 0


        if args.action == "check":
            is_valid = await check_tencent_account(args.account)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        publish_strategy = TENCENT_PUBLISH_STRATEGY_SCHEDULED if args.schedule else TENCENT_PUBLISH_STRATEGY_IMMEDIATE

        if args.action == "upload-video":
            request = TencentVideoUploadRequest(
                account_name=args.account,
                video_file=args.file,
                title=args.title,
                description=args.desc,
                tags=parse_tags(args.tags),
                publish_date=args.schedule or 0,
                thumbnail_file=args.thumbnail,
                thumbnail_landscape_file=args.thumbnail_landscape,
                thumbnail_portrait_file=args.thumbnail_portrait,
                short_title=args.short_title,
                category=args.category,
                is_draft=args.draft,
                publish_strategy=publish_strategy,
                debug=args.debug,
                headless=args.headless,
                collection_name=args.collection,
            )
            await upload_tencent_video(request)
            print(f"Tencent/WeChat Channels video upload submitted: {request.video_file}")
            return 0

        raise RuntimeError(f"Unsupported Tencent/WeChat Channels action: {args.action}")

    if args.platform == "alipay":
        if args.action == "login":
            result = await login_alipay_account(args.account, headless=args.headless)
            if not result["success"]:
                raise RuntimeError(result["message"])
            print(f"Alipay login flow completed: {result['account_file']}")
            return 0

        if args.action == "check":
            is_valid = await check_alipay_account(args.account)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        if args.action == "upload-video":
            request = AlipayVideoUploadRequest(
                account_name=args.account,
                video_file=args.file,
                title=args.title,
                description=args.desc,
                tags=parse_tags(args.tags),
                thumbnail_file=args.thumbnail,
                collection_name=args.collection,
                debug=args.debug,
                headless=args.headless,
            )
            await upload_alipay_video(request)
            print(f"Alipay video upload submitted: {request.video_file}")
            return 0

        raise RuntimeError(f"Unsupported Alipay action: {args.action}")

    if args.platform == "weibo":
        if args.action == "login":
            result = await login_weibo_account(args.account, headless=args.headless)
            if not result["success"]:
                raise RuntimeError(result["message"])
            print(f"Weibo login flow completed: {result['account_file']}")
            return 0

        if args.action == "check":
            is_valid = await check_weibo_account(args.account)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        if args.action == "upload-video":
            request = WeiboVideoUploadRequest(
                account_name=args.account,
                video_file=args.file,
                title=args.title,
                description=args.desc,
                tags=parse_tags(args.tags),
                thumbnail_file=args.thumbnail,
                collection_name=args.collection,
                debug=args.debug,
                headless=args.headless,
            )
            await upload_weibo_video(request)
            print(f"Weibo video upload submitted: {request.video_file}")
            return 0

        raise RuntimeError(f"Unsupported Weibo action: {args.action}")

    if args.platform == "hupu":
        if args.action == "login":
            result = await login_hupu_account(args.account, headless=args.headless)
            if not result["success"]:
                raise RuntimeError(result["message"])
            print(f"Hupu login flow completed: {result['account_file']}")
            return 0

        if args.action == "check":
            is_valid = await check_hupu_account(args.account)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        if args.action == "upload-video":
            request = HupuVideoUploadRequest(
                account_name=args.account,
                video_file=args.file,
                title=args.title,
                description=args.desc,
                tags=parse_tags(args.tags),
                thumbnail_file=args.thumbnail,
                debug=args.debug,
                headless=args.headless,
            )
            await upload_hupu_video(request)
            print(f"Hupu video upload submitted: {request.video_file}")
            return 0

        raise RuntimeError(f"Unsupported Hupu action: {args.action}")

    if args.platform == "youtube":
        if args.action == "login":
            result = await login_youtube_account(args.account, headless=args.headless)
            if not result["success"]:
                raise RuntimeError(result["message"])
            print(f"YouTube login flow completed: {result['account_file']}")
            return 0

        if args.action == "check":
            is_valid = await check_youtube_account(args.account)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        if args.action == "upload-video":
            request = YouTubeVideoUploadRequest(
                account_name=args.account,
                video_file=args.file,
                title=args.title,
                description=args.desc,
                tags=parse_tags(args.tags),
                thumbnail_file=args.thumbnail,
                playlist=args.playlist,
                visibility=args.visibility,
                debug=args.debug,
                headless=args.headless,
            )
            await upload_youtube_video(request)
            print(f"YouTube video upload submitted: {request.video_file}")
            return 0

        raise RuntimeError(f"Unsupported YouTube action: {args.action}")

    if args.platform == "baijiahao":
        if args.action == "login":
            result = await login_baijiahao_account(args.account, headless=args.headless)
            if not result["success"]:
                raise RuntimeError(result["message"])
            print(f"Baijiahao login flow completed: {result['account_file']}")
            return 0

        if args.action == "check":
            is_valid = await check_baijiahao_account(args.account)
            print("valid" if is_valid else "invalid")
            return 0 if is_valid else 1

        if args.action == "upload-video":
            request = BaijiahaoVideoUploadRequest(
                account_name=args.account,
                video_file=args.file,
                title=args.title,
                description=args.desc,
                tags=parse_tags(args.tags),
                thumbnail_file=args.thumbnail,
                collection_name=args.collection,
                debug=args.debug,
                headless=args.headless,
            )
            await upload_baijiahao_video(request)
            print(f"Baijiahao video upload submitted: {request.video_file}")
            return 0

        raise RuntimeError(f"Unsupported Baijiahao action: {args.action}")

    raise RuntimeError(f"Unsupported platform: {args.platform}")


def main(argv: Sequence[str] | None = None) -> int:
    try:
        parser = build_parser()
        args = parser.parse_args(list(argv) if argv is not None else None)
        return asyncio.run(dispatch(args))
    except SystemExit as se:
        return se.code if isinstance(se.code, int) else (0 if se.code is None else 1)
    except Exception as exc:
        import traceback
        err_msg = f"[SAU_CLI_ERROR] {exc}\n{traceback.format_exc()}"
        sys.stderr.write(err_msg + "\n")
        sys.stderr.flush()
        return 1
    except BaseException as be:
        import traceback
        err_msg = f"[SAU_CLI_CRITICAL] {be}\n{traceback.format_exc()}"
        sys.stderr.write(err_msg + "\n")
        sys.stderr.flush()
        return 1


if __name__ == "__main__":
    try:
        code = main()
        sys.exit(code)
    except SystemExit as se:
        sys.exit(se.code)
    except BaseException:
        sys.exit(1)
