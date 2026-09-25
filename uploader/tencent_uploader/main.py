# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import base64
import inspect
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from patchright.async_api import Page
from patchright.async_api import Playwright
from patchright.async_api import async_playwright

from conf import BASE_DIR, DEBUG_MODE, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from utils.base_social_media import set_init_script
from utils.log import tencent_logger

TENCENT_LOGIN_URL = "https://channels.weixin.qq.com"
TENCENT_HOME_URL = "https://channels.weixin.qq.com/platform"
TENCENT_UPLOAD_URL = "https://channels.weixin.qq.com/platform/post/create"
TENCENT_MANAGE_URL = "https://channels.weixin.qq.com/platform/post/list"
TENCENT_PUBLISH_STRATEGY_IMMEDIATE = "immediate"
TENCENT_PUBLISH_STRATEGY_SCHEDULED = "scheduled"


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


def _resolve_account_file(account_file: str | Path) -> str:
    path = Path(account_file).expanduser()
    if path.is_absolute():
        return str(path)

    target_in_root_cookies = Path(BASE_DIR) / "cookies" / path.name
    if target_in_root_cookies.exists():
        return str(target_in_root_cookies.resolve())

    if path.parts and path.parts[0] == "cookies":
        return str((Path(BASE_DIR) / path).resolve())

    if len(path.parts) == 1:
        return str(target_in_root_cookies.resolve())

    return str(path.resolve())


async def _emit_qrcode_callback(qrcode_callback, payload: dict):
    if not qrcode_callback:
        return

    callback_result = qrcode_callback(payload)
    if inspect.isawaitable(callback_result):
        await callback_result


def _build_login_result(
    success: bool,
    status: str,
    message: str,
    account_file: str,
    qrcode: dict | None = None,
    current_url: str = "",
    nickname: str = "",
    finder_uid: str = "",
    account_name: str = "",
) -> dict:
    stem_name = Path(account_file).stem
    if stem_name.startswith("tencent_"):
        stem_name = stem_name[len("tencent_"):]
    return {
        "success": success,
        "status": status,
        "message": message,
        "account_file": str(account_file),
        "account_name": str(account_name or stem_name),
        "nickname": nickname,
        "finder_uid": finder_uid,
        "qrcode": qrcode,
        "current_url": current_url,
    }


async def _human_delay(min_sec: float = 0.8, max_sec: float = 2.2) -> float:
    """产生带有正态扰动的真实人类随机停留延迟，打破脚本固定间隔规律。"""
    import random
    delay = random.uniform(min_sec, max_sec)
    await asyncio.sleep(delay)
    return delay


async def _native_click(page, locator) -> bool:
    """对元素做"真实人类级"点击：
    1. 动态生成按钮区域内的随机偏心坐标 (避免固定落在 0.00 中心点)
    2. 物理鼠标移动
    3. 带有微幅随机时间差的物理点击与底层 Event 链
    """
    import random
    try:
        await locator.scroll_into_view_if_needed(timeout=5000)
    except Exception:
        pass
    try:
        box = await locator.bounding_box()
    except Exception:
        box = None
    if not box:
        try:
            await locator.click(timeout=8000)
            return True
        except Exception:
            return False

    offset_x = (random.random() - 0.5) * (box["width"] * 0.5)
    offset_y = (random.random() - 0.5) * (box["height"] * 0.5)
    x = box["x"] + box["width"] / 2 + offset_x
    y = box["y"] + box["height"] / 2 + offset_y

    try:
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.1, 0.3))
        await page.mouse.click(x, y)
        await asyncio.sleep(random.uniform(0.15, 0.35))
        await page.evaluate(
            """({x, y}) => {
                const el = document.elementFromPoint(x, y);
                if (!el) return;
                const opts = {bubbles:true,cancelable:true,composed:true,clientX:x,clientY:y,view:window,pointerId:1,pointerType:'mouse',isPrimary:true,button:0,buttons:1};
                for (const t of ['pointerover','pointerenter','pointerdown','mousedown','pointerup','mouseup','click']) {
                    const C = t.startsWith('pointer') ? PointerEvent : MouseEvent;
                    try { el.dispatchEvent(new C(t, opts)); } catch(e){ try{ el.dispatchEvent(new MouseEvent(t,opts)); }catch(_){} }
                }
            }""",
            {"x": x, "y": y},
        )
        return True
    except Exception:
        return False


def _build_launch_kwargs(headless: bool) -> dict:
    launch_kwargs = {"headless": headless}
    if LOCAL_CHROME_PATH:
        launch_kwargs["executable_path"] = LOCAL_CHROME_PATH
    else:
        launch_kwargs["channel"] = "chrome"
    return launch_kwargs


def _get_qrcode_utils():
    from utils.login_qrcode import build_login_qrcode_path
    from utils.login_qrcode import decode_qrcode_from_path
    from utils.login_qrcode import print_terminal_qrcode
    from utils.login_qrcode import remove_qrcode_file
    from utils.login_qrcode import save_data_url_image

    return {
        "build_login_qrcode_path": build_login_qrcode_path,
        "decode_qrcode_from_path": decode_qrcode_from_path,
        "print_terminal_qrcode": print_terminal_qrcode,
        "remove_qrcode_file": remove_qrcode_file,
        "save_data_url_image": save_data_url_image,
    }


def format_str_for_short_title(origin_title: str) -> str:
    if not origin_title:
        return ""
    allowed_special_chars = "《》“”:+?%° -_"
    filtered_chars = [char if char.isalnum() or char in allowed_special_chars else " " if char == "," else "" for char in origin_title]
    formatted_string = "".join(filtered_chars).strip()
    # 微信官方短标题最长 16 个字符
    if len(formatted_string) > 16:
        formatted_string = formatted_string[:16]
    return formatted_string



async def cookie_auth(account_file):
    account_file = _resolve_account_file(account_file)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=True))
        try:
            context = await browser.new_context(storage_state=account_file)
            context = await set_init_script(context)
            page = await context.new_page()
            await page.goto(TENCENT_UPLOAD_URL, wait_until="domcontentloaded")

            # cookie 失效时, 页面先停在 post/create, 随后由前端 JS 跳转到登录页;
            # 必须等待跳转完成再判断, 否则会误报"cookie 有效"
            try:
                await page.wait_for_url("**/login.html**", timeout=8000)
                tencent_logger.info(_msg("🥹", "cookie 已失效（页面跳转到登录页），得重新登录一下"))
                return False
            except Exception:
                pass  # 8 秒内未跳转, 大概率已登录

            # 双保险: 页面里出现微信扫码登录 iframe 也视为失效
            for fr in page.frames:
                if "open.weixin.qq.com/connect/qrconnect" in fr.url:
                    tencent_logger.info(_msg("🥹", "cookie 已失效（页面出现扫码登录框），得重新登录一下"))
                    return False

            tencent_logger.success(_msg("🥳", "cookie 有效"))
            return True
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"cookie 校验时出错，按失效处理: {exc}"))
            return False
        finally:
            await browser.close()


async def _extract_tencent_qrcode_src(page: Page) -> str:
    if hasattr(page, "frame_locator"):
        try:
            iframe_locator = page.frame_locator('[src*="login-for-iframe"]')
            qr_code_img = iframe_locator.locator('div#app img.qrcode').first
            await qr_code_img.wait_for(state="visible", timeout=8000)
            src = await qr_code_img.get_attribute("src")
            if src and src.startswith("data:image/"):
                return src
        except Exception:
            pass

    # 2026 新版登录页: 二维码在 open.weixin.qq.com/connect/qrconnect 的 iframe 里,
    # img.qrcode 的 src 是相对路径(如 /connect/qrcode/xxxx), 需要下载后转成 data URL
    for frame in page.frames:
        if "open.weixin.qq.com/connect/qrconnect" not in frame.url:
            continue
        try:
            qr_img = frame.locator("img.qrcode").first
            await qr_img.wait_for(state="attached", timeout=15000)
            src = None
            for _ in range(20):
                src = await qr_img.get_attribute("src")
                if src:
                    break
                await page.wait_for_timeout(500)
            if not src:
                continue
            if src.startswith("data:image/"):
                return src
            abs_url = urljoin(frame.url, src)
            resp = await page.context.request.get(abs_url)
            if resp.ok:
                body = await resp.body()
                content_type = resp.headers.get("content-type", "image/png").split(";")[0]
                return f"data:{content_type};base64,{base64.b64encode(body).decode()}"
        except Exception:
            continue

    selector_candidates = [
        "div.login-qrcode-wrap img.qrcode",
        "div.qrcode-wrap img.qrcode",
        "img.qrcode",
        'img[src^="data:image/"]',
    ]
    for selector in selector_candidates:
        qr_code_img = page.locator(selector).first
        try:
            if not await qr_code_img.count() or not await qr_code_img.is_visible():
                continue
            src = await qr_code_img.get_attribute("src")
            if src and src.startswith("data:image/"):
                return src
        except Exception:
            continue

    raise RuntimeError("未获取到视频号登录二维码地址")


