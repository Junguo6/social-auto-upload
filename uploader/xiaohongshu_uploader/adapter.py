# -*- coding: utf-8 -*-
"""
小红书创作者平台适配器
管理小红书创作者主页 URL、登录态识别、USER_INFO_FOR_BIZ 提取与小红书号解析
"""

import json
from typing import Tuple
from uploader.base_adapter import BasePlatformAdapter


class XiaohongshuPlatformAdapter(BasePlatformAdapter):
    platform_id = "xiaohongshu"
    creator_url = "https://creator.xiaohongshu.com/"

    async def is_logged_in(self, page, context) -> bool:
        if not page:
            return False
        current_url = page.url
        if "creator.xiaohongshu.com" in current_url and "login" not in current_url:
            for sel in ["div.user-info span.name", "div.name", ".author-name", "span.name"]:
                try:
                    el = page.locator(sel).first
                    if await el.count() and await el.is_visible():
                        return True
                except Exception:
                    pass
            # 尝试通过 localStorage 判断
            try:
                raw_biz = await page.evaluate("() => localStorage.getItem('USER_INFO_FOR_BIZ') || ''")
                if raw_biz:
                    return True
            except Exception:
                pass
        return False

    async def extract_profile(self, page, context, cookies: list = None) -> Tuple[str, str, str]:
        nickname = ""
        finder_uid = ""
        avatar = ""

        # 1. 优先从页面的 localStorage 获取 USER_INFO_FOR_BIZ
        if page:
            try:
                user_info_raw = await page.evaluate("() => localStorage.getItem('USER_INFO_FOR_BIZ') || ''")
                if user_info_raw:
                    try:
                        uinfo = json.loads(user_info_raw)
                        if isinstance(uinfo, dict):
                            nickname = str(uinfo.get("userName") or "").strip()
                            finder_uid = str(uinfo.get("redId") or uinfo.get("userId") or "").strip()
                            avatar = str(uinfo.get("userAvatar") or uinfo.get("avatar") or uinfo.get("image") or "").strip()
                    except Exception:
                        pass
            except Exception:
                pass

        # 2. 若未探测到昵称，从 DOM 元素抽取
        if not nickname and page:
            for sel in [
                ".account-name",
                ".name-box",
                "div.user-info",
                "div.user-info span.name",
                "span.name",
                "div.name",
                ".author-name"
            ]:
                try:
                    el = page.locator(sel).first
                    if await el.count() and await el.is_visible():
                        t = (await el.inner_text()).strip()
                        if t and len(t) < 40 and "创作" not in t:
                            nickname = t
                            break
                except Exception:
                    pass

        # 3. 若未获取到头像，从 DOM 头像元素探测
        if not avatar and page:
            for avatar_sel in [
                "img.user_avatar",
                "img.user-avatar",
                "div.avatar img",
                "div.user-avatar img",
                "[class*=\"avatar\"] img",
                "img[class*=\"avatar\"]",
                "header img[src*=\"xhscdn.com\"]",
                "img[src*=\"sns-avatar\"]"
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

        # 4. 若 UID 未获取，从 cookies 中获取 x-user-id-creator.xiaohongshu.com
        if not finder_uid and cookies:
            for c in cookies:
                if c.get("name") in ["x-user-id-creator.xiaohongshu.com", "userId"]:
                    finder_uid = str(c.get("value")).strip()
                    break

        if avatar and avatar.startswith("http://"):
            avatar = "https://" + avatar[7:]

        return nickname, finder_uid, avatar

    def extract_from_state(self, state_data: dict) -> Tuple[str, str, str]:
        nickname = ""
        finder_uid = ""
        avatar = ""
        meta = state_data.get("__account_meta__") or state_data.get("account_meta", {})
        if isinstance(meta, dict) and meta.get("nickname"):
            return meta.get("nickname", ""), meta.get("finder_uid", ""), meta.get("avatar", "")

        for origin in state_data.get("origins", []):
            for ls in origin.get("localStorage", []):
                if ls.get("name") == "USER_INFO_FOR_BIZ":
                    try:
                        uinfo = json.loads(ls.get("value", ""))
                        if not nickname:
                            nickname = str(uinfo.get("userName") or "").strip()
                        if not finder_uid:
                            finder_uid = str(uinfo.get("redId") or uinfo.get("userId") or "").strip()
                        if not avatar:
                            avatar = str(uinfo.get("userAvatar") or uinfo.get("avatar") or uinfo.get("image") or "").strip()
                    except Exception:
                        pass
        if not finder_uid:
            for c in state_data.get("cookies", []):
                if c.get("name") in ["x-user-id-creator.xiaohongshu.com", "userId"] and c.get("value"):
                    finder_uid = str(c.get("value")).strip()
                    break
        if avatar and avatar.startswith("http://"):
            avatar = "https://" + avatar[7:]
        return nickname, finder_uid, avatar
