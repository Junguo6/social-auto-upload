import asyncio
import hashlib
import json
import time
import urllib.parse
from pathlib import Path
from typing import Tuple
from uploader.base_adapter import BasePlatformAdapter

try:
    import requests
except ImportError:
    requests = None


class BilibiliPlatformAdapter(BasePlatformAdapter):
    platform_id = "bilibili"
    creator_url = "https://member.bilibili.com/"

    @staticmethod
    def get_tv_qrcode():
        app_key = "4409e2ce8ffd12b8"
        app_sec = "59b43e04ad6965f34319062b478f83dd"
        ts = int(time.time())
        params = {"appkey": app_key, "local_id": "0", "ts": str(ts)}
        sorted_items = sorted(params.items())
        query = urllib.parse.urlencode(sorted_items)
        params["sign"] = hashlib.md5((query + app_sec).encode("utf-8")).hexdigest()
        
        session = requests or __import__("requests")
        resp = session.post(
            "https://passport.bilibili.com/x/passport-tv-login/qrcode/auth_code",
            data=params,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"获取B站授权二维码失败: {data.get('message')}")
        auth_code = data["data"]["auth_code"]
        auth_url = data["data"]["url"]

        import qrcode
        import qrcode.image.svg
        img = qrcode.make(auth_url, image_factory=qrcode.image.svg.SvgPathImage)
        svg_code = img.to_string(encoding="unicode")
        return auth_code, auth_url, svg_code

    @staticmethod
    def poll_tv_status(auth_code):
        app_key = "4409e2ce8ffd12b8"
        app_sec = "59b43e04ad6965f34319062b478f83dd"
        ts = int(time.time())
        params = {"appkey": app_key, "auth_code": auth_code, "local_id": "0", "ts": str(ts)}
        sorted_items = sorted(params.items())
        query = urllib.parse.urlencode(sorted_items)
        params["sign"] = hashlib.md5((query + app_sec).encode("utf-8")).hexdigest()

        session = requests or __import__("requests")
        resp = session.post(
            "https://passport.bilibili.com/x/passport-tv-login/qrcode/poll",
            data=params,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        return resp.json()

    @staticmethod
    def render_auth_page(svg_code: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>哔哩哔哩客户端授权登录</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: linear-gradient(135deg, #f0f3f8 0%, #e8edf5 100%);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            color: #18191c;
        }}
        .auth-card {{
            background: #ffffff;
            width: 440px;
            padding: 40px 32px;
            border-radius: 20px;
            box-shadow: 0 16px 40px rgba(0, 174, 236, 0.08), 0 4px 12px rgba(0,0,0,0.03);
            text-align: center;
            border: 1px solid rgba(251, 114, 153, 0.15);
        }}
        .brand-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(251, 114, 153, 0.1);
            color: #fb7299;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 16px;
        }}
        .title {{
            font-size: 22px;
            font-weight: 700;
            color: #18191c;
            margin-bottom: 8px;
        }}
        .subtitle {{
            font-size: 14px;
            color: #61666d;
            margin-bottom: 24px;
            line-height: 1.5;
        }}
        .qr-wrapper {{
            width: 240px;
            height: 240px;
            margin: 0 auto 24px;
            padding: 12px;
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.06);
            border: 1px solid #e3e5e7;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .qr-wrapper svg {{
            width: 100%;
            height: 100%;
        }}
        .status-box {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            font-size: 14px;
            color: #00aeec;
            font-weight: 500;
        }}
        .dot-flashing {{
            position: relative;
            width: 8px;
            height: 8px;
            border-radius: 5px;
            background-color: #00aeec;
            animation: dotFlashing 1s infinite linear alternate;
        }}
        @keyframes dotFlashing {{
            0% {{ opacity: 0.2; transform: scale(0.8); }}
            100% {{ opacity: 1; transform: scale(1.2); }}
        }}
        .footer-note {{
            margin-top: 24px;
            font-size: 12px;
            color: #9499a0;
        }}
    </style>
</head>
<body>
    <div class="auth-card">
        <div class="brand-badge">bilibili × biliup 直传授权</div>
        <h1 class="title">扫码授权哔哩哔哩</h1>
        <p class="subtitle">请打开手机 <b>哔哩哔哩 App</b> 扫码<br>并在手机上点击【确认授权】</p>
        <div class="qr-wrapper" id="qrContainer">
            {svg_code}
        </div>
        <div class="status-box" id="statusBox">
            <div class="dot-flashing" id="dotAnim"></div>
            <span id="statusText">等待手机扫码中...</span>
        </div>
        <div class="footer-note">授权成功后视窗将自动同步并关闭</div>
    </div>