async def _save_tencent_qrcode(page: Page, account_file: str, previous_qrcode_path: Path | None = None, qrcode_callback=None) -> dict:
    qrcode_utils = _get_qrcode_utils()
    qrcode_src = await _extract_tencent_qrcode_src(page)
    qrcode_path = qrcode_utils["save_data_url_image"](
        qrcode_src,
        qrcode_utils["build_login_qrcode_path"](account_file, suffix="tencent_login_qrcode"),
    )
    if previous_qrcode_path and previous_qrcode_path != qrcode_path:
        if qrcode_utils["remove_qrcode_file"](previous_qrcode_path):
            tencent_logger.info(_msg("🧹", f"临时二维码文件已清理: {previous_qrcode_path}"))

    tencent_logger.info(_msg("🖼️", f"二维码已经准备好啦，已保存到: {qrcode_path}"))
    qrcode_content = qrcode_utils["decode_qrcode_from_path"](qrcode_path)
    if qrcode_content:
        qrcode_utils["print_terminal_qrcode"](qrcode_content, qrcode_path, "微信")
    else:
        tencent_logger.warning(
            _msg(
                "😵",
                f"没能从二维码图片里解析出可打印内容，所以这次没法在终端重绘二维码；请直接打开 {qrcode_path} 扫码",
            )
        )

    qrcode_info = {
        "image_path": str(qrcode_path),
        "image_data_url": qrcode_src,
    }
    await _emit_qrcode_callback(qrcode_callback, qrcode_info)
    return qrcode_info


async def _is_tencent_login_completed(page: Page) -> bool:
    publish_markers = [
        page.locator('div:has-text("发表视频")').first,
        page.locator('button:has-text("发表")').first,
        page.locator('button:has-text("保存草稿")').first,
    ]
    for marker in publish_markers:
        try:
            if await marker.count() and await marker.is_visible():
                return True
        except Exception:
            continue

    if not (page.url.startswith(TENCENT_UPLOAD_URL) or page.url.startswith(TENCENT_MANAGE_URL)):
        return False

    login_markers = [
        page.locator("div.login-qrcode-wrap").first,
        page.locator("div.qrcode-wrap").first,
        page.locator("img.qrcode").first,
        page.locator('span:has-text("微信扫码登录 视频号助手")').first,
    ]
    for marker in login_markers:
        try:
            if await marker.count() and await marker.is_visible():
                return False
        except Exception:
            continue

    return True


async def _is_tencent_qrcode_expired(page: Page) -> bool:
    tip_selectors = [
        'div.mask.show p.refresh-tip:has-text("二维码已过期，点击刷新")',
        'div.mask.show p.refresh-tip:has-text("网络不可用，点击刷新")',
        'p.refresh-tip:has-text("二维码已过期，点击刷新")',
        'p.refresh-tip:has-text("网络不可用，点击刷新")',
    ]
    for selector in tip_selectors:
        tip = page.locator(selector).first
        try:
            if await tip.count() and await tip.is_visible():
                return True
        except Exception:
            continue
    return False


async def _is_tencent_qrcode_scanned(page: Page) -> bool:
    scanned_tips = [
        'div.qr-tip div:has-text("已扫码")',
        'div.qr-tip div:has-text("需在手机上进行确认")',
    ]
    for selector in scanned_tips:
        tip = page.locator(selector).first
        try:
            if await tip.count() and await tip.is_visible():
                return True
        except Exception:
            continue
    return False


async def _refresh_tencent_qrcode(page: Page) -> None:
    visible_refresh_selectors = [
        "div.login-qrcode-wrap div.mask.show div.refresh-wrap",
        "div.login-qrcode-wrap div.mask.show .refresh-wrap",
    ]
    for selector in visible_refresh_selectors:
        refresh_wrap = page.locator(selector).first
        try:
            if not await refresh_wrap.count() or not await refresh_wrap.is_visible():
                continue
            await refresh_wrap.click()
            return
        except Exception:
            continue

    tip_selectors = [
        'div.mask.show p.refresh-tip:has-text("二维码已过期，点击刷新")',
        'div.mask.show p.refresh-tip:has-text("网络不可用，点击刷新")',
        'p.refresh-tip:has-text("二维码已过期，点击刷新")',
        'p.refresh-tip:has-text("网络不可用，点击刷新")',
    ]
    for selector in tip_selectors:
        tip = page.locator(selector).first
        try:
            if not await tip.count() or not await tip.is_visible():
                continue
            refresh_wrap = tip.locator("xpath=ancestor::div[contains(@class, 'refresh-wrap')]").first
            if await refresh_wrap.count():
                await refresh_wrap.click()
            else:
                await tip.click()
            return
        except Exception:
            continue

    fallback_refresh = page.locator("div.login-qrcode-wrap div.refresh-wrap").first
    if await fallback_refresh.count():
        await fallback_refresh.click()
        return

    raise RuntimeError("未找到可点击的视频号二维码刷新区域")


async def _wait_for_tencent_login(
    page: Page,
    account_file: str,
    qrcode_info: dict | None,
    qrcode_callback=None,
    poll_interval: int = 3,
    max_checks: int = 100,
) -> dict:
    qrcode_path = Path(qrcode_info["image_path"]) if qrcode_info else None
    scanned_logged = False
    for _ in range(max_checks):
        if await _is_tencent_login_completed(page):
            tencent_logger.info(_msg("🥳", f"扫码成功，已经跳转到登录后页面: {page.url}"))
            return _build_login_result(True, "success", "视频号扫码登录成功", account_file, qrcode_info, page.url)

        if not scanned_logged and await _is_tencent_qrcode_scanned(page):
            tencent_logger.info(_msg("📱", "已经扫码啦，还差手机端确认一下"))
            scanned_logged = True

        if await _is_tencent_qrcode_expired(page):
            tencent_logger.warning(_msg("😵", "二维码失效了，小人马上去刷新"))
            await _refresh_tencent_qrcode(page)
            await asyncio.sleep(1)
            try:
                qrcode_info = await _save_tencent_qrcode(
                    page,
                    account_file,
                    previous_qrcode_path=qrcode_path,
                    qrcode_callback=qrcode_callback,
                )
                qrcode_path = Path(qrcode_info["image_path"])
            except Exception as exc:
                tencent_logger.warning(_msg("⚠️", f"刷新后未能重新提取二维码({exc})，请直接在浏览器窗口中扫码"))

        await asyncio.sleep(poll_interval)

    return _build_login_result(False, "timeout", "等待视频号扫码登录超时", account_file, qrcode_info, page.url)


async def tencent_cookie_gen(
    account_file,
    qrcode_callback=None,
    poll_interval: int = 3,
    max_checks: int = 100,
    headless: bool = LOCAL_CHROME_HEADLESS,
):
    account_file = _resolve_account_file(account_file)
    Path(account_file).parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=headless))
        context = await browser.new_context()
        qrcode_path = None
        result = _build_login_result(False, "failed", "视频号登录失败", account_file)
        try:
            page = await context.new_page()
            await page.goto(TENCENT_LOGIN_URL)
            try:
                qrcode_info = await _save_tencent_qrcode(page, account_file, qrcode_callback=qrcode_callback)
                qrcode_path = Path(qrcode_info["image_path"])
            except Exception as exc:
                tencent_logger.warning(
                    _msg("⚠️", f"提取二维码图片失败({exc})，请直接在弹出的浏览器窗口中扫码，登录流程不受影响")
                )
                qrcode_info = None
                qrcode_path = None
            tencent_logger.info(_msg("🧍", "请扫码，小人正在耐心等待登录完成"))
            result = await _wait_for_tencent_login(
                page,
                account_file,
                qrcode_info,
                qrcode_callback=qrcode_callback,
                poll_interval=poll_interval,
                max_checks=max_checks,
            )
            if result["success"]:
                await asyncio.sleep(2)
                
                # 尝试从页面中提取真实昵称与视频号 UID
                nickname = ""
                finder_uid = ""
                for _ in range(12):
                    try:
                        name_el = page.locator("h2.finder-nickname, div.side-bar-footer .account-info span.name").first
                        if await name_el.count() and await name_el.is_visible():
                            extracted_name = (await name_el.inner_text()).strip()
                            if extracted_name:
                                nickname = extracted_name
                                break
                    except Exception:
                        pass
                    await asyncio.sleep(0.5)

                try:
                    uid_el = page.locator("span.finder-uniq-id, #finder-uid-copy").first
                    if await uid_el.count():
                        finder_uid = (await uid_el.inner_text()).strip()
                except Exception:
                    pass

                # 如果传入的是 auto 或临时 account，且成功解析出 finder_uid，则自动决定安全文件名
                final_account_name = Path(account_file).stem.replace("tencent_", "")
                final_account_file = account_file
                if (final_account_name == "auto" or not final_account_name) and finder_uid:
                    final_account_name = finder_uid
                    final_account_file = str(Path(account_file).parent / f"tencent_{finder_uid}.json")

                # 保存 storage state
                await context.storage_state(path=final_account_file)
                if final_account_file != account_file and os.path.exists(account_file):
                    try:
                        os.remove(account_file)
                    except Exception:
                        pass

                # 注入元数据 __account_meta__，保留无损 Emoji 和真实昵称
                try:
                    import json
                    if os.path.exists(final_account_file):
                        with open(final_account_file, "r", encoding="utf-8") as f:
                            state_data = json.load(f)
                        state_data["__account_meta__"] = {
                            "nickname": nickname,
                            "finder_uid": finder_uid,
                            "account_name": final_account_name,
                            "platform": "tencent",
                            "updated_at": datetime.now().isoformat()
                        }
                        with open(final_account_file, "w", encoding="utf-8") as f:
                            json.dump(state_data, f, ensure_ascii=False, indent=2)
                except Exception as meta_err:
                    tencent_logger.warning(_msg("⚠️", f"元数据写入失败(不影响登录): {meta_err}"))

                if not await cookie_auth(final_account_file):
                    result = _build_login_result(
                        False,
                        "cookie_invalid",
                        "视频号扫码流程结束，但 cookie 校验失败",
                        final_account_file,
                        qrcode_info,
                        page.url,
                        nickname=nickname,
                        finder_uid=finder_uid,
                        account_name=final_account_name,
                    )
                else:
                    result = _build_login_result(
                        True,
                        "success",
                        f"视频号扫码登录成功 (昵称: {nickname or final_account_name})",
                        final_account_file,
                        qrcode_info,
                        page.url,
                        nickname=nickname,
                        finder_uid=finder_uid,
                        account_name=final_account_name,
                    )
                    tencent_logger.success(_msg("🎉", f"登录成功！识别到视频号账号: {nickname or final_account_name} (ID: {finder_uid})"))
            return result
        except Exception as exc:
            result = _build_login_result(
                False,
                "failed",
                str(exc),
                account_file,
                current_url=page.url if "page" in locals() else "",
            )
            return result
        finally:
            qrcode_utils = _get_qrcode_utils()
            if qrcode_utils["remove_qrcode_file"](qrcode_path):
                tencent_logger.info(_msg("🧹", f"临时二维码文件已清理: {qrcode_path}"))
            if not result["success"]:
                tencent_logger.error(_msg("😢", f"登录失败: {result['message']}"))
            await context.close()
            await browser.close()


