# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import inspect
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from patchright.async_api import Page, Playwright, async_playwright

from conf import BASE_DIR, DEBUG_MODE, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from utils.base_social_media import set_init_script
from utils.log import bilibili_logger

BILIBILI_CREATOR_URL = "https://member.bilibili.com/platform/home"
BILIBILI_UPLOAD_FRAME_URL = "https://member.bilibili.com/platform/upload/video/frame"
BILIBILI_MANAGE_URL = "https://member.bilibili.com/platform/upload-manager/article"

# 前端与 B站最新创作者服务平台分区映射表 (TID -> [一级分类, 二级分类])
TID_CATEGORY_MAP = {
    230: ("科技数码", "软件应用"),     # 科技 - 软件应用/计算机技术
    122: ("科技数码", "野生技术协会"),   # 科技 - 野生技术协会
    240: ("人工智能", "创新应用"),      # 人工智能 - 创新应用
    171: ("游戏", "电子竞技"),         # 游戏 - 电子竞技
    17:  ("游戏", "单机游戏"),         # 游戏 - 单机游戏
    21:  ("生活经验", "生活兴趣"),      # 生活 - 日常
    138: ("生活经验", "搞笑"),         # 生活 - 搞笑
    163: ("美食", "美食制作"),         # 生活 - 美食制作
    217: ("知识", "科学科普"),         # 知识 - 科学科普
    201: ("知识", "商业财经"),         # 知识 - 商业财经
    157: ("影视", "影视剪辑"),         # 影视 - 影视剪辑
    130: ("音乐", "音乐综合"),         # 音乐 - 音乐综合
}


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


def _resolve_account_file(account_file: str | Path) -> Path:
    path = Path(account_file).expanduser()
    if path.is_absolute():
        return path
    target = Path(BASE_DIR) / "cookies" / path.name
    if target.exists():
        return target.resolve()
    return path.resolve()


