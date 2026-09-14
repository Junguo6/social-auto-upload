# -*- coding: utf-8 -*-
"""
多平台账号资料持久化、纯 ASCII 安全更名与 __account_meta__ 元数据注入工具
具体平台的登录判定、资料抽取与凭证转换已完全委托给各平台专属 adapter
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from uploader.base_adapter import get_platform_adapter


def safe_ascii_uid(raw_id: str) -> str:
    """过滤特殊字符，只保留字母、数字、下划线和连字符，确保磁盘文件名纯 ASCII 安全"""
    if not raw_id:
        return ""
    cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "", str(raw_id).strip())
    cleaned = cleaned.strip("_-")
    return cleaned


# 兼容层快捷函数（转发给 bilibili 适配器）
async def fetch_bilibili_nav_meta(cookies: list) -> Tuple[str, str]:
    adapter = get_platform_adapter("bilibili")
    if hasattr(adapter, "_fetch_nav_profile"):
        return adapter._fetch_nav_profile(cookies)
    return "", ""


def format_bilibili_biliup_state(state_data: dict, mid: str = "") -> dict:
    adapter = get_platform_adapter("bilibili")
    return adapter.format_credentials(state_data, mid)


async def extract_account_meta_from_page(platform: str, page, cookies: list = None) -> Tuple[str, str, str]:
    """从浏览器当前页面委托平台专属适配器探测真实昵称、平台安全 UID 与头像 URL"""
    adapter = get_platform_adapter(platform)
    context = page.context if page else None
    res = await adapter.extract_profile(page, context, cookies)
    if len(res) == 3:
        return res[0], res[1], res[2]
    return res[0], res[1], ""


def inject_account_meta_and_rename(
    platform: str,
    account_file: str | Path,
    nickname: str = "",
    finder_uid: str = "",
    avatar: str = "",
    current_account_name: str = "auto",
    state_data: Optional[dict] = None
) -> Tuple[str, str, dict]:
    """
    注入 __account_meta__ 元数据，并在 account_name 为 auto 时，根据 safe_uid 自动重命名文件为:
    cookies/{platform}_{safe_uid}.json (纯 ASCII 磁盘安全)。
    返回: (final_account_name, final_account_file, meta_dict)
    """
    account_path = Path(account_file)
    account_path.parent.mkdir(parents=True, exist_ok=True)

    if state_data is None:
        if account_path.exists():
            try:
                with open(account_path, "r", encoding="utf-8") as f:
                    state_data = json.load(f)
            except Exception:
                state_data = {}
        else:
            state_data = {}

    adapter = get_platform_adapter(platform)

    # 1. 兜底提取：若外部未传昵称、UID 或头像，委托平台专属适配器从 state_data 中提取
    if not nickname or not finder_uid or not avatar:
        st_res = adapter.extract_from_state(state_data)
        st_nick = st_res[0] if len(st_res) > 0 else ""
        st_uid = st_res[1] if len(st_res) > 1 else ""
        st_avatar = st_res[2] if len(st_res) > 2 else ""

        if not nickname and st_nick:
            nickname = st_nick
        if not finder_uid and st_uid:
            finder_uid = st_uid
        if not avatar and st_avatar:
            avatar = st_avatar

    safe_uid = safe_ascii_uid(finder_uid)

    # 2. 凭证格式化：调用平台适配器（例如 B站自动转换补齐 biliup 所需结构）
    state_data = adapter.format_credentials(state_data, safe_uid or finder_uid)

    # 3. 决策文件名与 account_name
    stem_name = account_path.stem
    prefix = f"{platform}_"
    if stem_name.startswith(prefix):
        parsed_acc = stem_name[len(prefix):]
    else:
        parsed_acc = stem_name

    final_account_name = current_account_name or parsed_acc
    final_account_path = account_path

    is_auto = final_account_name.lower() in ["auto", "default", ""] or parsed_acc.lower() in ["auto", "default", ""]
    if is_auto and safe_uid:
        final_account_name = safe_uid
        final_account_path = account_path.parent / f"{platform}_{safe_uid}.json"

    if avatar and avatar.startswith("http://"):
        avatar = "https://" + avatar[7:]

    meta_dict = {
        "success": True,
        "nickname": nickname or final_account_name,
        "finder_uid": finder_uid or safe_uid,
        "avatar": avatar or "",
        "account_name": final_account_name,
        "platform": platform,
        "updated_at": datetime.now().isoformat()
    }

    state_data["__account_meta__"] = meta_dict

    # 4. 保存新文件
    with open(final_account_path, "w", encoding="utf-8") as f:
        json.dump(state_data, f, ensure_ascii=False, indent=2)

    # 5. 若发生重命名且原文件与新文件不同，清理旧的临时文件
    if str(final_account_path) != str(account_path) and account_path.exists():
        try:
            os.remove(account_path)
        except Exception:
            pass

    return final_account_name, str(final_account_path), meta_dict
