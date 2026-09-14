# -*- coding: utf-8 -*-
"""
快手创作者平台适配器
管理快手创作者服务主页 URL、登录态识别、真实昵称与快手号提取
"""

import re
from typing import Tuple
from uploader.base_adapter import BasePlatformAdapter


class KuaishouPlatformAdapter(BasePlatformAdapter):
    platform_id = "kuaishou"
    creator_url = "https://cp.kuaishou.com/"

    async def is_logged_in(self, page, context) -> bool:
        # 1. 优先通过 Context Cookies 进行毫秒级精准判活 (扫码确认瞬间必定写入)
        if context:
            try:
                cookies = await context.cookies()
                has_user = any(c.get("name") in ["userId", "wid"] and str(c.get("value", "")).strip() != "" for c in cookies)
                has_token = any(
                    c.get("name") in ["passToken", "kuaishou.web.cp.api_st", "ks_onvideo_token"]
                    and len(c.get("value", "")) > 5
                    for c in cookies
                )
                if has_user and has_token:
                    return True
            except Exception:
                pass

        # 2. 如果 page 存在，通过 DOM 检测快手创作者服务内部真实用户信息元素 (注意不加 is_visible 限制)
        if page:
            try:
                has_valid_name = await page.evaluate("""() => {
                    const selectors = [
                        '.user__name',
                        '[class*="user__name"]',
                        'span.user-name',
                        'div.user-name',
                        '.user-info .name'
                    ];
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            const t = (el.innerText || el.textContent || '').trim();
                            if (t && t !== '登录' && t !== '立即登录' && t.length < 50) {
                                return true;
                            }
                        }
                    }
                    return false;
                }""")
                if has_valid_name:
                    return True
            except Exception:
                pass

            # 3. 检查是否有快手头像
            try:
                has_head = await page.evaluate("""() => {
                    const img = document.querySelector('img.user__head, [class*="user__head"]');
                    if (img && img.src && (img.src.includes('kwimgs.com') || img.src.includes('yximgs.com'))) {
                        return true;
                    }
                    return false;
                }""")
                if has_head:
                    return True
            except Exception:
                pass

        return False

    async def extract_profile(self, page, context, cookies: list = None) -> Tuple[str, str, str]:
        nickname = ""
        finder_uid = ""
        avatar = ""

        # 1. 优先从 cookies 中提取最准确的快手官方数字 UID (userId)，备选 wid
        cookie_list = cookies or []
        if not cookie_list and context:
            try:
                cookie_list = await context.cookies()
            except Exception:
                pass

        for c in cookie_list:
            if c.get("name") == "userId" and c.get("value"):
                finder_uid = str(c.get("value")).strip()
                break
        if not finder_uid:
            for c in cookie_list:
                if c.get("name") == "wid" and c.get("value"):
                    finder_uid = str(c.get("value")).strip()
                    break

        # 2. 获取用于提取 DOM 的目标页面 (若当前页面已关闭或为空，利用有效会话 context 启动后台页面自愈抓取)
        target_page = page
        need_close_temp = False
        if (target_page is None or target_page.is_closed()) and context:
            try:
                target_page = await context.new_page()
                await target_page.goto(self.creator_url, wait_until="domcontentloaded")
                need_close_temp = True
            except Exception:
                target_page = None

        if target_page and not target_page.is_closed():
            try:
                dom_info = await target_page.evaluate("""() => {
                    let name = '';
                    let avatar = '';
                    const nameSels = [
                        '.user__name',
                        '[class*="user__name"]',
                        'span.user-name',
                        'div.user-name',
                        '.user-info .name',
                        'div.header-user-info span',
                        '.user .name'
                    ];
                    for (const sel of nameSels) {
                        const el = document.querySelector(sel);
                        if (el) {
                            const t = (el.innerText || el.textContent || '').trim();
                            if (t && t !== '登录' && t !== '立即登录' && t.length < 50) {
                                name = t;
                                break;
                            }
                        }
                    }

                    const imgSels = [
                        'img.user__head',
                        '[class*="user__head"]',
                        '.user img',
                        'div.user-avatar img',
                        'header [class*="avatar"] img',
                        'img[src*="kwimgs.com"]',
                        'img[src*="yximgs.com"]'
                    ];
                    for (const sel of imgSels) {
                        const img = document.querySelector(sel);
                        if (img) {
                            const src = img.src || img.getAttribute('src') || '';
                            if (src && (src.includes('kwimgs.com') || src.includes('yximgs.com') || src.includes('uhead') || src.includes('avatar'))) {
                                avatar = src.trim();
                                break;
                            }
                        }
                    }
                    return { name, avatar };
                }""")
                if dom_info:
                    if not nickname and dom_info.get("name"):
                        nickname = dom_info["name"]
                    if not avatar and dom_info.get("avatar"):
                        avatar = dom_info["avatar"]
            except Exception:
                pass

            # 若尚未拿到昵称或头像，且页面仍在加载/跳转中，等待 1.5 秒后再次尝试
            if (not nickname or not avatar) and not target_page.is_closed():
                try:
                    await target_page.wait_for_timeout(1500)
                    retry_info = await target_page.evaluate("""() => {
                        let name = '';
                        let avatar = '';
                        const nameEl = document.querySelector('.user__name, [class*="user__name"], .user-name, [class*="user-name"]');
                        if (nameEl) {
                            const t = (nameEl.innerText || nameEl.textContent || '').trim();
                            if (t && t !== '登录' && t !== '立即登录') name = t;
                        }
                        const imgEl = document.querySelector('img.user__head, [class*="user__head"], .user img');
                        if (imgEl) {
                            const s = imgEl.src || imgEl.getAttribute('src') || '';
                            if (s) avatar = s.trim();
                        }
                        return { name, avatar };
                    }""")
                    if retry_info:
                        if not nickname and retry_info.get("name"):
                            nickname = retry_info["name"]
                        if not avatar and retry_info.get("avatar"):
                            avatar = retry_info["avatar"]
                except Exception:
                    pass

        if need_close_temp and target_page and not target_page.is_closed():
            try:
                await target_page.close()
            except Exception:
                pass

        # 3. 兜底格式化
        if avatar and avatar.startswith("http://"):
            avatar = "https://" + avatar[7:]

        return nickname, finder_uid, avatar

    def extract_from_state(self, state_data: dict) -> Tuple[str, str, str]:
        nickname = ""
        finder_uid = ""
        avatar = ""
        meta = state_data.get("__account_meta__") or state_data.get("account_meta", {})
        if isinstance(meta, dict):
            nickname = meta.get("nickname", "")
            finder_uid = meta.get("finder_uid", "")
            avatar = meta.get("avatar", "")

        # 优先校准 UID：从 cookies 中获取权威 userId，备选 wid
        for c in state_data.get("cookies", []):
            if c.get("name") == "userId" and c.get("value"):
                finder_uid = str(c.get("value")).strip()
                break
        if not finder_uid:
            for c in state_data.get("cookies", []):
                if c.get("name") == "wid" and c.get("value"):
                    finder_uid = str(c.get("value")).strip()
                    break

        if nickname == "auto" or (finder_uid and nickname == finder_uid):
            nickname = ""

        if avatar and avatar.startswith("http://"):
            avatar = "https://" + avatar[7:]

        return nickname, finder_uid, avatar