async def tencent_setup(
    account_file,
    handle=False,
    return_detail=False,
    qrcode_callback=None,
    headless: bool = LOCAL_CHROME_HEADLESS,
):
    account_file = _resolve_account_file(account_file)
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "cookie文件不存在或已失效", account_file)
            return result if return_detail else False

        tencent_logger.info(_msg("🥹", "cookie 失效了，准备打开浏览器重新登录"))
        result = await tencent_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless)
        return result if return_detail else result["success"]

    result = _build_login_result(True, "cookie_valid", "cookie有效", account_file)
    return result if return_detail else True


async def get_tencent_cookie(account_file, qrcode_callback=None, headless: bool = LOCAL_CHROME_HEADLESS):
    return await tencent_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless)


async def weixin_setup(
    account_file,
    handle=False,
    return_detail=False,
    qrcode_callback=None,
    headless: bool = LOCAL_CHROME_HEADLESS,
):
    return await tencent_setup(
        account_file,
        handle=handle,
        return_detail=return_detail,
        qrcode_callback=qrcode_callback,
        headless=headless,
    )


class TencentBaseUploader(BaseVideoUploader):
    def __init__(
        self,
        publish_date: datetime | int,
        account_file,
        publish_strategy: str = TENCENT_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
        collection_name: str | None = None,
    ):
        self.publish_date = publish_date
        self.account_file = _resolve_account_file(account_file)
        self.publish_strategy = publish_strategy
        self.debug = debug
        self.headless = headless
        self.collection_name = collection_name
        self.local_executable_path = LOCAL_CHROME_PATH

    async def validate_base_args(self):
        if not os.path.exists(self.account_file):
            raise RuntimeError(f"cookie文件不存在，请先完成视频号登录: {self.account_file}")
        if not await cookie_auth(self.account_file):
            raise RuntimeError(f"cookie文件已失效，请先完成视频号登录: {self.account_file}")
        if self.publish_strategy not in {TENCENT_PUBLISH_STRATEGY_IMMEDIATE, TENCENT_PUBLISH_STRATEGY_SCHEDULED}:
            raise ValueError(f"不支持的发布策略: {self.publish_strategy}")

        if self.publish_strategy == TENCENT_PUBLISH_STRATEGY_SCHEDULED:
            self.publish_date = self.validate_publish_date(self.publish_date)
        else:
            self.publish_date = 0

    async def wait_for_realtime_verification(
        self,
        page: Page,
        qr_path: str | Path | None = None,
        timeout_seconds: float = 10 * 60,
        poll_interval_seconds: float = 2,
    ) -> Path | None:
        dialog = page.locator("div.weui-desktop-dialog__wrp:visible").filter(has_text="实名验证").first
        if not await dialog.count() or not await dialog.is_visible():
            return None

        output_path = Path(qr_path) if qr_path else Path(self.account_file).with_name(
            f"{Path(self.account_file).stem}_verification_qr.png"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        await dialog.screenshot(path=str(output_path))
        tencent_logger.warning(_msg("📱", f"需要管理员微信扫码完成实名验证: {output_path}"))

        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while await dialog.count() and await dialog.is_visible():
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError("等待视频号管理员实名验证超时")
            await asyncio.sleep(poll_interval_seconds)

        tencent_logger.success(_msg("🥳", "管理员实名验证已完成，继续发表"))
        return output_path

    async def set_schedule_time_tencent(self, page: Page, publish_date: datetime):
        label_element = page.locator("label").filter(has_text="定时").nth(1)
        await label_element.click()
        await page.click('input[placeholder="请选择发表时间"]')

        current_month = publish_date.strftime("%m月")
        page_month = await page.inner_text('span.weui-desktop-picker__panel__label:has-text("月")')
        if page_month != current_month:
            await page.click("button.weui-desktop-btn__icon__right")

        elements = await page.query_selector_all("table.weui-desktop-picker__table a")
        for element in elements:
            if "weui-desktop-picker__disabled" in await element.evaluate("el => el.className"):
                continue
            text = await element.inner_text()
            if text.strip() == str(publish_date.day):
                await element.click()
                break

        await page.click('input[placeholder="请选择时间"]')
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(publish_date.strftime("%H"))
        await page.keyboard.press("Enter")  # 确认小时并关闭时间下拉
        await page.wait_for_timeout(500)
        # 收起时间选择浮层：直接点描述区可能被 weui-desktop-dialog 遮挡，做容错
        try:
            await page.locator("div.input-editor").click(timeout=5000)
        except Exception:
            await page.keyboard.press("Escape")

    async def open_upload_page(self, page: Page) -> None:
        # 视频号已改版：直接全页加载 /platform/post/create 会被跳回 /platform 首页，
        # 发布表单 iframe 只加载空壳（Vue 不挂载），页面上没有任何 input[type=file]。
        # 正确入口：先进首页，再点可见的「发表视频」按钮做客户端跳转，表单才会真正挂载。
        await page.goto(TENCENT_HOME_URL, timeout=120000, wait_until="domcontentloaded")
        # cookie 失效时前端 JS 会跳转到登录页, 提前发现并报明确的错误
        try:
            await page.wait_for_url("**/login.html**", timeout=8000)
            raise RuntimeError("视频号 cookie 已失效（被跳转到登录页），请重新扫码登录后再发布")
        except TimeoutError:
            pass  # 8 秒内未跳转, 正常
        except RuntimeError:
            raise
        except Exception:
            pass
        if any("open.weixin.qq.com/connect/qrconnect" in fr.url for fr in page.frames):
            raise RuntimeError("视频号 cookie 已失效（被跳转到登录页），请重新扫码登录后再发布")
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        # 注意：get_by_text("发表视频") 会命中一个隐藏的说明 <p>（不可点）；
        # 首页真正可点的入口是 button.weui-desktop-btn。
        publish_entry = page.locator("button.weui-desktop-btn", has_text="发表视频").first
        try:
            await publish_entry.wait_for(state="visible", timeout=30000)
            await publish_entry.click()
        except Exception:
            # 兜底：按钮没点到时退回老逻辑直接跳转（可能仍是空壳，但保持向后兼容）
            await page.goto(TENCENT_UPLOAD_URL, timeout=120000, wait_until="domcontentloaded")
        try:
            await page.wait_for_url("**/platform/post/create", timeout=120000)
        except Exception:
            pass

        # 上传表单在 micro/content/post/create 这个 iframe 里，domcontentloaded 时它还是空的。
        # 不等网络静默就去找 input[type=file]，会误报「未找到视频号文件上传框」——
        # 失败截图上左栏渲染正常、主内容区一片空白，看起来完全不像加载没完成。
        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            pass  # 静默不了就算了，下面还有重试兜底

    async def upload_video_file(self, page: Page, file_path: str) -> None:
        async def find_file_input():
            for fr in page.frames:  # 主 frame + 所有 iframe（视频号编辑器可能在 iframe 内）
                try:
                    fi = fr.locator('input[type="file"]')
                    if await fi.count():
                        return fi.first
                except Exception:
                    continue
            return None

        fi = await find_file_input()
        clicked_publish = False
        for _ in range(60):
            if fi is not None:
                break
            if not clicked_publish:
                # 新版视频号助手可能先落在首页，且「发表视频」按钮异步出现。
                # 持续轮询所有可访问 button；Patchright 在当前页面上按名称精确匹配不稳定。
                try:
                    publish_buttons = await page.get_by_role("button").all()
                except Exception:
                    publish_buttons = []
                for candidate in publish_buttons:
                    try:
                        button_text = (await candidate.inner_text()).strip()
                        is_visible = await candidate.is_visible()
                    except Exception:
                        continue
                    if "发表视频" in button_text and is_visible:
                        await candidate.click(force=True)
                        clicked_publish = True
                        break
            fi = await find_file_input()
            if fi is None:
                await asyncio.sleep(1)
        if fi is None:
            # 留现场：这个错误的可能原因太多（没登录 / 落到首页 / iframe 没加载完 /
            # 平台改版），只看错误字符串没法区分，截图能一眼看出是哪种。
            try:
                shot = Path(BASE_DIR) / "debug_tencent_no_file_input.png"
                await page.screenshot(path=str(shot), full_page=True)
                tencent_logger.info(_msg(
                    "📸",
                    f"失败现场已截图 {shot}; url={page.url}; "
                    f"frames={[fr.url[:80] for fr in page.frames]}",
                ))
            except Exception:
                pass
            raise RuntimeError("未找到视频号文件上传框")
        await fi.set_input_files(file_path)

    async def _get_content_target(self, page: Page, wait_seconds: float = 8.0):
        """动态探测真正包含微信视频号发布表单的 Frame 或 Page，坚决排除空壳 empty.html"""
        deadline = time.monotonic() + wait_seconds
        while True:
            # 0. 优先按 frame 名称匹配 content
            fr_content = page.frame(name="content")
            if fr_content and "empty.html" not in fr_content.url:
                try:
                    if await fr_content.locator("div.input-editor, .post-position-wrap, input, button").count() > 0:
                        return fr_content
                except Exception:
                    pass

            # 1. 遍历所有 frame，优先寻找真正包含 input-editor 或其它表单特征的活跃 frame
            for fr in page.frames:
                if "empty.html" in fr.url:
                    continue
                try:
                    if await fr.locator("div.input-editor, .post-position-wrap, input[placeholder*='短标题']").count() > 0:
                        return fr
                except Exception:
                    continue

            # 2. 检查主 page 是否直接包含编辑器或表单
            try:
                if await page.locator("div.input-editor, .post-position-wrap, input[placeholder*='短标题']").count() > 0:
                    return page
            except Exception:
                pass

            # 3. 寻找微前端容器 frame
            for fr in page.frames:
                if "empty.html" in fr.url:
                    continue
                if any(k in fr.url for k in ("post/create", "micro/content", "channels")):
                    try:
                        if await fr.locator("input, button, textarea").count() > 0:
                            return fr
                    except Exception:
                        continue

            if time.monotonic() >= deadline:
                break
            await asyncio.sleep(0.5)

        return page

    async def _find_first_locator(self, page: Page, selector: str):
        """双保险定位器：同时在目标 frame、主页面以及所有活跃 frame 探测首个匹配的 locator"""
        target = await self._get_content_target(page, wait_seconds=1.0)
        try:
            loc = target.locator(selector).first
            if await loc.count() > 0:
                return loc
        except Exception:
            pass
        # 遍历所有非 empty 的 frame
        for fr in page.frames:
            if "empty.html" in fr.url:
                continue
            try:
                loc = fr.locator(selector).first
                if await loc.count() > 0:
                    return loc
            except Exception:
                continue
        # 最后看主页面
        try:
            loc = page.locator(selector).first
            if await loc.count() > 0:
                return loc
        except Exception:
            pass
        return target.locator(selector).first

    async def set_short_title(self, page: Page, title: str, short_title: str | None = None) -> None:
        # 仅当用户明确配置了短标题时才填写；未填则严格留空，绝不拿主标题滥充
        if not short_title or not str(short_title).strip():
            tencent_logger.info(_msg("🧾", "未设置短标题，保持默认留空"))
            return

        value = format_str_for_short_title(str(short_title).strip())
        if not value:
            return

        field = await self._find_first_locator(page, 'input[placeholder="填写短标题有机会获得更多流量"]')
        if not await field.count():
            target = await self._get_content_target(page)
            field = (
                target.get_by_text("短标题", exact=True)
                .locator("..")
                .locator("xpath=following-sibling::div")
                .locator('span input[type="text"]')
            )
        if await field.count():
            await field.fill(value)
            tencent_logger.success(_msg("🏷️", f"短标题已填写：{value}"))
        else:
            tencent_logger.info(_msg("🧾", "未找到短标题输入框，跳过短标题"))
        await page.wait_for_timeout(600)

    async def _dismiss_switch_account_dialog(self, page: Page) -> None:
        cancel = page.locator('.changeAccount-dialog button:has-text("取消")').first
        closeb = page.locator('.changeAccount-dialog .weui-desktop-dialog__close-btn').first
        for cand in (cancel, closeb):
            try:
                if await cand.count() and await cand.is_visible():
                    await cand.click(timeout=2000)
                    await page.wait_for_timeout(600)
                    return
            except Exception:
                continue
        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(600)
        except Exception:
            pass

    async def fill_editor_content(self, page: Page) -> None:
        """填写视频描述与话题：一次性安全注入，杜绝逐字敲击 # 触发推荐浮层导致的焦点乱跳与滚动"""
        content_parts = []
        if self.desc and str(self.desc).strip():
            content_parts.append(str(self.desc).strip())
        elif self.title and str(self.title).strip():
            content_parts.append(str(self.title).strip())

        if self.tags:
            current_all = " ".join(content_parts)
            missing_tags = [f"#{t.lstrip('#')}" for t in self.tags if f"#{t.lstrip('#')}" not in current_all]
            if missing_tags:
                content_parts.append(" ".join(missing_tags))

        final_text = " ".join(content_parts).strip()
        if not final_text:
            return

        editor = None
        for _ in range(12):
            cand = await self._find_first_locator(page, "div.input-editor, div[contenteditable='true'].input-editor")
            try:
                if await cand.count() > 0:
                    await cand.wait_for(state="visible", timeout=3000)
                    await cand.click()
                    editor = cand
                    break
            except Exception:
                pass
            await self._dismiss_switch_account_dialog(page)
            await page.wait_for_timeout(800)

        if not editor or await editor.count() == 0:
            tencent_logger.warning(_msg("😵", "未找到视频描述输入框，跳过描述输入"))
            return

        try:
            # 通过 execCommand 一次性注入文本，杜绝 # 键盘联想浮层与光标乱跳
            await editor.evaluate(
                """(el, text) => {
                    el.focus();
                    document.execCommand('selectAll', false, null);
                    document.execCommand('delete', false, null);
                    document.execCommand('insertText', false, text);
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                }""",
                final_text,
                timeout=5000,
            )
            tencent_logger.success(_msg("📝", f"视频描述与话题已填入（{len(final_text)}字）"))
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"通过命令注入描述失败，尝试直接输入: {exc}"))
            try:
                await editor.fill(final_text, timeout=5000)
            except Exception:
                pass
        await page.wait_for_timeout(800)

    # 保留旧方法签名以保持兼容
    async def fill_title_and_tags(self, page: Page) -> None:
        await self.fill_editor_content(page)

    async def fill_description(self, page: Page) -> None:
        pass

    async def apply_location(self, page: Page) -> None:
        """设置发布位置：支持 auto(按平台定位) 与 none(不显示位置)"""
        loc = getattr(self, "location", None)
        if not loc or loc in ("auto", "平台定位", "按平台定位"):
            tencent_logger.info(_msg("📍", "位置设置为：按平台默认定位"))
            return

        if loc in ("none", "不显示位置", "0"):
            try:
                # 1. 定位并点击位置下拉框（div.position-display-wrap 或 .post-position-wrap .position-display）
                trigger = await self._find_first_locator(
                    page,
                    "div.position-display-wrap, .post-position-wrap .position-display, .post-position-wrap .position-display-wrap, .post-position-wrap"
                )
                if await trigger.count() == 0:
                    tencent_logger.info(_msg("🧾", "未找到位置设置入口，跳过"))
                    return
                try:
                    await trigger.scroll_into_view_if_needed(timeout=3000)
                    await trigger.click(timeout=4000)
                except Exception:
                    await trigger.evaluate("el => el.click()")
                await page.wait_for_timeout(800)

                # 2. 定位"不显示位置"选项（微信定位列表结构为 div.location-item）
                frames_to_search = [await self._get_content_target(page), page] + [f for f in page.frames if "empty.html" not in f.url]
                not_display = None
                for ctx in frames_to_search:
                    cand = ctx.locator("div.location-item").filter(has_text="不显示位置").first
                    if await cand.count() > 0:
                        not_display = cand
                        break
                    cand2 = ctx.locator(".location-filter-wrap .not-display, .location-item, .not-display").filter(has_text="不显示位置").first
                    if await cand2.count() > 0:
                        not_display = cand2
                        break
                    cand3 = ctx.get_by_text("不显示位置", exact=True).first
                    if await cand3.count() > 0:
                        not_display = cand3
                        break

                if not_display and await not_display.count() > 0:
                    try:
                        await not_display.scroll_into_view_if_needed(timeout=3000)
                        await not_display.click(timeout=3000)
                    except Exception:
                        await not_display.evaluate("el => el.click()")
                    await page.wait_for_timeout(600)
                    tencent_logger.success(_msg("📍", "位置已选择：不显示位置"))
                else:
                    tencent_logger.warning(_msg("😵", "未找到「不显示位置」选项，保持默认"))
            except Exception as exc:
                tencent_logger.warning(_msg("😵", f"设置「不显示位置」失败，跳过: {exc}"))
                try:
                    await page.keyboard.press("Escape")
                except Exception:
                    pass
        await page.wait_for_timeout(600)

    async def apply_collection(self, page: Page) -> None:
        """在发布表单页"添加到合集"下拉框按合集名精确选中"""
        if not self.collection_name:
            return
        try:
            trigger = await self._find_first_locator(page, "text=添加到合集")
            if await trigger.count() == 0:
                tencent_logger.info(_msg("🧾", "当前页面未发现「添加到合集」入口，跳过归集"))
                return
            dropdown = trigger.locator("xpath=following-sibling::div").first
            await dropdown.click(timeout=8000)
            await page.wait_for_timeout(800)

            target = await self._get_content_target(page)
            option = dropdown.locator(".option-list-wrap .option-item").filter(
                has=target.locator(f'.name:text-is("{self.collection_name}")')
            )
            if await option.count() == 0:
                tencent_logger.warning(
                    _msg("😵", f"合集下拉框未找到「{self.collection_name}」，跳过归集，保持未选状态")
                )
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(300)
                return

            tgt = option.first
            try:
                await tgt.scroll_into_view_if_needed(timeout=3000)
            except Exception:
                pass
            try:
                await tgt.click(timeout=4000)
            except Exception:
                await tgt.dispatch_event("click")
            await page.wait_for_timeout(500)
            tencent_logger.success(_msg("🥳", f"已选择合集：{self.collection_name}"))
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"选择合集失败，跳过归集继续发布: {exc}"))
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
        await page.wait_for_timeout(600)

    async def apply_link(self, page: Page) -> None:
        """设置关联链接：支持 公众号文章 / 红包封面 / 视频号剧集 / 小程序短剧"""
        link_type = getattr(self, "link_type", None)
        if not link_type or link_type in ("none", "不添加", "0", ""):
            tencent_logger.info(_msg("🔗", "未添加关联链接"))
            return

        type_map = {
            "article": "公众号文章",
            "redpacket": "红包封面",
            "series": "视频号剧集",
            "minidrama": "小程序短剧"
        }
        target_name = type_map.get(link_type, link_type)
        try:
            # 1. 点击展开链接类型下拉（参考 wxauto: div.link-display-wrap）
            wrap = await self._find_first_locator(
                page,
                "div.link-display-wrap, .post-with-link .link-display-wrap, .post-link-wrap .link-display-wrap, .post-link-wrap"
            )
            if await wrap.count() == 0:
                tencent_logger.info(_msg("🧾", "未找到链接设置入口，跳过"))
                return
            try:
                await wrap.scroll_into_view_if_needed(timeout=3000)
                await wrap.click(timeout=4000)
            except Exception:
                await wrap.evaluate("el => el.click()")
            await page.wait_for_timeout(600)

            # 2. 选中对应类型（参考 wxauto: div.link-list-options get_by_text(target_name)）
            frames_to_search = [await self._get_content_target(page), page] + [f for f in page.frames if "empty.html" not in f.url]
            target_opt = None
            for ctx in frames_to_search:
                opt = ctx.locator("div.link-list-options .link-option-item, div.link-option-item").filter(has_text=target_name).first
                if await opt.count() > 0:
                    target_opt = opt
                    break
                opt2 = ctx.get_by_text(target_name, exact=True).first
                if await opt2.count() > 0:
                    target_opt = opt2
                    break

            if target_opt and await target_opt.count() > 0:
                try:
                    await target_opt.click(timeout=4000)
                except Exception:
                    await target_opt.evaluate("el => el.click()")
                await page.wait_for_timeout(600)
                tencent_logger.info(_msg("🔗", f"已选择链接类型：{target_name}"))
            else:
                tencent_logger.warning(_msg("😵", f"未找到链接类型「{target_name}」选项，跳过"))
                await page.keyboard.press("Escape")
                return

            # 3. 填入具体 URL 或在弹窗内选择剧集/短剧
            link_url = getattr(self, "link_url", None)
            link_title = getattr(self, "link_title", None)

            if link_type in ("article", "redpacket") and link_url:
                input_field = await self._find_first_locator(page, ".link-input-wrap input.weui-desktop-form__input, .link-input-wrap input")
                if await input_field.count() > 0:
                    await input_field.fill(link_url)
                    await page.wait_for_timeout(500)
                    tencent_logger.success(_msg("🔗", f"已填入链接地址：{link_url}"))
            elif link_type in ("series", "minidrama") and link_title:
                # 点击进入剧集/短剧弹窗选择器
                choose_box = await self._find_first_locator(
                    page,
                    "div.link-input-wrap div.post-component-choose-wrap, div.post-component-choose-wrap, .link-input-wrap"
                )
                if await choose_box.count() > 0:
                    try:
                        await choose_box.scroll_into_view_if_needed(timeout=3000)
                        await choose_box.click(timeout=4000)
                    except Exception:
                        await choose_box.evaluate("el => el.click()")
                    await page.wait_for_timeout(1000)

                    # 在弹窗内寻找真实可见的搜索输入框（规避宽度为0的隐藏搜索框引发的30秒evaluate超时）
                    search_inp = None
                    for ctx in frames_to_search:
                        cands = ctx.locator("input[placeholder='搜索内容'], input[placeholder*='搜索内容'], input[placeholder*='搜索']")
                        try:
                            cnt = await cands.count()
                            for i in range(cnt):
                                it = cands.nth(i)
                                if await it.is_visible():
                                    box = await it.bounding_box()
                                    if box and box["width"] > 20 and box["height"] > 20:
                                        search_inp = it
                                        break
                        except Exception:
                            pass
                        if search_inp:
                            break

                    if search_inp:
                        try:
                            await search_inp.click(timeout=3000)
                            await search_inp.fill(link_title)
                            await search_inp.press("Enter")
                        except Exception:
                            import json as _json
                            await search_inp.evaluate(f"el => {{ el.value = {_json.dumps(link_title)}; el.dispatchEvent(new Event('input', {{bubbles: true}})); }}")
                        tencent_logger.info(_msg("🔍", f"正在搜索{target_name}「{link_title}」，等待列表渲染..."))
                        await page.wait_for_timeout(2000)
                    else:
                        tencent_logger.warning(_msg("⚠️", f"未找到可见的搜索框，尝试直接在列表中匹配{target_name}"))

                    # 动态轮询寻找匹配行（微信弹窗使用 tr.drama-row / tr.ant-table-row，最多等待 6 秒适应网络延迟）
                    row_loc = None
                    poll_deadline = time.monotonic() + 6.0
                    while time.monotonic() < poll_deadline:
                        for ctx in frames_to_search:
                            cands = ctx.locator("tr.drama-row, tr.ant-table-row, div.drama-table-wrap tr").filter(has_text=link_title)
                            if await cands.count() > 0:
                                row_loc = cands.first
                                break
                        if row_loc:
                            break
                        await asyncio.sleep(0.5)

                    if not row_loc:
                        for ctx in frames_to_search:
                            cands = ctx.locator("tr.drama-row, tr.ant-table-row, div.drama-table-wrap tbody tr")
                            if await cands.count() > 0:
                                row_loc = cands.first
                                break

                    if row_loc and await row_loc.count() > 0:
                        try:
                            await row_loc.scroll_into_view_if_needed(timeout=3000)
                            cell = row_loc.locator("td").first
                            if await cell.count() > 0:
                                await cell.click(timeout=3000)
                            else:
                                await row_loc.click(timeout=3000)
                        except Exception:
                            await row_loc.evaluate("el => el.click()")
                        await page.wait_for_timeout(1000)

                        # 检查是否有确定按钮需点击（如果微信弹窗未自动关闭）
                        for ctx in frames_to_search:
                            btn = ctx.locator('div.weui-desktop-dialog button.weui-desktop-btn_primary, button:has-text("确定"), button:has-text("确认")').first
                            if await btn.count() and await btn.is_visible():
                                try:
                                    await btn.click(timeout=2000)
                                except Exception:
                                    pass
                                break
                        await page.wait_for_timeout(800)
                        tencent_logger.success(_msg("🔗", f"已关联{target_name}：{link_title}"))
                    else:
                        tencent_logger.warning(_msg("😵", f"弹窗内未搜索到匹配的{target_name}「{link_title}」，跳过"))
                        try:
                            await page.keyboard.press("Escape")
                        except Exception:
                            pass
                else:
                    tencent_logger.warning(_msg("😵", f"未找到{target_name}选择按钮，跳过"))
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"设置链接「{target_name}」失败，跳过: {exc}"))
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
        await page.wait_for_timeout(600)

    async def apply_activity(self, page: Page) -> None:
        """设置参与活动：支持搜索指定活动名称并单次精准勾选"""
        act_name = getattr(self, "activity_name", None)
        if not act_name or not str(act_name).strip() or str(act_name).strip() in ("none", "不参与", "不参与活动", "0"):
            tencent_logger.info(_msg("🎯", "未参与特定活动（保持不参与活动）"))
            return

        act_name = str(act_name).strip()
        try:
            display_wrap = await self._find_first_locator(
                page,
                "div.activity-display-wrap, .post-activity-wrap .activity-display, .post-activity-wrap"
            )
            if await display_wrap.count() == 0:
                tencent_logger.info(_msg("🧾", "未找到活动设置入口，跳过"))
                return
            try:
                await display_wrap.scroll_into_view_if_needed(timeout=3000)
                await display_wrap.click(timeout=4000)
            except Exception:
                await display_wrap.evaluate("el => el.click()")
            await page.wait_for_timeout(600)

            # 在搜索框中输入活动名（规避不可见元素）
            frames_to_search = [await self._get_content_target(page), page] + [f for f in page.frames if "empty.html" not in f.url]
            search_input = None
            for ctx in frames_to_search:
                cands = ctx.locator("input[placeholder*='搜索活动'], input[placeholder='搜索活动'], .activity-filter-wrap input")
                try:
                    cnt = await cands.count()
                    for i in range(cnt):
                        it = cands.nth(i)
                        if await it.is_visible():
                            search_input = it
                            break
                except Exception:
                    pass
                if search_input:
                    break

            if search_input and await search_input.count() > 0:
                await search_input.scroll_into_view_if_needed()
                await search_input.click(timeout=3000)
                await search_input.fill(act_name)
                await search_input.press("Enter")
                # 活动搜索需要异步接口返回，给予充分的初始网络响应与渲染缓冲
                tencent_logger.info(_msg("🔍", f"正在搜索活动「{act_name}」，等待搜索结果渲染..."))
                await page.wait_for_timeout(2000)
            else:
                tencent_logger.warning(_msg("⚠️", "未找到活动搜索框，尝试直接在候选列表中匹配"))

            # 动态轮询查找匹配的活动列表项（最多等待 6 秒，每 500ms 检查一次，适应网络波动）
            res_item = None
            poll_deadline = time.monotonic() + 6.0
            while time.monotonic() < poll_deadline:
                for ctx in frames_to_search:
                    cands = ctx.locator("div.activity-item").filter(has_text=act_name)
                    if await cands.count() > 0:
                        res_item = cands.first
                        break
                if res_item:
                    break
                for ctx in frames_to_search:
                    cands = ctx.locator(".activity-filter-wrap .activity-item, .activity-filter-wrap li").filter(has_text=act_name)
                    if await cands.count() > 0:
                        res_item = cands.first
                        break
                if res_item:
                    break
                await asyncio.sleep(0.5)

            # 若完全匹配未找到，退化寻找首个活动项
            if not res_item:
                for ctx in frames_to_search:
                    cands = ctx.locator("div.activity-item")
                    if await cands.count() > 0:
                        res_item = cands.first
                        break

            if res_item and await res_item.count() > 0:
                # 微信核心逻辑：仅需单次点击 div.activity-item，Vue 即可捕获选中、展现 yes-icon 并自动收起下拉框
                # 绝不可二次派发 change 或再次点击，否则会反选取消！
                await page.wait_for_timeout(500)
                try:
                    await res_item.scroll_into_view_if_needed(timeout=3000)
                    await res_item.click(timeout=3000)
                except Exception:
                    await res_item.evaluate("el => el.click()")
                await page.wait_for_timeout(1000)
                tencent_logger.success(_msg("🎯", f"已选择参与活动：{act_name}"))
            else:
                tencent_logger.warning(_msg("😵", f"未搜索到匹配活动「{act_name}」，跳过"))
                try:
                    await page.keyboard.press("Escape")
                except Exception:
                    pass
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"设置活动「{act_name}」失败，跳过: {exc}"))
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
        await page.wait_for_timeout(600)

    async def apply_original_statement(self, page: Page) -> None:
        # 视频号「视频标注」下拉：对齐官方标准标注选项
        label_text = getattr(self, "content_label", None)
        if not label_text or label_text in ("无需标注", "none", "0", ""):
            tencent_logger.info(_msg("🧾", "未指定视频标注或选择无需标注，跳过视频标注"))
            return
        # 只接受视频号官方标注文案；其他值（如历史遗留的 '1'）一律跳过，
        # 避免「按文本查找」退化为全页搜索而误点页面其他元素
        valid_labels = {
            "含AI生成内容",
            "内容为虚构剧情，仅供娱乐",
            "个人观点，仅供参考",
            "内容包含营销广告",
            "内容为自行拍摄",
            "内容为转载",
        }
        if label_text not in valid_labels:
            tencent_logger.info(_msg("🧾", f"视频标注值「{label_text}」非官方标准标注，跳过视频标注"))
            return
        try:
            entry = await self._find_first_locator(page, "text=选择视频标注")
            if not await entry.count():
                entry = await self._find_first_locator(page, ".post-with-mark-tag .select-display")
            if not await entry.count():
                tencent_logger.info(_msg("🧾", "当前页面未发现「视频标注」入口，跳过标注继续发布"))
                return
            await entry.click()
            await page.wait_for_timeout(800)
            target = await self._get_content_target(page)
            option = target.get_by_text(label_text, exact=True).first
            if not await option.count():
                option = page.get_by_text(label_text, exact=True).first
            await option.wait_for(state="visible", timeout=5000)
            await option.click()
            await page.wait_for_timeout(500)
            tencent_logger.success(_msg("🏷️", f"视频标注已选择：{label_text}"))
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"设置视频标注「{label_text}」失败，跳过继续发布：{exc}"))
        await page.wait_for_timeout(600)

    async def wait_for_upload_complete(
        self, page: Page, timeout_seconds: int = 3600, max_retries: int = 3
    ) -> None:
        """等上传完成。

        **必须有个头，而且重试必须有上限。** 原来是没有出口的 while True：上传出错就
        删掉重传，失败再删再传，永远循环；中间每 2 秒打一行「正在上传视频中...」——
        这条日志和真的在传一模一样，从外面完全分不出。

        实测（2026-08-11，172MB / 上行 ~0.5Mbps）：每次传到 4 分钟左右报错，然后重来，
        整整循环了近 2 小时也不会停，进程也不会退。用户看到的只有「正在上传视频中」，
        真相是同一段视频被反复上传了 20 多次。

        默认 1 小时 / 3 次重试：慢网络上大文件确实会传很久，上限要给够；
        但到点、或者重试用完，就带现场截图明确报错，不要静默地转下去。
        """
        deadline = time.monotonic() + timeout_seconds
        last_report = 0.0
        retries = 0
        while True:
            if time.monotonic() > deadline:
                try:
                    shot = Path(BASE_DIR) / "debug_tencent_upload_timeout.png"
                    await page.screenshot(path=str(shot), full_page=True)
                    tencent_logger.error(_msg("📸", f"上传超时现场已截图 {shot}"))
                except Exception:
                    pass
                raise RuntimeError(
                    f"视频号上传超过 {timeout_seconds} 秒仍未完成（「发表」按钮一直不可用）"
                )
            try:
                publish_button = await self._find_first_locator(page, 'div.form-btns button:has-text("发表"):visible')
                if await publish_button.count():
                    button_class = await publish_button.get_attribute("class")
                    # 检查是否有正在上传或转码的状态提示
                    is_uploading = False
                    for fr in page.frames:
                        if "empty.html" in fr.url:
                            continue
                        try:
                            if await fr.locator(".media-status-content:has-text('上传'), .media-status-content:has-text('转码'), .media-status-content:has-text('%')").count() > 0:
                                is_uploading = True
                                break
                        except Exception:
                            continue

                    if (
                        not is_uploading
                        and not await publish_button.is_disabled()
                        and (not button_class or "weui-desktop-btn_disabled" not in button_class)
                    ):
                        tencent_logger.info(_msg("🥳", "视频上传完毕"))
                        break

                # 每 2 秒刷一行同样的话没有信息量，只是把日志冲爆（实测 50 分钟刷了 1600 行）。
                # 30 秒一行，并且带上已等多久——「还要多久」是这里唯一有用的信息。
                now = time.monotonic()
                if now - last_report >= 30:
                    waited = int(timeout_seconds - (deadline - now))
                    tencent_logger.info(_msg("🏃", f"正在上传视频中...（已等 {waited} 秒）"))
                    last_report = now
                await asyncio.sleep(2)

                upload_failed = await page.locator("div.status-msg.error").count()
                delete_button = await page.locator('div.media-status-content div.tag-inner:has-text("删除")').count()
                if upload_failed and delete_button:
                    retries += 1
                    if retries > max_retries:
                        try:
                            shot = Path(BASE_DIR) / "debug_tencent_upload_failed.png"
                            await page.screenshot(path=str(shot), full_page=True)
                            tencent_logger.error(_msg("📸", f"上传反复失败，现场已截图 {shot}"))
                        except Exception:
                            pass
                        raise RuntimeError(
                            f"视频号上传连续失败 {max_retries} 次，已停止重试"
                            "（常见原因：文件过大、上行带宽太慢导致平台侧超时，或走了代理/VPN）"
                        )
                    tencent_logger.error(_msg("😵", f"发现上传出错了，准备重试（第 {retries}/{max_retries} 次）"))
                    await self.handle_upload_error(page)
            except RuntimeError:
                raise
            except Exception:
                await asyncio.sleep(2)

    async def submit_publish(self, page: Page) -> None:
        is_draft = getattr(self, "is_draft", False)
        # 先等待并清理遮罩/弹窗,再等发表或草稿按钮就绪
        btn_selector = 'div.form-btns button:has-text("保存草稿"):visible, button:has-text("保存草稿"):visible' if is_draft else 'div.form-btns button:has-text("发表"):visible, button:has-text("发表"):visible'
        
        for wait_round in range(60):
            await self._dismiss_switch_account_dialog(page)
            try:
                await page.evaluate("""() => document.querySelectorAll('.mask, .changeAccount-dialog, .common-dialog').forEach(e => e.remove())""")
            except Exception:
                pass
            publish_btn = await self._find_first_locator(page, btn_selector)
            try:
                if await publish_btn.count() and await publish_btn.is_visible():
                    break
            except Exception:
                pass
            await asyncio.sleep(1)
        else:
            tencent_logger.warning(_msg("😵", "60s 内未找到可见的发表/草稿按钮，尝试强制继续"))

        publish_btn = await self._find_first_locator(page, btn_selector)
        if not await publish_btn.count():
            # 备选通用选择器
            fallback_sel = 'button:has-text("保存草稿"), button:has-text("存草稿")' if is_draft else 'button:has-text("发表")'
            publish_btn = page.locator(fallback_sel).first

        if not await publish_btn.count():
            action_name = "保存草稿" if is_draft else "发表"
            raise RuntimeError(f"未找到「{action_name}」按钮，无法完成提交")

        # ========================================================
        # 1. 保存草稿分支（单次点击，结合多种成功信号轮询，彻底告别死循环）
        # ========================================================
        if is_draft:
            tencent_logger.info(_msg("💾", "正在点击「保存草稿」..."))
            try:
                await publish_btn.scroll_into_view_if_needed(timeout=3000)
                await publish_btn.click(timeout=4000)
            except Exception:
                await publish_btn.evaluate("el => el.click()")

            # 轮询探测保存草稿的结果反馈（最多等待 12 秒）
            for sec in range(12):
                await asyncio.sleep(1)
                cur_url = page.url

                # A. 检查页面是否已跳转（部分版本会重定向到草稿列表或控制台）
                if "/post/create" not in cur_url or "post/list" in cur_url or "draft" in cur_url:
                    tencent_logger.success(_msg("🥳", "视频草稿保存成功（页面已重定向）"))
                    return

                # B. 检查错误提示拦截 Toast
                warn_toast = page.locator("div.weui-desktop-tips_warn, div.weui-desktop-form__warn, div.form-error").first
                if await warn_toast.count() and await warn_toast.is_visible():
                    warn_txt = (await warn_toast.inner_text()).strip()
                    if warn_txt:
                        tencent_logger.error(_msg("❌", f"保存草稿失败拦截: {warn_txt}"))
                        raise RuntimeError(f"保存草稿被阻断: {warn_txt}")

                # C. 检查成功 Toast 提示（微信常见 .weui-desktop-toast, .weui-desktop-tips_success）
                success_toast = page.locator(".weui-desktop-toast, div.weui-desktop-tips_success, .toast-success").first
                if await success_toast.count() and await success_toast.is_visible():
                    toast_txt = (await success_toast.inner_text()).strip()
                    tencent_logger.success(_msg("🥳", f"视频草稿保存成功 ({toast_txt or '提示保存成功'})"))
                    return

                # D. 检查是否存在“保存成功”弹窗确认框
                dialog_succ = page.locator("div.weui-desktop-dialog, div.dialog-wrap").filter(has_text="保存").filter(has_text="成功").first
                if await dialog_succ.count() and await dialog_succ.is_visible():
                    ok_btn = dialog_succ.locator('button:has-text("确定"), button:has-text("我知道了"), button:has-text("完成"), button:has-text("好的")').first
                    if await ok_btn.count() and await ok_btn.is_visible():
                        try:
                            await ok_btn.click(timeout=2000)
                        except Exception:
                            pass
                    tencent_logger.success(_msg("🥳", "视频草稿保存成功"))
                    return

                # E. 检查按钮是否已被禁用（表示已提交保存中或已保存）
                try:
                    cls = await publish_btn.get_attribute("class") or ""
                    is_dis = await publish_btn.get_attribute("disabled")
                    if is_dis is not None or "disabled" in cls or "is-disabled" in cls:
                        tencent_logger.success(_msg("🥳", "视频草稿保存成功（按钮状态已置灰确认）"))
                        return
                except Exception:
                    pass

            # 12 秒内无任何报错拦截，且点击正常下发，判定草稿保存成功
            tencent_logger.success(_msg("🥳", "视频草稿保存指令已完成响应"))
            return

        # ========================================================
        # 2. 公开发表分支
        # ========================================================
        tencent_logger.info(_msg("🚀", "正在点击「发表」..."))
        try:
            await publish_btn.scroll_into_view_if_needed(timeout=3000)
            await publish_btn.click(timeout=4000)
        except Exception:
            await publish_btn.evaluate("el => el.click()")

        # 等待发表结果（最多等待 25 秒）
        for sec in range(25):
            await asyncio.sleep(1)
            cur_url = page.url

            # 检查是否有错误提示
            warn_toast = page.locator("div.weui-desktop-tips_warn, div.weui-desktop-form__warn, div.form-error").first
            if await warn_toast.count() and await warn_toast.is_visible():
                warn_txt = (await warn_toast.inner_text()).strip()
                if warn_txt:
                    tencent_logger.error(_msg("❌", f"微信视频号发表失败拦截: {warn_txt}"))
                    raise RuntimeError(f"微信视频号发表被阻断: {warn_txt}")

            # 检查成功跳转或按钮消失
            if "/post/create" not in cur_url:
                tencent_logger.success(_msg("🥳", "视频发布成功（页面已离开创建页）"))
                return

            if not await publish_btn.count():
                tencent_logger.success(_msg("🥳", "视频发布成功（发表按钮已正常移除）"))
                return

        raise RuntimeError("发表未在预期时间内完成，请检查发布页面状态")


