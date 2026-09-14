# -*- coding: utf-8 -*-
"""
微信视频号平台适配器
管理视频号创作者中心 URL、防扫码 frame 误判识别、真实昵称与 sph 安全 UID 提取
"""

from typing import Tuple
from uploader.base_adapter import BasePlatformAdapter


class TencentPlatformAdapter(BasePlatformAdapter):
    platform_id = "tencent"
    creator_url = "https://channels.weixin.qq.com/platform"

    async def is_logged_in(self, page, context) -> bool:
        if not page:
            return False
        current_url = page.url
        has_qr_frame = any("open.weixin.qq.com/connect/qrconnect" in fr.url for fr in page.frames)
        has_login_url = "login.html" in current_url
        if not has_qr_frame and not has_login_url and "channels.weixin.qq.com" in current_url:
            for sel in ["h2.finder-nickname", "div.finder-nickname", "div.side-bar-footer .account-info span.name"]:
                try:
                    el = page.locator(sel).first
                    if await el.count() and await el.is_visible():
                        t = (await el.inner_text()).strip()
                        if t and len(t) < 40:
                            return True
                except Exception:
                    pass
        return False

    async def extract_profile(self, page, context, cookies: list = None) -> Tuple[str, str, str]:
        nickname = ""
        finder_uid = ""
        avatar = ""

        if page:
            for sel in [
                "h2.finder-nickname",
                "div.finder-nickname",
                "div.side-bar-footer .account-info span.name",
                ".side-bar-footer span.name"
            ]:
                try:
                    el = page.locator(sel).first
                    if await el.count() and await el.is_visible():
                        t = (await el.inner_text()).strip()
                        if t and len(t) < 40:
                            nickname = t
                            break
                except Exception:
                    pass

            try:
                uid_el = page.locator("span.finder-uniq-id, #finder-uid-copy").first
                if await uid_el.count():
                    finder_uid = (await uid_el.inner_text()).strip()
            except Exception:
                pass

            # 探测平台头像
            for avatar_sel in [
                "div.finder-nickname-wrapper img",
                "div.side-bar-footer .account-info img",
                "div.avatar-wrap img",
                "div.ant-avatar img",
                "header img[src*=\"qlogo\"]",
                "img[src*=\"wx.qlogo.cn\"]",
                "img.avatar"
            ]:
                try:
                    img_el = page.locator(avatar_sel).first
                    if await img_el.count():
                        src = await img_el.get_attribute("src")
                        if src and src.startswith("http"):
                            avatar = src.strip()
                            break
                except Exception:
                    pass

        if not finder_uid and cookies:
            for c in cookies:
                if c.get("name") == "wxuin" and c.get("value"):
                    finder_uid = str(c.get("value")).strip()
                    break

        return nickname, finder_uid, avatar

    def extract_from_state(self, state_data: dict) -> Tuple[str, str, str]:
        nickname = ""
        finder_uid = ""
        avatar = ""
        meta = state_data.get("account_meta", {})
        if isinstance(meta, dict):
            nickname = meta.get("nickname", "")
            finder_uid = meta.get("finder_uid", "")
            avatar = meta.get("avatar", "")

        for origin in state_data.get("origins", []):
            for ls in origin.get("localStorage", []):
                if ls.get("name") == "finder_username" and ls.get("value"):
                    finder_uid = str(ls.get("value")).strip()
                    break
        if not finder_uid:
            for c in state_data.get("cookies", []):
                if c.get("name") == "wxuin" and c.get("value"):
                    finder_uid = str(c.get("value")).strip()
                    break
        return nickname, finder_uid, avatar