</body>
</html>"""

    async def run_tv_login_flow(self, page, context, account_file: Path, current_account_name: str) -> dict:
        """在拉起的独立视窗中渲染官方 TV 客户端授权二维码，实现零终端输入的自动登录闭环"""
        auth_code, auth_url, svg_code = self.get_tv_qrcode()
        html = self.render_auth_page(svg_code)
        await page.set_content(html)

        last_refresh_time = time.time()
        while not page.is_closed():
            # 超过 170 秒二维码临近过期，自动无感重新生成
            if time.time() - last_refresh_time > 170:
                try:
                    auth_code, auth_url, svg_code = self.get_tv_qrcode()
                    html = self.render_auth_page(svg_code)
                    await page.set_content(html)
                    last_refresh_time = time.time()
                except Exception:
                    pass

            poll_res = self.poll_tv_status(auth_code)
            code = poll_res.get("code")

            if code == 86090:
                # 已扫码未确认
                try:
                    await page.evaluate("""() => {
                        const t = document.getElementById('statusText');
                        if (t) {
                            t.innerText = '📱 手机已扫码，请在手机上点击【确认授权】';
                            t.style.color = '#fb7299';
                        }
                    }""")
                except Exception:
                    pass

            elif code == 86038:
                # 二维码失效，自动刷新
                try:
                    auth_code, auth_url, svg_code = self.get_tv_qrcode()
                    html = self.render_auth_page(svg_code)
                    await page.set_content(html)
                    last_refresh_time = time.time()
                except Exception:
                    pass

            elif code == 0:
                # 授权成功！
                data = poll_res.get("data") or {}
                token_info = {
                    "access_token": data.get("access_token", ""),
                    "refresh_token": data.get("refresh_token", ""),
                    "expires_in": data.get("expires_in", 0),
                    "mid": data.get("mid", 0)
                }
                cookie_info = data.get("cookie_info") or {"cookies": []}
                sso = data.get("sso") or []

                # 保存标准 biliup 结构
                bili_data = {
                    "token_info": token_info,
                    "cookie_info": cookie_info,
                    "sso": sso,
                    "platform": "BiliTV"
                }

                # 提取用户名和头像
                cookies_list = cookie_info.get("cookies", [])
                nickname, finder_uid, avatar = self._fetch_nav_profile(cookies_list)
                if not finder_uid:
                    finder_uid = str(token_info.get("mid") or "")

                # 页面展示成功状态
                try:
                    await page.evaluate("""() => {
                        const b = document.getElementById('statusBox');
                        if (b) {
                            b.innerHTML = '<span style="color:#00aeec;font-weight:bold;">🎉 授权成功！正在保存凭证并关闭视窗...</span>';
                        }
                        const c = document.getElementById('qrContainer');
                        if (c) {
                            c.style.borderColor = '#00aeec';
                            c.style.background = 'rgba(0,174,236,0.05)';
                        }
                    }""")
                except Exception:
                    pass

                # 存盘并重命名
                account_path = Path(account_file)
                account_path.parent.mkdir(parents=True, exist_ok=True)
                with open(account_path, "w", encoding="utf-8") as f:
                    json.dump(bili_data, f, ensure_ascii=False, indent=2)

                from utils.account_meta import inject_account_meta_and_rename
                final_acc, final_path, meta_dict = inject_account_meta_and_rename(
                    platform="bilibili",
                    account_file=account_path,
                    nickname=nickname,
                    finder_uid=finder_uid,
                    avatar=avatar,
                    current_account_name=current_account_name,
                    state_data=bili_data
                )

                # 同步回写完整的 bili_data
                try:
                    with open(final_path, "r", encoding="utf-8") as f:
                        saved_f = json.load(f)
                    saved_f["token_info"] = token_info
                    saved_f["cookie_info"] = cookie_info
                    saved_f["sso"] = sso
                    saved_f["platform"] = "BiliTV"
                    with open(final_path, "w", encoding="utf-8") as f:
                        json.dump(saved_f, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

                meta_dict["success"] = True
                meta_dict["account_name"] = final_acc
                meta_dict["account_file"] = final_path
                return meta_dict

            await asyncio.sleep(1)

        return {"success": False, "message": "视窗已关闭，未完成扫码"}

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
        if not cookies and "cookie_info" in state_data and isinstance(state_data["cookie_info"], dict):
            cookies = state_data["cookie_info"].get("cookies", [])

        mid_str = finder_uid
        if not mid_str:
            for c in cookies:
                if c.get("name") == "DedeUserID" and c.get("value"):
                    mid_str = str(c.get("value")).strip()
                    break

        mid_val = int(mid_str) if str(mid_str).isdigit() else 0

        state_data["cookies"] = cookies
        state_data["cookie_info"] = {
            "cookies": cookies
        }
        if "sso" not in state_data:
            state_data["sso"] = []
        if "platform" not in state_data or not state_data.get("platform"):
            state_data["platform"] = "BiliTV"
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