class TencentVideo(TencentBaseUploader):
    def __init__(
        self,
        title,
        file_path,
        tags,
        publish_date: datetime | int,
        account_file,
        category=None,
        is_draft=False,
        desc: str | None = None,
        thumbnail_path: str | None = None,
        thumbnail_landscape_path: str | None = None,
        thumbnail_portrait_path: str | None = None,
        short_title: str | None = None,
        publish_strategy: str = TENCENT_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
        collection_name: str | None = None,
        content_label: str | None = None,
        location: str | None = None,
        link_type: str | None = None,
        link_url: str | None = None,
        link_title: str | None = None,
        activity_name: str | None = None,
    ):
        super().__init__(
            publish_date=publish_date,
            account_file=account_file,
            publish_strategy=publish_strategy,
            debug=debug,
            headless=headless,
            collection_name=collection_name,
        )
        self.title = title
        self.file_path = file_path
        self.tags = tags or []
        self.category = category
        self.is_draft = is_draft
        self.desc = desc or ""
        self.thumbnail_path = thumbnail_path
        self.thumbnail_landscape_path = thumbnail_landscape_path
        self.thumbnail_portrait_path = thumbnail_portrait_path or thumbnail_path
        self.short_title = short_title
        self.content_label = content_label
        self.location = location
        self.link_type = link_type
        self.link_url = link_url
        self.link_title = link_title
        self.activity_name = activity_name

    async def validate_upload_args(self):
        await self.validate_base_args()
        if not self.title or not str(self.title).strip():
            raise ValueError("视频模式下，title 是必须的")
        self.file_path = str(self.validate_video_file(self.file_path))
        if self.thumbnail_landscape_path:
            self.thumbnail_landscape_path = str(self.validate_image_file(self.thumbnail_landscape_path))
        if self.thumbnail_portrait_path:
            self.thumbnail_portrait_path = str(self.validate_image_file(self.thumbnail_portrait_path))

    async def handle_upload_error(self, page: Page) -> None:
        tencent_logger.info(_msg("😵", "视频出错了，重新上传中"))
        await page.locator('div.media-status-content div.tag-inner:has-text("删除")').click()
        await page.get_by_role("button", name="删除", exact=True).click()
        await self.upload_video_file(page, self.file_path)

    async def open_thumbnail_dialog(self, page: Page, selectors: list[str], dialog_titles: list[str]):
        for selector in selectors:
            cover_entry = await self._find_first_locator(page, selector)
            try:
                if not await cover_entry.count():
                    continue
                await cover_entry.wait_for(state="visible", timeout=3000)
                await cover_entry.click()
                await page.wait_for_timeout(500)
                break
            except Exception:
                continue

        for title in dialog_titles:
            cover_dialog = await self._find_first_locator(page, f"div.weui-desktop-dialog:has-text('{title}')")
            if await cover_dialog.count():
                return cover_dialog
        return None

    async def confirm_thumbnail_crop(self, page: Page) -> None:
        crop_dialog = await self._find_first_locator(page, "div.weui-desktop-dialog:has-text('裁剪封面图')")
        if not await crop_dialog.count():
            return

        try:
            await crop_dialog.wait_for(state="visible", timeout=10000)
            crop_confirm_button = crop_dialog.locator(
                'div.weui-desktop-dialog__ft button.weui-desktop-btn_primary:has-text("确定")'
            ).first
            if await crop_confirm_button.count():
                await crop_confirm_button.wait_for(state="visible", timeout=5000)
                await crop_confirm_button.click()
                await page.wait_for_timeout(1000)
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"封面裁剪确认时出错，小人继续尝试保存主弹窗: {exc}"))

    async def upload_thumbnail_in_dialog(self, page: Page, cover_dialog, thumbnail_path: str) -> None:
        await cover_dialog.wait_for(state="visible", timeout=5000)
        file_input = cover_dialog.locator('.single-cover-uploader-wrap input[type="file"]').first
        await file_input.wait_for(state="attached", timeout=10000)
        await file_input.set_input_files(thumbnail_path)
        await page.wait_for_timeout(2000)

        confirm_button = cover_dialog.locator(
            'div.weui-desktop-dialog__ft button.weui-desktop-btn_primary:has-text("确认")'
        ).first
        await confirm_button.wait_for(state="visible", timeout=10000)
        await confirm_button.click()

    async def set_single_thumbnail(
        self,
        page: Page,
        thumbnail_path: str,
        selectors: list[str],
        dialog_titles: list[str],
        label: str,
    ) -> None:
        cover_dialog = await self.open_thumbnail_dialog(page, selectors, dialog_titles)
        if not cover_dialog:
            tencent_logger.info(_msg("🧍", f"当前页面没有出现{label}封面编辑弹窗，小人先跳过"))
            return

        try:
            await self.upload_thumbnail_in_dialog(page, cover_dialog, thumbnail_path)
            tencent_logger.success(_msg("🥳", f"{label}封面已经设置完成"))
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"{label}封面设置失败，这次先跳过: {exc}"))

    async def set_thumbnail(self, page: Page) -> None:
        if not self.thumbnail_landscape_path and not self.thumbnail_portrait_path:
            return

        tencent_logger.info(_msg("🖼️", "小人准备设置封面"))

        landscape_selectors = [
            'div.horizontal-cover-wrap:has-text("4:3")',
            'div[class*="cover-wrap"]:has-text("4:3"):has-text("动态")',
            'div:has-text("视频号动态"):has-text("4:3")',
            'div:has-text("横版封面"):has-text("4:3")',
        ]
        portrait_selectors = [
            'div.vertical-cover-wrap:has-text("个人主页卡片"):has-text("3:4")',
            'div.vertical-cover-wrap:has-text("3:4")',
            'div.vertical-cover-wrap:has-text("个人主页卡片")',
        ]

        if self.thumbnail_landscape_path:
            await self.set_single_thumbnail(
                page,
                self.thumbnail_landscape_path,
                landscape_selectors,
                ["编辑视频号动态封面", "编辑动态封面", "编辑封面"],
                "4:3 横版",
            )
        if self.thumbnail_portrait_path:
            await self.set_single_thumbnail(
                page,
                self.thumbnail_portrait_path,
                portrait_selectors,
                ["编辑个人主页卡片", "编辑封面"],
                "3:4 竖版",
            )

    async def prepare_video_for_publish(self, page: Page) -> None:
        await self.wait_for_realtime_verification(page)
        await self.fill_title_and_tags(page)
        await self.fill_description(page)
        # 合集不在这里选：此时视频还在上传，上传完成后表单会刷新，
        # 上传中选的合集会被重置/不绑定（"日志说选了、后台没加"的根因）。
        # 改到 wait_for_upload_complete 之后再选，见 upload()。

    async def upload(self, playwright: Playwright) -> None:
        tencent_logger.info(_msg("🧍", "小人先检查 cookie、视频文件和发布时间"))
        await self.validate_upload_args()
        tencent_logger.info(_msg("🥳", "上传前检查通过"))

        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=self.headless))
        context = await browser.new_context(storage_state=self.account_file)

        try:
            page = await context.new_page()
            await self.open_upload_page(page)
            tencent_logger.info(_msg("🏃", f"小人开始搬运视频: {self.title}"))

            await self.upload_video_file(page, self.file_path)
            # 等待 3 秒确保文件上传动作被页面接收，微前端表单稳定就绪
            await page.wait_for_timeout(3000)
            await self.wait_for_realtime_verification(page)
            tencent_logger.info(_msg("📝", "开始按官方表单顺序依次设置发布选项..."))

            # 1. 视频描述与话题 (微信顶部 div.input-editor)
            await self.fill_editor_content(page)
            # 2. 短标题 (仅在用户显式配置时输入，不篡改不乱补)
            await self.set_short_title(page, self.title, self.short_title)
            # 3. 位置 (按平台定位 / 不显示位置)
            await self.apply_location(page)
            # 4. 添加到合集
            await self.apply_collection(page)
            # 5. 链接 (公众号文章 / 红包封面 / 视频号剧集 / 小程序短剧)
            await self.apply_link(page)
            # 6. 活动 (不参与活动 / 搜索活动名)
            await self.apply_activity(page)
            # 7. 定时发表
            if self.publish_strategy == TENCENT_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
                await self.set_schedule_time_tencent(page, self.publish_date)
            # 8. 视频标注
            await self.apply_original_statement(page)
            # 9. 封面设置
            await self.set_thumbnail(page)
            # 10. 表单填写完毕，等待视频文件上传与转码彻底完成（此时描述等必填已满足，发表按钮将正常变亮）
            await self.wait_for_upload_complete(page)
            # 11. 保存草稿或公开发表
            await self.submit_publish(page)

            await context.storage_state(path=self.account_file)
            tencent_logger.success(_msg("🥳", "cookie 更新完毕"))
        finally:
            await context.close()
            await browser.close()

    async def tencent_upload_video(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def main(self):
        await self.tencent_upload_video()


class TencentNote(TencentBaseUploader):
    def __init__(
        self,
        image_paths,
        note,
        tags,
        publish_date: datetime | int,
        account_file,
        title: str | None = None,
        publish_strategy: str = TENCENT_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
        is_draft: bool = False,
    ):
        super().__init__(
            publish_date=publish_date,
            account_file=account_file,
            publish_strategy=publish_strategy,
            debug=debug,
            headless=headless,
        )
        self.image_paths = image_paths
        self.note = note or ""
        self.title = title or (self.note[:30] if self.note else "")
        self.tags = tags or []
        self.is_draft = is_draft

    async def validate_upload_args(self):
        await self.validate_base_args()
        if not self.title or not str(self.title).strip():
            raise ValueError("图文模式下，title 是必须的")
        if not self.image_paths:
            raise ValueError("图文模式下，图片是必须的")

        if isinstance(self.image_paths, (str, Path)):
            self.image_paths = [self.image_paths]

        normalized_image_paths = []
        for image_path in self.image_paths:
            normalized_image_paths.append(str(self.validate_image_file(image_path)))
        self.image_paths = normalized_image_paths

    async def switch_to_note_mode(self, page: Page) -> None:
        raise NotImplementedError("请在 TencentNote.switch_to_note_mode 中补充视频号切换到图文发布模式的逻辑")

    async def upload_note_images(self, page: Page) -> None:
        raise NotImplementedError("请在 TencentNote.upload_note_images 中补充视频号图文图片上传逻辑")

    async def fill_note_title_and_tags(self, page: Page) -> None:
        raise NotImplementedError("请在 TencentNote.fill_note_title_and_tags 中补充视频号图文标题/话题填写逻辑")

    async def fill_note_body(self, page: Page) -> None:
        return None

    async def prepare_note_for_publish(self, page: Page) -> None:
        await self.fill_note_title_and_tags(page)
        await self.fill_note_body(page)
        await self.apply_collection(page)
        await self.apply_original_statement(page)

    async def upload_note_content(self, page: Page) -> None:
        await self.switch_to_note_mode(page)
        await self.upload_note_images(page)
        await self.prepare_note_for_publish(page)

    async def upload(self, playwright: Playwright) -> None:
        tencent_logger.info(_msg("🧍", "小人先检查 cookie、图文图片和发布时间"))
        await self.validate_upload_args()
        tencent_logger.info(_msg("🥳", "图文上传前检查通过"))

        browser = await playwright.chromium.launch(**_build_launch_kwargs(headless=self.headless))
        context = await browser.new_context(storage_state=self.account_file)
        context = await set_init_script(context)

        try:
            page = await context.new_page()
            await self.open_upload_page(page)
            tencent_logger.info(_msg("🏃", f"小人开始搬运图文，共 {len(self.image_paths)} 张图片"))

            await self.upload_note_content(page)

            if self.publish_strategy == TENCENT_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
                await self.set_schedule_time_tencent(page, self.publish_date)

            await self.submit_publish(page)

            await context.storage_state(path=self.account_file)
            tencent_logger.success(_msg("🥳", "cookie 更新完毕"))
        finally:
            await context.close()
            await browser.close()

    async def tencent_upload_note(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def main(self):
        await self.tencent_upload_note()
