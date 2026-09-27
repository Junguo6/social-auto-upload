# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import inspect
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from patchright.async_api import Page, Playwright, async_playwright
except ImportError:
    from playwright.async_api import Page, Playwright, async_playwright

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
                        radio = page.locator('span:has-text("自制"), label:has-text("自制"), div:has-text("自制")').first
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


    async def _upload_custom_cover(self, page: Page) -> bool:
        """通过 B 站【封面制作】弹窗上传用户指定的本地自定义封面图片"""
        bilibili_logger.info(_msg("🖼️", f"正在上传自定义封面: {self.thumbnail_path.name}"))
        try:
            # 1. 滚动到页面顶部封面区域
            await page.evaluate("() => window.scrollTo(0, 0)")
            await asyncio.sleep(0.5)

            # 2. 定位添加封面或更改封面入口
            pill = page.locator(
                '.cover-slot .cover-empty-pill, .cover-slot .add-text, .cover-slot, .cover-empty, .cover-main .cover-module, div:text("封面设置"), div:text("更改封面")'
            ).first
            if await pill.count() == 0:
                bilibili_logger.warning(_msg("⚠️", "未找到封面入口元素，尝试等待页面加载..."))
                await asyncio.sleep(1)

            # 点击入口打开【封面制作】弹窗
            await pill.click(force=True)
            bilibili_logger.info(_msg("⏳", "已点击封面入口，等待【封面制作】弹窗唤起..."))

            editor = page.locator('.cover-editor').first
            await editor.wait_for(state="visible", timeout=12000)

            # 3. 在弹窗内直接对文件输入框注入封面图片
            img_input = editor.locator('input[type="file"][accept*="image"]').first
            if await img_input.count() > 0:
                await img_input.set_input_files(str(self.thumbnail_path))
                bilibili_logger.info(_msg("📁", f"已成功注入封面图片文件: {self.thumbnail_path.name}"))
            else:
                # 备用点击拖拽区域上传
                upload_area = editor.locator('.bcc-upload.empty-uploader, .empty-uploader-wrap, div:has-text("拖拽图片或点击上传")').first
                async with page.expect_file_chooser(timeout=5000) as fc_info:
                    await upload_area.click(force=True)
                chooser = await fc_info.value
                await chooser.set_files(str(self.thumbnail_path))

            # 4. 等待图片裁剪预览渲染完成
            await asyncio.sleep(2)

            # 5. 点击弹窗右下角的【完成】按钮
            done_btn = editor.locator(
                '.cover-editor .button.submit, .cover-editor-button .submit, .cover-editor div:text-is("完成"), .cover-editor button:has-text("完成")'
            ).first
            if await done_btn.count() > 0:
                await done_btn.click(force=True)
                bilibili_logger.info(_msg("🎯", "已点击【封面制作】完成按钮，正在应用封面设置..."))
            else:
                # 兜底用 JS 触发点击
                await page.evaluate('''() => {
                    const btn = document.querySelector('.cover-editor .button.submit, .cover-editor-button .submit');
                    if (btn) btn.click();
                }''')

            # 等待弹窗消失
            try:
                await editor.wait_for(state="hidden", timeout=8000)
            except Exception:
                # 若弹窗未自动消失，尝试点击右上角关闭按钮
                close_btn = editor.locator('.bcc-dialog__close, i[class*="close"]').first
                if await close_btn.count() > 0:
                    await close_btn.click(force=True)

            await asyncio.sleep(1)
            bilibili_logger.info(_msg("✅", f"自定义封面上传完成: {self.thumbnail_path.name}"))
            return True
        except Exception as e:
            bilibili_logger.warning(_msg("⚠️", f"自定义封面上传未成功: {e}，将使用系统推荐截帧封面兜底"))
            # 确保关闭可能残留的弹窗遮罩
            try:
                await page.evaluate('''() => {
                    document.querySelectorAll('.cover-editor, .bcc-dialog__wrap').forEach(el => {
                        const close = el.querySelector('.bcc-dialog__close, i[class*="close"], .button.cancel');
                        if (close) close.click();
                    });
                }''')
            except Exception:
                pass
            return False

    def _extract_video_frame(self) -> Path | None:
        """从本地视频自动截取第 1 帧作为高可靠保底封面，彻底规避服务端截帧慢或失败"""
        try:
            import cv2
            cap = cv2.VideoCapture(str(self.file_path))
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None:
                tmp_dir = Path.home() / ".sau_tmp"
                tmp_dir.mkdir(parents=True, exist_ok=True)
                tmp_path = tmp_dir / f"bili_cover_{self.file_path.stem}.jpg"
                cv2.imwrite(str(tmp_path), frame)
                bilibili_logger.info(_msg("⚡", f"已从本地视频中快速截取首帧作为封面保底: {tmp_path.name}"))
                return tmp_path
        except Exception as e:
            bilibili_logger.debug(f"本地截帧跳过: {e}")
        return None

    async def _select_recommended_cover(self, page: Page) -> bool:
        """视频上传完成后，智能检测并选择系统推荐截帧封面（默认第1张，若服务端延迟过大则自动本地首帧保底）"""
        bilibili_logger.info(_msg("🖼️", "视频上传已就绪，正在等待并检测 B 站服务端生成推荐截帧封面..."))

        # 先将页面滚动到顶部封面区域，确保推荐封面列表进入视口
        try:
            await page.evaluate("() => window.scrollTo(0, 0)")
            await asyncio.sleep(0.5)
        except Exception:
            pass

        # 最多等待 25 秒服务端截帧生成，期间每隔 3 秒输出一次进度
        for attempt in range(25):
            # 优先精准定位推荐截帧卡片（必须是实际生成的图片卡片，排除 AI 生成按钮）
            cards = page.locator(
                '.cover-recommend-list .img-item-box.img-item-cover, .cover-recommend-list .card .img-item-cover, .cover-recommend-list .img-item-box'
            )
            count = await cards.count()
            if count > 0:
                # 遍历找到第一个非 AI 按钮的卡片并点击
                for idx in range(count):
                    card = cards.nth(idx)
                    try:
                        txt = (await card.inner_text()).strip()
                        if "AI" in txt or "生成" in txt:
                            continue
                        await card.scroll_into_view_if_needed()
                        await card.click(force=True)
                        await asyncio.sleep(1)

                        # 验证主封面区域是否已经成功呈现封面
                        cover_text = await page.locator('.cover-main').inner_text()
                        if "封面设置" in cover_text or "更改封面" in cover_text or (await page.locator('.cover-main img, .cover-main [style*="background"]').count() > 0):
                            bilibili_logger.info(_msg("🎯", f"已成功选用 B 站系统推荐第 {idx + 1} 张截帧封面！"))
                            return True
                    except Exception:
                        pass

                # JS 兜底点击第 1 张有效推荐封面卡片
                try:
                    js_clicked = await page.evaluate('''() => {
                        const recCards = document.querySelectorAll('.cover-recommend-list .img-item-box, .cover-recommend-list .img-item-cover');
                        for (const el of recCards) {
                            if (el.closest('.ai-generate-btn') || (el.innerText || '').includes('AI') || (el.innerText || '').includes('生成')) {
                                continue;
                            }
                            el.click();
                            return true;
                        }
                        return false;
                    }''')
                    if js_clicked:
                        await asyncio.sleep(1)
                        bilibili_logger.info(_msg("🎯", "通过 DOM 成功选定第 1 张系统推荐截帧封面！"))
                        return True
                except Exception:
                    pass

            # 每隔 3 秒输出一次等待日志，给用户清晰的视觉反馈
            if (attempt + 1) % 3 == 0:
                bilibili_logger.info(_msg("⏳", f"正在等待 B 站服务端完成截帧处理 (已等待 {attempt + 1} 秒)..."))

            await asyncio.sleep(1)

        # 超过 25 秒仍未截出：启动本地首帧秒级兜底上传
        bilibili_logger.info(_msg("💡", "B 站服务端截帧耗时较长，正在启动本地视频首帧秒级兜底机制..."))
        fallback_cover = self._extract_video_frame()
        if fallback_cover and fallback_cover.exists():
            self.thumbnail_path = fallback_cover
            upload_success = await self._upload_custom_cover(page)
            if upload_success:
                return True

        bilibili_logger.warning(_msg("⚠️", "未能获取到任何封面选项，将尝试继续投递"))
        return False

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
            change_btn = page.locator('button:has-text("更换视频"), span:has-text("更换视频"), div:has-text("更换视频")')
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
            fail_loc = page.locator('.upload-failed, [class*="upload-error"], span:has-text("上传失败"), div:has-text("上传失败")')
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

                # 4. 视频上传完成后，统一执行封面选定与应用
                cover_ok = False
                if self.thumbnail_path and self.thumbnail_path.exists():
                    bilibili_logger.info(_msg("🖼️", f"检测到用户已指定本地封面，正在上传: {self.thumbnail_path.name}"))
                    cover_ok = await self._upload_custom_cover(page)

                if not cover_ok:
                    # 若未提供自定义封面或自定义封面上传未成功，智能选用系统推荐截帧封面
                    cover_ok = await self._select_recommended_cover(page)

                # 投递前最终防线：检查是否仍然未选定封面（主槽位仍有“添加封面”字样且无图）
                empty_cover = page.locator('.cover-slot .add-text, .cover-slot .cover-empty-pill')
                if await empty_cover.count() > 0 and await empty_cover.first.is_visible():
                    bilibili_logger.warning(_msg("⚠️", "检测到主封面仍然为空，正在触发终极首帧保底..."))
                    fallback = self._extract_video_frame()
                    if fallback and fallback.exists():
                        self.thumbnail_path = fallback
                        await self._upload_custom_cover(page)

                # 5. 点击【立即投稿】按钮（强制消灭右下角遮挡气泡）
                bilibili_logger.info(_msg("🚀", "视频与元数据已就绪，正在触发最终投递..."))
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

                # 6. 等待投递成功确认（精确校验，严防误判）
                bilibili_logger.info(_msg("⏳", "正在确认投递结果..."))
                success = False
                for _ in range(25):
                    await asyncio.sleep(1)
                    curr_url = page.url

                    # 判定方式 1：页面发生真实跳转到稿件管理列表或投稿成功结果页
                    if "upload-manager" in curr_url or "upload/success" in curr_url or "platform/upload-manager" in curr_url:
                        success = True
                        break

                    # 判定方式 2：检测页面正文中弹出的明确投稿成功文本（避开左侧常驻侧边栏）
                    success_elem = page.locator(
                        'h1:has-text("稿件投递成功"), h2:has-text("稿件投递成功"), div:text-is("稿件投递成功"), .success-title, a:has-text("查看稿件")'
                    )
                    if await success_elem.count() > 0 and await success_elem.first.is_visible():
                        success = True
                        break

                    # 实时捕获表单校验报错（如：请上传视频封面、标题不合规等），即时阻断
                    err_box = page.locator('.error-tip, .bili-message-error, .toast-error, [class*="error-message"], [class*="error-tip"]')
                    if await err_box.count() > 0:
                        for e_idx in range(min(await err_box.count(), 3)):
                            if await err_box.nth(e_idx).is_visible():
                                err_msg = (await err_box.nth(e_idx).inner_text()).strip()
                                if err_msg:
                                    raise RuntimeError(f"B站表单校验未通过: {err_msg}")

                if not success:
                    # 超时未确认成功，再次检查错误提示
                    err_box = page.locator('.error-tip, .bili-message-error, .toast-error, [class*="error-message"], [class*="error-tip"]')
                    if await err_box.count() > 0 and await err_box.first.is_visible():
                        err_msg = (await err_box.first.inner_text()).strip()
                        raise RuntimeError(f"B站表单校验未通过: {err_msg}")
                    raise RuntimeError("B站投稿提交超时或未通过校验，页面未检测到投递成功跳转")

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
