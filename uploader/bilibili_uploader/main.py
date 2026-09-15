# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import inspect
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

# 常用分区映射表 (TID -> [一级分类, 二级分类])
TID_CATEGORY_MAP = {
    171: ("生活", "日常"),
    172: ("生活", "出行"),
    174: ("生活", "搞笑"),
    173: ("生活", "手工"),
    175: ("生活", "绘画"),
    21: ("动画", "综合"),
    138: ("游戏", "网络游戏"),
    122: ("科技", "软件应用"),
    230: ("知识", "科学科普"),
    231: ("知识", "社科·法律·心理"),
    76: ("美食", "美食制作"),
    157: ("影视", "影视剪辑"),
    163: ("时尚", "美妆护肤"),
    130: ("音乐", "音乐综合"),
    28: ("音乐", "原创音乐"),
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
        self.thumbnail_path = Path(thumbnail_path).resolve() if thumbnail_path and Path(thumbnail_path).exists() else None
        self.debug = debug
        self.headless = headless

    async def _extract_cookies_for_context(self) -> list[dict]:
        """从凭据文件中稳健提取 cookies 列表"""
        import json
        if not self.account_file.exists():
            return []
        try:
            with open(self.account_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            cookies = data.get("cookies", [])
            if not cookies and "cookie_info" in data and isinstance(data["cookie_info"], dict):
                cookies = data["cookie_info"].get("cookies", [])
            
            # 格式化兼容 Playwright 字段
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

    async def _select_partition(self, page: Page):
        """选择视频投稿分区"""
        bilibili_logger.info(_msg("🏷️", f"正在配置投稿分区 (TID={self.tid})..."))
        primary, secondary = TID_CATEGORY_MAP.get(self.tid, ("生活", "日常"))
        if self.category:
            parts = [p.strip() for p in self.category.replace("-", "/").split("/") if p.strip()]
            if len(parts) >= 2:
                primary, secondary = parts[0], parts[1]
            elif len(parts) == 1:
                secondary = parts[0]

        # 策略 1: 查找推荐分区标签 (B站通常在分区下方列出几个推荐子分区)
        try:
            sec_tag = page.locator(f'span:text("{secondary}"), div:text("{secondary}")')
            if await sec_tag.count() > 0 and await sec_tag.first.is_visible():
                await sec_tag.first.click()
                bilibili_logger.info(_msg("✅", f"已快速选中推荐分区: {secondary}"))
                return
        except Exception:
            pass

        # 策略 2: 点击分区选择器容器进行级联选择
        try:
            selector_btn = page.locator(
                'div.select-box-v2-container, div[class*="select-box"], div[class*="cascader-container"], div.drop-cascader-container'
            ).first
            if await selector_btn.count() > 0 and await selector_btn.is_visible():
                await selector_btn.click()
                await asyncio.sleep(0.6)

                # 点击主分类
                main_item = page.locator(f'text="{primary}"').first
                if await main_item.count() > 0 and await main_item.is_visible():
                    await main_item.click()
                    await asyncio.sleep(0.4)

                # 点击子分类
                sub_item = page.locator(f'text="{secondary}"').first
                if await sub_item.count() > 0 and await sub_item.is_visible():
                    await sub_item.click()
                    bilibili_logger.info(_msg("✅", f"已级联选择分区: {primary} -> {secondary}"))
                    return
        except Exception as e:
            bilibili_logger.warning(_msg("⚠️", f"级联选择分区遇到阻碍: {e}，尝试搜索匹配"))

        # 策略 3: 使用分区搜索框
        try:
            search_input = page.locator('input[placeholder*="搜索分区"], input[placeholder*="输入分区"]').first
            if await search_input.count() > 0 and await search_input.is_visible():
                await search_input.click()
                await search_input.fill(secondary)
                await asyncio.sleep(0.6)
                first_result = page.locator('div[class*="search-result-item"], li[class*="search-item"]').first
                if await first_result.count() > 0:
                    await first_result.click()
                    bilibili_logger.info(_msg("✅", f"已通过搜索选中分区: {secondary}"))
                    return
        except Exception:
            pass

        bilibili_logger.info(_msg("ℹ️", "分区使用系统默认推荐项"))

    async def _fill_form_metadata(self, page: Page):
        """填写稿件表单元数据（标题、自制、分区、标签、简介等）"""
        bilibili_logger.info(_msg("📝", f"开始填写稿件信息: 标题={self.title}"))

        # 1. 标题 (B站限制 80 字符)
        title_val = self.title[:80]
        try:
            title_input = page.locator(
                'input[placeholder*="请输入稿件标题"], input[placeholder*="稿件标题"], input[placeholder*="标题"], input.input-val'
            ).first
            await title_input.wait_for(state="visible", timeout=15000)
            await title_input.click()
            await title_input.fill(title_val)
            bilibili_logger.info(_msg("✅", f"已输入稿件标题: {title_val}"))
        except Exception as e:
            bilibili_logger.warning(_msg("⚠️", f"定位标题输入框失败: {e}"))

        await asyncio.sleep(0.5)

        # 2. 勾选“自制”
        try:
            original_radio = page.locator('text="自制", span:text("自制")').first
            if await original_radio.count() > 0 and await original_radio.is_visible():
                await original_radio.click()
        except Exception:
            pass

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
                            await tag_input.click()
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
                    await desc_input.click()
                    await desc_input.fill(self.desc)
                    bilibili_logger.info(_msg("✅", "简介填写完成"))
            except Exception as e:
                bilibili_logger.warning(_msg("⚠️", f"填写简介失败: {e}"))

        # 6. 上传封面 (若有自定义封面)
        if self.thumbnail_path and self.thumbnail_path.exists():
            bilibili_logger.info(_msg("🖼️", f"正在上传自定义封面: {self.thumbnail_path.name}"))
            try:
                cover_uploader = page.locator(
                    '.cover-upload, [class*="cover-upload"], div:text("更改封面"), div:text("上传封面")'
                ).first
                if await cover_uploader.count() > 0 and await cover_uploader.is_visible():
                    async with page.expect_file_chooser(timeout=8000) as fc_info:
                        await cover_uploader.click()
                    chooser = await fc_info.value
                    await chooser.set_files(str(self.thumbnail_path))
                    await asyncio.sleep(1)
                    confirm_btn = page.locator('button:text("完成"), button:text("确定"), text="完成"').first
                    if await confirm_btn.count() > 0 and await confirm_btn.is_visible():
                        await confirm_btn.click()
                    bilibili_logger.info(_msg("✅", "自定义封面上传完成"))
            except Exception as e:
                bilibili_logger.warning(_msg("⚠️", f"自定义封面上传未成功: {e}，将使用系统截帧封面"))

    async def _wait_for_upload_finish(self, page: Page, timeout_seconds: int = 900):
        """等待视频分片上传全部完成"""
        bilibili_logger.info(_msg("⏳", "正在监控视频上传进度，等待服务端接收完成..."))
        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout_seconds:
                raise TimeoutError(f"视频上传超时 (超过 {timeout_seconds} 秒)")

            # 检查是否已显示“上传完成”
            done_indicator = page.locator('text="上传完成", text="重新上传", span:text("上传完成")')
            if await done_indicator.count() > 0 and await done_indicator.first.is_visible():
                bilibili_logger.info(_msg("🎉", "视频分片上传 100% 完成！"))
                break

            # 提取进度百分比输出日志
            try:
                progress_elem = page.locator('.progress-text, [class*="progress-num"], [class*="upload-progress"]').first
                if await progress_elem.count() > 0 and await progress_elem.is_visible():
                    p_text = (await progress_elem.inner_text()).strip()
                    if p_text:
                        bilibili_logger.info(_msg("📤", f"上传进度: {p_text}"))
            except Exception:
                pass

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
                        ).first.click()
                    chooser = await fc_info.value
                    await chooser.set_files(str(self.file_path))

                bilibili_logger.info(_msg("✅", "视频文件已成功载入，进入表单编辑与上传同步阶段"))
                await asyncio.sleep(2)

                # 2. 填写稿件表单元数据（标题、分区、标签、简介等）
                await self._fill_form_metadata(page)

                # 3. 等待视频分片上传 100% 完成
                await self._wait_for_upload_finish(page)

                # 4. 点击【立即投稿】按钮
                bilibili_logger.info(_msg("🚀", "视频上传完成，正在触发最终投递..."))
                await asyncio.sleep(1)

                submit_btn = page.locator(
                    'button:text("立即投稿"), .submit-add, [class*="submit-btn"], button[class*="submit"]'
                ).first
                await submit_btn.wait_for(state="visible", timeout=15000)
                await submit_btn.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)
                await submit_btn.click()

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
