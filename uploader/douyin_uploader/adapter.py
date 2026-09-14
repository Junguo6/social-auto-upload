# -*- coding: utf-8 -*-
"""
抖音创作者平台适配器
管理抖音创作者主页 URL、登录态识别、真实昵称与抖音号提取
"""

import re
from typing import Tuple
from uploader.base_adapter import BasePlatformAdapter


class DouyinPlatformAdapter(BasePlatformAdapter):
    platform_id = "douyin"
    creator_url = "https://creator.douyin.com/"

    async def is_logged_in(self, page, context) -> bool:
        if not page:
            return False
        current_url = page.url
        if "creator.douyin.com" in current_url and "login" not in current_url:
            # 进一步确认不是登录表单界面
            for sel in [
                "span[class*=\"name-\"]",
                "div.user-info-name",
                "div.avatar-wrap + span",
                "div[class*=\"account-name\"]"
            ]:
                try:
                    el = page.locator(sel).first
                    if await el.count() and await el.is_visible():
                        return True
                except Exception:
                    pass
            # 如果在 creator-micro 后台主路径下，也视为登录成功
            if "creator-micro" in current_url:
                return True
        return False

    async def extract_profile(self, page, context, cookies: list = None) -> Tuple[str, str, str]:
        nickname = ""
        finder_uid = ""
        avatar = ""

        if page:
            # 探测真实昵称（完整保留 Emoji）
            for sel in [
                "span[class*=\"name-\"]",
                "div.user-info-name",
                "div.avatar-wrap + span",
                "div.name-wrap span",
                ".semi-navigation-header-title",
                "div[class*=\"account-name\"]"
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

            # 探测抖音号或 UID
            try:
                uid_el = page.locator("div[class*=\"unique_id-\"], span[class*=\"unique_id-\"]").first
                if await uid_el.count() and await uid_el.is_visible():
                    raw_text = (await uid_el.inner_text()).strip()
                    match = re.search(r"(\d+)", raw_text)
                    if match:
                        finder_uid = match.group(1)
                    else:
                        finder_uid = raw_text
            except Exception:
                pass

            # 探测抖音真实头像
            for avatar_sel in [
                "div[class*=\"avatar\"] img",
                ".semi-avatar img",
                "header img[src*=\"douyinpic.com\"]",
                "header img[src*=\"byteimg.com\"]",
                "img[class*=\"avatar\"]",
                "img[alt*=\"avatar\"]"
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
                if c.get("name") in ["uid_tt", "uid_tt_ss"] and c.get("value"):
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
        
        for c in state_data.get("cookies", []):
            if not finder_uid and c.get("name") in ["uid_tt", "uid_tt_ss"] and c.get("value"):
                finder_uid = str(c.get("value")).strip()
                break
        return nickname, finder_uid, avatar
