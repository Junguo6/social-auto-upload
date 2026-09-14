# -*- coding: utf-8 -*-
"""
哔哩哔哩平台适配器
管理B站创作者中心 URL、登录态识别、官方 nav 接口用户信息获取及 biliup 凭证格式兼容转换
"""

import json
from typing import Tuple
from uploader.base_adapter import BasePlatformAdapter

try:
    import requests
except ImportError:
    requests = None


class BilibiliPlatformAdapter(BasePlatformAdapter):
    platform_id = "bilibili"
    creator_url = "https://member.bilibili.com/"

    async def is_logged_in(self, page, context) -> bool:
        if not context:
            return False
        try:
            cookies = await context.cookies()
            return any(c.get("name") in ["DedeUserID", "SESSDATA"] and c.get("value") for c in cookies)
        except Exception:
            return False

    async def extract_profile(self, page, context, cookies: list = None) -> Tuple[str, str, str]:
        nickname = ""
        finder_uid = ""
        avatar = ""

        if cookies is None and context:
            try:
                cookies = await context.cookies()
            except Exception:
                cookies = []

        if cookies:
            nickname, finder_uid, avatar = self._fetch_nav_profile(cookies)

        if not nickname and page:
            for sel in [".header-entry-mini", "span.header-entry-avatar", ".user-info .name", "span.uname"]:
                try:
                    el = page.locator(sel).first
                    if await el.count() and await el.is_visible():
                        t = (await el.inner_text()).strip()
                        if t and len(t) < 40:
                            nickname = t
                            break
                except Exception:
                    pass

        if not avatar and page:
            for avatar_sel in [
                ".header-entry-avatar img",
                ".header-avatar-wrap img",
                "div.avatar-wrap img",
                "[class*=\"avatar\"] img",
                "img[src*=\"hdslb.com\"]"
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
                if c.get("name") == "DedeUserID" and c.get("value"):
                    finder_uid = str(c.get("value")).strip()
                    break

        if avatar and avatar.startswith("http://"):
            avatar = "https://" + avatar[7:]

        return nickname, finder_uid, avatar

    def format_credentials(self, state_data: dict, finder_uid: str = "") -> dict:
        """为 Playwright cookies 补全 Rust biliup 上传工具所需的 cookie_info / sso / token_info"""
        cookies = state_data.get("cookies", [])
        mid_str = finder_uid
        if not mid_str:
            for c in cookies:
                if c.get("name") == "DedeUserID" and c.get("value"):
                    mid_str = str(c.get("value")).strip()
                    break

        mid_val = int(mid_str) if str(mid_str).isdigit() else 0

        state_data["cookie_info"] = {
            "cookies": cookies
        }
        if "sso" not in state_data:
            state_data["sso"] = []
        if "token_info" not in state_data or not isinstance(state_data.get("token_info"), dict):
            state_data["token_info"] = {
                "mid": mid_val,
                "access_token": "",
                "refresh_token": "",
                "expires_in": 0
            }
        else:
            state_data["token_info"]["mid"] = mid_val

        return state_data

    def extract_from_state(self, state_data: dict) -> Tuple[str, str, str]:
        meta = state_data.get("__account_meta__") or state_data.get("account_meta", {})
        if isinstance(meta, dict) and meta.get("nickname"):
            av = meta.get("avatar", "")
            if av and av.startswith("http://"):
                av = "https://" + av[7:]
            return meta.get("nickname", ""), meta.get("finder_uid", ""), av

        cookies = state_data.get("cookies", [])
        if not cookies and "cookie_info" in state_data and isinstance(state_data["cookie_info"], dict):
            cookies = state_data["cookie_info"].get("cookies", [])
        return self._fetch_nav_profile(cookies)

    def _fetch_nav_profile(self, cookies: list) -> Tuple[str, str, str]:
        nickname = ""
        finder_uid = ""
        avatar = ""

        for c in cookies:
            if c.get("name") == "DedeUserID" and c.get("value"):
                finder_uid = str(c.get("value")).strip()
                break

        if cookies:
            c_dict = {c["name"]: str(c["value"]) for c in cookies if "name" in c and "value" in c}
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "Referer": "https://www.bilibili.com/",
            }
            if requests:
                try:
                    resp = requests.get("https://api.bilibili.com/x/web-interface/nav", headers=headers, cookies=c_dict, timeout=4)
                    if resp.status_code == 200:
                        nav_json = resp.json()
                        if nav_json.get("code") == 0 and isinstance(nav_json.get("data"), dict):
                            data = nav_json["data"]
                            nickname = str(data.get("uname") or "").strip()
                            avatar = str(data.get("face") or "").strip()
                            if not finder_uid:
                                finder_uid = str(data.get("mid") or "").strip()
                except Exception:
                    pass

            if not nickname:
                try:
                    import urllib.request
                    cookie_str = "; ".join([f"{k}={v}" for k, v in c_dict.items()])
                    req = urllib.request.Request("https://api.bilibili.com/x/web-interface/nav", headers={
                        **headers,
                        "Cookie": cookie_str
                    })
                    with urllib.request.urlopen(req, timeout=4) as response:
                        nav_json = json.loads(response.read().decode("utf-8"))
                        if nav_json.get("code") == 0 and isinstance(nav_json.get("data"), dict):
                            data = nav_json["data"]
                            nickname = str(data.get("uname") or "").strip()
                            avatar = str(data.get("face") or "").strip()
                            if not finder_uid:
                                finder_uid = str(data.get("mid") or "").strip()
                except Exception:
                    pass

        if avatar and avatar.startswith("http://"):
            avatar = "https://" + avatar[7:]

        return nickname, finder_uid, avatar