class BilibiliVideo(BaseVideoUploader):
    def __init__(
        self,
        title: str,
        file_path: str | Path,
        tags: list[str] | None = None,
        publish_date: datetime | int = 0,
        account_file: str | Path = "",
        category: str | None = None,
        tid: int = 171,
        desc: str | None = None,
        declaration: str | None = "1",
        thumbnail_path: str | Path | None = None,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
    ):
        self.title = (title or "").strip()
        self.file_path = self.validate_video_file(file_path)
        self.tags = [t.strip() for t in (tags or []) if t.strip()]
        self.publish_date = publish_date
        self.account_file = _resolve_account_file(account_file)
        self.category = category
        self.tid = tid or 171
        self.desc = desc or self.title
        self.declaration = str(declaration).strip() if declaration else "1"
        self.thumbnail_path = Path(thumbnail_path).resolve() if thumbnail_path and Path(thumbnail_path).exists() else None
        self.debug = debug
        self.headless = headless

    async def _extract_cookies_for_context(self) -> list[dict]:
        """从凭据文件中稳健提取 cookies 列表"""
        if not self.account_file.exists():
            return []
        try:
            with open(self.account_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            cookies = data.get("cookies", [])
            if not cookies and "cookie_info" in data and isinstance(data["cookie_info"], dict):
                cookies = data["cookie_info"].get("cookies", [])
            
            pw_cookies = []
            for c in cookies:
                if not isinstance(c, dict) or not c.get("name"):
                    continue
                pw_cookie = {
                    "name": str(c["name"]),
                    "value": str(c.get("value", "")),
                    "domain": str(c.get("domain") or ".bilibili.com"),
                    "path": str(c.get("path") or "/"),
                }
                if "secure" in c:
                    pw_cookie["secure"] = bool(c["secure"])
                if "httpOnly" in c:
                    pw_cookie["httpOnly"] = bool(c["httpOnly"])
                elif "http_only" in c:
                    pw_cookie["httpOnly"] = bool(c["http_only"])
                pw_cookies.append(pw_cookie)
            return pw_cookies
        except Exception as e:
            bilibili_logger.warning(_msg("⚠️", f"读取 Cookie 发生异常: {e}"))
            return []

    async def _clear_overlays(self, page: Page):
        """自动检测并消除阻挡交互的弹窗、通知浮层、验证码遮罩及右下角气泡"""
        try:
            # 1. 点击常见的关闭按钮
            close_buttons = page.locator(
                '.risk-captcha [class*="close"], .base-verify [class*="close"], '
                '.bcc-dialog__footer button, .bcc-dialog [class*="close"], '
                'button:has-text("知道了"), button:has-text("确定"), button:has-text("我知道了"), '
                '.vp-nd-f, [class*="bubble"] [class*="close"], [class*="guide"] [class*="close"]'
            )
            count = await close_buttons.count()
            for i in range(min(count, 5)):
                try:
                    btn = close_buttons.nth(i)
                    if await btn.is_visible():
                        await btn.click(force=True, timeout=1200)
                        await asyncio.sleep(0.2)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            # 2. 移除拦截指针事件的遮罩背景 (仅针对非验证码的提示遮罩)
            await page.evaluate(r'''() => {
                const overlaySelectors = [
                    '.bcc-dialog', '.add-modal', '.v-modal', '.vp-nd-f',
                    '[class*="guide-bubble"]'
                ];
                document.querySelectorAll(overlaySelectors.join(',')).forEach(el => {
                    try {
                        el.style.display = 'none';
                        el.remove();
                    } catch(e) {}
                });
            }''')
        except Exception:
            pass

    async def _check_and_handle_captcha(self, page: Page):
        """检测是否出现平台安全验证码（短信验证码、极验滑块等），若出现则根据策略主动跳过该账号"""
        try:
            captcha_locators = page.locator(
                '.risk-captcha, .base-verify.sms-verify, input.sms-cell, '
                '.geetest_panel, .geetest_popup_wrap, .geetest_radar_tip, [class*="captcha-box"], [class*="risk-dialog"]'
            )
            count = await captcha_locators.count()
            for i in range(count):
                item = captcha_locators.nth(i)
                if await item.is_visible():
                    bilibili_logger.warning(
                        _msg("⚠️", "检测到账号触发平台安全验证码（短信验证/人机滑块），根据配置策略自动跳过该账号！")
                    )
                    raise RuntimeError("检测到平台安全验证码，已自动跳过该账号")
        except RuntimeError:
            raise
        except Exception:
            pass

    async def _handle_declaration(self, page: Page):
        """配置创作声明（自制原创、转载注明出处、AI生成等）"""
        await self._clear_overlays(page)
        bilibili_logger.info(_msg("🛡️", f"正在配置创作声明 (declaration={self.declaration})..."))
        try:
            claim_input = page.locator('input[placeholder*="创作声明"]').first
            if await claim_input.count() > 0 and await claim_input.is_visible():
                await claim_input.click(force=True)
                await asyncio.sleep(0.5)

                decl = str(self.declaration).strip()
                if decl == "2" or "转载" in decl:
                    # 转载声明
                    opt = page.locator('.bcc-select-option-list li:has-text("转载"), .bcc-select-item:has-text("转载")').first
                    if await opt.count() > 0:
                        await opt.click(force=True)
                        bilibili_logger.info(_msg("✅", "已选择【内容为转载】"))
                        await asyncio.sleep(0.5)

                        # 填写转载出处输入框（必填）
                        source_input = page.locator('input[placeholder*="转载"], input[placeholder*="来源"], input[placeholder*="出处"]').first
                        if await source_input.count() > 0 and await source_input.is_visible():
                            source_text = "转自公开网络渠道"
                            await source_input.click(force=True)
                            await source_input.fill(source_text)
                            bilibili_logger.info(_msg("✅", f"已自动填报转载来源: {source_text}"))
                elif "AI" in decl or "ai" in decl or "人工智能" in decl:
                    opt = page.locator('.bcc-select-option-list li:has-text("AI"), .bcc-select-item:has-text("AI")').first
                    if await opt.count() > 0:
                        await opt.click(force=True)
                        bilibili_logger.info(_msg("✅", "已选择【含AI生成内容】"))
                else:
                    # 自制原创 (默认 1)
                    opt = page.locator('.bcc-select-option-list li:has-text("自制"), .bcc-select-item:has-text("自制")').first
                    if await opt.count() > 0:
                        await opt.click(force=True)
                        bilibili_logger.info(_msg("✅", "已选择【自制原创：未经作者允许，禁止转载】"))
                    else:
                        radio = page.locator('text="自制", span:text("自制")').first
                        if await radio.count() > 0:
                            await radio.click(force=True)
        except Exception as e:
            bilibili_logger.warning(_msg("⚠️", f"配置创作声明失败: {e}，将使用系统默认值"))

    async def _select_partition(self, page: Page):
        """选择视频投稿分区（支持最新两级级联面板）"""
        await self._clear_overlays(page)
        bilibili_logger.info(_msg("🏷️", f"正在配置投稿分区 (TID={self.tid})..."))
        primary, secondary = TID_CATEGORY_MAP.get(self.tid, ("生活经验", "生活兴趣"))
        if self.category:
            parts = [p.strip() for p in self.category.replace("-", "/").split("/") if p.strip()]
            if len(parts) >= 2:
                primary, secondary = parts[0], parts[1]
            elif len(parts) == 1:
                secondary = parts[0]

        # 策略 1: 检查快捷推荐分区标签
        try:
            rec_tag = page.locator(f'.recommand-tag:has-text("{secondary}"), [class*="rec-tag"]:has-text("{secondary}")').first
            if await rec_tag.count() > 0 and await rec_tag.is_visible():
                await rec_tag.click(force=True)
                bilibili_logger.info(_msg("✅", f"已快速选中推荐分区: {secondary}"))
                return
        except Exception:
            pass

        # 策略 2: 点击分区选择器展开级联面板
        try:
            selector_btn = page.locator(
                '.select-controller, .select-item-cont, div.select-box-v2-container, div[class*="select-box"], div[class*="cascader-container"], div.drop-cascader-container'
            ).first
            if await selector_btn.count() > 0:
                await selector_btn.click(force=True)
                await asyncio.sleep(0.8)

                # 点击一级主大类
                first_item = page.locator(f'.drop-list-v2-item:has-text("{primary}"), [class*="cascader"] li:has-text("{primary}"), div:text("{primary}")').first
                if await first_item.count() > 0:
                    await first_item.click(force=True)
                    await asyncio.sleep(0.5)

                # 点击二级子分类
                second_item = page.locator(f'.drop-list-v2-item:has-text("{secondary}"), [class*="cascader"] li:has-text("{secondary}"), div:text("{secondary}")').first
                if await second_item.count() > 0:
                    await second_item.click(force=True)
                    bilibili_logger.info(_msg("✅", f"已级联选择分区: {primary} -> {secondary}"))
                    return
        except Exception as e:
            bilibili_logger.warning(_msg("⚠️", f"级联选择分区遇到阻碍: {e}"))

        # 策略 3: 使用分区搜索框
        try:
            search_input = page.locator('input[placeholder*="搜索分区"], input[placeholder*="输入分区"]').first
            if await search_input.count() > 0 and await search_input.is_visible():
                await search_input.click(force=True)
                await search_input.fill(secondary)
                await asyncio.sleep(0.6)
                first_result = page.locator('div[class*="search-result-item"], li[class*="search-item"]').first
                if await first_result.count() > 0:
                    await first_result.click(force=True)
                    bilibili_logger.info(_msg("✅", f"已通过搜索选中分区: {secondary}"))
                    return
        except Exception:
            pass

        bilibili_logger.info(_msg("ℹ️", "分区保留当前选中项"))

    async def _handle_schedule(self, page: Page):
        """配置定时发布"""
        if not self.publish_date:
            return
        await self._clear_overlays(page)
        bilibili_logger.info(_msg("⏰", f"正在配置定时发布: {self.publish_date}..."))
        try:
            switch_btn = page.locator('div:has-text("定时发布") .bcc-switch, div:has-text("定时发布") [class*="switch"], .form-item:has-text("定时发布") [role="switch"]').first
            if await switch_btn.count() > 0:
                is_checked = "checked" in (await switch_btn.get_attribute("class") or "")
                if not is_checked:
                    await switch_btn.click(force=True)
                    await asyncio.sleep(0.8)
                bilibili_logger.info(_msg("✅", "已开启定时发布开关"))
        except Exception as e:
            bilibili_logger.warning(_msg("⚠️", f"配置定时发布失败: {e}"))

    async def _fill_form_metadata(self, page: Page):
        """填写稿件表单元数据（标题、创作声明、分区、标签、简介等）"""
        bilibili_logger.info(_msg("📝", f"开始填写稿件信息: 标题={self.title}"))

        await self._clear_overlays(page)

        # 1. 标题 (B站限制 80 字符)
        title_val = self.title[:80]
        try:
            title_input = page.locator(
                'input[placeholder*="请输入稿件标题"], input[placeholder*="稿件标题"], input[placeholder*="标题"], input.input-val'
            ).first
            await title_input.wait_for(state="visible", timeout=15000)
            await title_input.click(force=True)
            await title_input.fill(title_val)
            bilibili_logger.info(_msg("✅", f"已输入稿件标题: {title_val}"))
        except Exception as e:
            bilibili_logger.warning(_msg("⚠️", f"定位标题输入框失败: {e}"))

        await asyncio.sleep(0.5)

        # 2. 创作声明（自制/转载/AI）
        await self._handle_declaration(page)
        await asyncio.sleep(0.5)

        # 3. 选择分区
        await self._select_partition(page)
        await asyncio.sleep(0.5)

        # 4. 输入标签 (逐个按 Enter 确认)
        if self.tags:
            bilibili_logger.info(_msg("🏷️", f"正在添加标签: {', '.join(self.tags)}"))
            try:
                tag_input = page.locator(
                    'input[placeholder*="创建标签"], input[placeholder*="按回车键创建标签"], input[placeholder*="添加标签"]'
                ).first
                if await tag_input.count() > 0 and await tag_input.is_visible():
                    for tag in self.tags[:10]:
                        try:
                            await tag_input.click(force=True)
                            await tag_input.fill(tag)
                            await page.keyboard.press("Enter")
                            await asyncio.sleep(0.4)
                        except Exception:
                            pass
                    bilibili_logger.info(_msg("✅", "标签添加完成"))
            except Exception as e:
                bilibili_logger.warning(_msg("⚠️", f"输入标签失败: {e}"))

        await asyncio.sleep(0.5)

        # 5. 填写简介
        if self.desc:
            bilibili_logger.info(_msg("📄", "正在填写视频简介..."))
            try:
                desc_input = page.locator(
                    'div.ql-editor, textarea[placeholder*="填写更全"], textarea[placeholder*="视频简介"], textarea'
                ).first
                if await desc_input.count() > 0 and await desc_input.is_visible():
                    await desc_input.click(force=True)
                    await desc_input.fill(self.desc)
                    bilibili_logger.info(_msg("✅", "简介填写完成"))
            except Exception as e:
                bilibili_logger.warning(_msg("⚠️", f"填写简介失败: {e}"))

        # 6. 定时发布
        if self.publish_date:
            await self._handle_schedule(page)
            await asyncio.sleep(0.5)

        # 7. 上传封面 (若有自定义封面)
        if self.thumbnail_path and self.thumbnail_path.exists():
            bilibili_logger.info(_msg("🖼️", f"正在上传自定义封面: {self.thumbnail_path.name}"))
            try:
                cover_uploader = page.locator(
                    '.cover-upload, [class*="cover-upload"], div:text("更改封面"), div:text("上传封面")'
                ).first
                if await cover_uploader.count() > 0 and await cover_uploader.is_visible():
                    async with page.expect_file_chooser(timeout=8000) as fc_info:
                        await cover_uploader.click(force=True)
                    chooser = await fc_info.value
                    await chooser.set_files(str(self.thumbnail_path))
                    await asyncio.sleep(1)
                    confirm_btn = page.locator('button:text("完成"), button:text("确定"), text="完成"').first
                    if await confirm_btn.count() > 0 and await confirm_btn.is_visible():
                        await confirm_btn.click(force=True)
                    bilibili_logger.info(_msg("✅", "自定义封面上传完成"))
            except Exception as e:
                bilibili_logger.warning(_msg("⚠️", f"自定义封面上传未成功: {e}，将使用系统截帧封面"))

    async def _wait_for_upload_finish(self, page: Page, timeout_seconds: int = 900):
        """等待视频分片上传全部完成"""
        bilibili_logger.info(_msg("⏳", "正在监控视频上传进度，等待服务端接收完成..."))
        start_time = asyncio.get_event_loop().time()
        last_progress = ""

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout_seconds:
                raise TimeoutError(f"视频上传超时 (超过 {timeout_seconds} 秒)")

            # 消除可能弹出的遮罩和引导气泡
            await self._clear_overlays(page)

            # 1. 精确指标一：检查是否存在并可见的“更换视频”按钮（上传完成后必定出现，且唯一性极高）
            change_btn = page.locator('text="更换视频", button:has-text("更换视频"), span:has-text("更换视频")')
            c_count = await change_btn.count()
            if c_count > 0:
                for idx in range(min(c_count, 3)):
                    if await change_btn.nth(idx).is_visible():
                        bilibili_logger.info(_msg("🎉", "检测到视频上传已完成（出现更换视频标识）！"))
                        return

            # 2. 精确指标二：遍历检查“上传完成”文本的可见性（避免 .first 取到不可见外层容器）
            done_spans = page.locator('span:text-is("上传完成"), span.text:has-text("上传完成"), div:text-is("上传完成")')
            count = await done_spans.count()
            if count == 0:
                done_spans = page.locator('span:has-text("上传完成"), div:has-text("上传完成")')
                count = await done_spans.count()

            for idx in range(min(count, 15)):
                try:
                    elem = done_spans.nth(idx)
                    if await elem.is_visible():
                        txt = (await elem.inner_text()).strip()
                        if "上传完成" in txt and len(txt) <= 10:  # 确保是小标签，不是包含大量文字的外层大容器
                            bilibili_logger.info(_msg("🎉", "视频分片上传 100% 完成！"))
                            return
                except Exception:
                    pass

            # 3. 检查是否有上传失败报错
            fail_loc = page.locator('.upload-failed, [class*="upload-error"], text="上传失败"')
            if await fail_loc.count() > 0:
                for idx in range(min(await fail_loc.count(), 3)):
                    if await fail_loc.nth(idx).is_visible():
                        err_text = (await fail_loc.nth(idx).inner_text()).strip()
                        raise RuntimeError(f"B站视频上传失败: {err_text}")

            # 4. 提取进度百分比输出日志
            try:
                progress_elem = page.locator('.progress-text, [class*="progress-num"], [class*="upload-progress"], [class*="upload-status"]').first
                if await progress_elem.count() > 0 and await progress_elem.is_visible():
                    p_text = (await progress_elem.inner_text()).strip()
                    if p_text and p_text != last_progress:
                        last_progress = p_text
                        bilibili_logger.info(_msg("📤", f"上传进度: {p_text}"))
            except Exception:
                pass

            # 5. 智能兜底：B 站官方明确支持“信息填写后，就可投稿！不需等待上传完成”
            # 若等待已超 30 秒，且底部的“立即投稿”按钮处于可见状态，可顺利推进至投稿
            if elapsed > 30:
                submit_btn = page.locator('button:text("立即投稿"), .submit-add, [class*="submit-btn"]')
                if await submit_btn.count() > 0 and await submit_btn.first.is_visible():
                    bilibili_logger.info(_msg("💡", "已达稳定上传状态（服务支持后台接收），准备进入投稿流程..."))
                    return

            await asyncio.sleep(2)

    async def upload(self) -> Path:
        """执行完整的 B 站网页拟真发布闭环"""
        bilibili_logger.info(_msg("🚀", f"启动哔哩哔哩 Playwright 原生发布: {self.file_path.name}"))

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=1440,900",
        ]

        async with async_playwright() as playwright:
            browser = None
            strategies = []
            if LOCAL_CHROME_PATH and Path(LOCAL_CHROME_PATH).exists():
                strategies.append((f"指定 Chrome ({LOCAL_CHROME_PATH})", {"executable_path": LOCAL_CHROME_PATH, "headless": self.headless, "args": launch_args}))
            if sys.platform == "darwin":
                strategies.append(("系统 Chrome", {"channel": "chrome", "headless": self.headless, "args": launch_args}))
                strategies.append(("系统 Edge", {"channel": "msedge", "headless": self.headless, "args": launch_args}))
            elif sys.platform == "win32":
                strategies.append(("系统 Edge", {"channel": "msedge", "headless": self.headless, "args": launch_args}))
                strategies.append(("系统 Chrome", {"channel": "chrome", "headless": self.headless, "args": launch_args}))
            strategies.append(("内置 Chromium", {"headless": self.headless, "args": launch_args}))

            for name, opts in strategies:
                try:
                    browser = await playwright.chromium.launch(**opts)
                    if browser:
                        bilibili_logger.info(_msg("🌐", f"已拉起拟真浏览器内核: {name}"))
                        break
                except Exception:
                    continue

            if not browser:
                raise RuntimeError("无法启动任何可用浏览器内核，请确保安装了 Chrome 或 Chromium")

            context_kwargs = {
                "viewport": {"width": 1440, "height": 900},
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            }

            if self.account_file.exists():
                try:
                    context = await browser.new_context(storage_state=str(self.account_file), **context_kwargs)
                except Exception:
                    context = await browser.new_context(**context_kwargs)
                    cookies = await self._extract_cookies_for_context()
                    if cookies:
                        await context.add_cookies(cookies)
            else:
                context = await browser.new_context(**context_kwargs)

            context = await set_init_script(context)
            page = await context.new_page()

            try:
                bilibili_logger.info(_msg("🔗", f"正在打开 B 站创作服务平台投稿页: {BILIBILI_UPLOAD_FRAME_URL}"))
                await page.goto(BILIBILI_UPLOAD_FRAME_URL, wait_until="domcontentloaded", timeout=40000)
                await asyncio.sleep(2)

                # 初始清除各类弹窗与遮罩
                await self._clear_overlays(page)

                # 检查登录态是否有效（若被重定向到登录页则提示凭证失效）
                curr_url = page.url
                if "passport.bilibili.com" in curr_url or "login" in curr_url:
                    raise RuntimeError("B站账号凭据已过期，请在桌面端点击【重新登录】进行扫码授权")

                # 1. 定位上传文件 input 标签或触发文件选择器
                bilibili_logger.info(_msg("📁", f"正在注入待发布视频文件: {self.file_path}"))
                file_input = page.locator('input[type="file"]')
                if await file_input.count() > 0:
                    await file_input.first.set_input_files(str(self.file_path))
                else:
                    async with page.expect_file_chooser(timeout=15000) as fc_info:
                        await page.locator(
                            '.bcc-upload-wrapper, [class*="upload-btn"], [class*="upload_btn"], .upload-btn'
                        ).first.click(force=True)
                    chooser = await fc_info.value
                    await chooser.set_files(str(self.file_path))

                bilibili_logger.info(_msg("✅", "视频文件已成功载入，进入表单编辑与上传同步阶段"))
                await asyncio.sleep(2)

                # 检查是否触发安全验证码，若触发则自动跳过
                await self._check_and_handle_captcha(page)

                # 2. 填写稿件表单元数据（标题、分区、标签、简介等）
                await self._fill_form_metadata(page)

                # 3. 等待视频分片上传 100% 完成
                await self._wait_for_upload_finish(page)

                # 4. 点击【立即投稿】按钮（强制消灭右下角遮挡气泡）
                bilibili_logger.info(_msg("🚀", "视频上传完成，正在触发最终投递..."))
                await self._clear_overlays(page)
                await asyncio.sleep(1)

                # 投递前再次检查验证码
                await self._check_and_handle_captcha(page)

                submit_btn = page.locator(
                    'button:text("立即投稿"), .submit-add, [class*="submit-btn"], button[class*="submit"]'
                ).first
                await submit_btn.wait_for(state="visible", timeout=15000)
                await submit_btn.scroll_into_view_if_needed()
                await self._clear_overlays(page)
                await asyncio.sleep(0.5)
                await submit_btn.click(force=True)

                # 5. 等待投递成功确认
                bilibili_logger.info(_msg("⏳", "正在确认投递结果..."))
                success = False
                for _ in range(25):
                    await asyncio.sleep(1)
                    page_text = await page.content()
                    if (
                        "稿件投递成功" in page_text
                        or "投稿成功" in page_text
                        or "稿件管理" in page_text
                        or "upload-manager" in page.url
                    ):
                        success = True
                        break

                if not success:
                    # 若页面仍留在投稿页但有错误提示框，抓取错误
                    err_box = page.locator('.error-tip, .bili-message-error, [class*="error-message"]')
                    if await err_box.count() > 0 and await err_box.first.is_visible():
                        err_msg = (await err_box.first.inner_text()).strip()
                        raise RuntimeError(f"B站表单校验未通过: {err_msg}")
                    bilibili_logger.warning(_msg("⚠️", "未检测到明确成功提示，根据页面跳转判定完成"))

                bilibili_logger.info(_msg("🎉", f"哔哩哔哩稿件发布成功: 《{self.title}》！"))
                await asyncio.sleep(2)
                return self.account_file

            finally:
                try:
                    await page.close()
                    await context.close()
                    await browser.close()
                except Exception:
                    pass
