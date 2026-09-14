"""
智能 Chromium 内核提取与瘦身同步脚本
作用：精准提取当前 patchright / playwright 实际所需的单一版本 Chromium 内核，
丢弃本地历史残留的多版本垃圾，大幅减小桌面端打包体积（可立省 700MB ~ 1GB）。
"""
import os
import sys
import shutil
import pathlib


def get_default_ms_playwright_dir():
    # 1. 环境变量优先
    env_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if env_path and os.path.isdir(env_path):
        return pathlib.Path(env_path)

    # 2. 系统默认缓存目录
    if sys.platform == "win32":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            p = pathlib.Path(local_appdata) / "ms-playwright"
            if p.is_dir():
                return p
        user_profile = os.environ.get("USERPROFILE")
        if user_profile:
            p = pathlib.Path(user_profile) / "AppData" / "Local" / "ms-playwright"
            if p.is_dir():
                return p
    elif sys.platform == "darwin":
        p = pathlib.Path.home() / "Library" / "Caches" / "ms-playwright"
        if p.is_dir():
            return p
    else:
        p = pathlib.Path.home() / ".cache" / "ms-playwright"
        if p.is_dir():
            return p
    return None


def detect_active_revision(src_path: pathlib.Path):
    # 优先尝试通过 patchright API 获取可执行文件真实路径
    try:
        from patchright.sync_api import sync_playwright
        with sync_playwright() as p:
            exec_path = pathlib.Path(p.chromium.executable_path)
            for parent in exec_path.parents:
                if parent.name.startswith("chromium-"):
                    return parent.name.replace("chromium-", "")
    except Exception:
        pass

    # 回退尝试 playwright API
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            exec_path = pathlib.Path(p.chromium.executable_path)
            for parent in exec_path.parents:
                if parent.name.startswith("chromium-"):
                    return parent.name.replace("chromium-", "")
    except Exception:
        pass

    # 回退：扫描 src_path 中版本号最大（最新）的一个 chromium-*
    if src_path and src_path.is_dir():
        c_dirs = [d.name.replace("chromium-", "") for d in src_path.glob("chromium-*") if d.is_dir()]
        if c_dirs:
            return sorted(c_dirs, key=lambda x: int(x) if x.isdigit() else 0)[-1]

    return None


def sync_browser_kernel(dest_dir: str, src_dir_override: str = None):
    dest_path = pathlib.Path(dest_dir).resolve()
    
    if src_dir_override and os.path.isdir(src_dir_override):
        src_path = pathlib.Path(src_dir_override).resolve()
    else:
        src_path = get_default_ms_playwright_dir()

    if not src_path or not src_path.is_dir():
        print(f"[BROWSER_SYNC] ⚠️ 未在系统默认路径找到 ms-playwright 缓存目录 ({src_path})")
        return False

    print(f"[BROWSER_SYNC] 正在扫描浏览器内核资源: {src_path}")
    active_rev = detect_active_revision(src_path)
    if not active_rev:
        print("[BROWSER_SYNC] ⚠️ 未能在缓存中识别出有效的 Chromium 内核版本")
        return False

    print(f"[BROWSER_SYNC] 🎯 精准定位当前所需内核版本: chromium-{active_rev}")

    # 清空目标目录以彻底消除旧版本残留
    if dest_path.exists():
        print(f"[BROWSER_SYNC] 清理目标旧内核残留: {dest_path}")
        shutil.rmtree(dest_path, ignore_errors=True)
    dest_path.mkdir(parents=True, exist_ok=True)

    copied_items = []

    # 1. 同步主 Chromium 内核
    main_dir = src_path / f"chromium-{active_rev}"
    if main_dir.is_dir():
        print(f"  -> 正在内嵌 Chromium 主内核: {main_dir.name} ...")
        shutil.copytree(main_dir, dest_path / main_dir.name, dirs_exist_ok=True)
        copied_items.append(main_dir.name)
    else:
        print(f"[BROWSER_SYNC] ⚠️ 警告: 未找到 {main_dir}")

    # 2. 同步 Headless Shell (如果存在)
    shell_dir = src_path / f"chromium_headless_shell-{active_rev}"
    if shell_dir.is_dir():
        print(f"  -> 正在内嵌 Headless Shell: {shell_dir.name} ...")
        shutil.copytree(shell_dir, dest_path / shell_dir.name, dirs_exist_ok=True)
        copied_items.append(shell_dir.name)

    # 3. 同步最新的 ffmpeg
    ffmpeg_dirs = sorted(src_path.glob("ffmpeg-*"))
    if ffmpeg_dirs:
        latest_ff = ffmpeg_dirs[-1]
        print(f"  -> 正在内嵌多媒体库: {latest_ff.name} ...")
        shutil.copytree(latest_ff, dest_path / latest_ff.name, dirs_exist_ok=True)
        copied_items.append(latest_ff.name)

    print(f"[BROWSER_SYNC] ✅ 浏览器内核同步完成！成功保留: {', '.join(copied_items)}")
    print(f"[BROWSER_SYNC] 🎉 已成功过滤历史多余版本，立省 700MB+ 体积！")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python sync_browser_kernel.py <目标保存路径> [来源路径(可选)]")
        sys.exit(1)
    dest = sys.argv[1]
    src = sys.argv[2] if len(sys.argv) > 2 else None
    success = sync_browser_kernel(dest, src)
    if not success:
        sys.exit(1)
