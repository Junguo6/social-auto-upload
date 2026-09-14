# -*- coding: utf-8 -*-
"""
各平台适配器抽象基类与动态加载工厂
实现平台专属规则（创作者URL、登录态判定、个人资料抽取、凭证格式兼容）与调度层的彻底解耦
"""

import importlib
from abc import ABC
from typing import Tuple, Dict, Optional, Any


class BasePlatformAdapter(ABC):
    platform_id: str = ""
    creator_url: str = ""

    async def is_logged_in(self, page, context) -> bool:
        """判断当前浏览器页面是否处于该平台的已登录态"""
        if not page:
            return False
        return "login" not in page.url.lower()

    async def extract_profile(self, page, context, cookies: list = None) -> Tuple[str, str, str]:
        """从正在运行的浏览器页面中提取该平台的真实昵称、安全唯一 UID 与头像 URL (nickname, finder_uid, avatar)"""
        return "", "", ""

    def format_credentials(self, state_data: dict, finder_uid: str = "") -> dict:
        """平台特有的凭证数据结构补齐或转换（如 B站 biliup 兼容补丁），默认原样返回"""
        return state_data

    def extract_from_state(self, state_data: dict) -> Tuple[str, str, str]:
        """离线从已有 state_data (cookies, localStorage) 中做兜底提取 (nickname, finder_uid, avatar)"""
        return "", "", ""


class DefaultPlatformAdapter(BasePlatformAdapter):
    """兜底默认适配器，用于暂未编写专属适配器的长尾平台"""
    def __init__(self, platform_id: str, creator_url: str = ""):
        self.platform_id = platform_id
        self.creator_url = creator_url or f"https://{platform_id}.com/"


# 平台专属模块映射字典（平台标识 -> 模块导入路径）
_PLATFORM_MODULE_MAP = {
    "douyin": "uploader.douyin_uploader.adapter",
    "xiaohongshu": "uploader.xiaohongshu_uploader.adapter",
    "kuaishou": "uploader.ks_uploader.adapter",
    "bilibili": "uploader.bilibili_uploader.adapter",
    "tencent": "uploader.tencent_uploader.adapter",
}

# 默认 URL 备用映射
_DEFAULT_CREATOR_URLS = {
    "douyin": "https://creator.douyin.com/",
    "xiaohongshu": "https://creator.xiaohongshu.com/",
    "kuaishou": "https://cp.kuaishou.com/",
    "tencent": "https://channels.weixin.qq.com/platform",
    "bilibili": "https://member.bilibili.com/",
    "weibo": "https://weibo.com/",
    "baijiahao": "https://baijiahao.baidu.com/",
    "alipay": "https://b.alipay.com/",
    "hupu": "https://www.hupu.com/",
    "youtube": "https://studio.youtube.com/",
}

_ADAPTER_REGISTRY: Dict[str, BasePlatformAdapter] = {}


def get_platform_adapter(platform: str) -> BasePlatformAdapter:
    """动态获取或实例化指定平台的专属适配器"""
    platform_key = platform.strip().lower()
    if platform_key in _ADAPTER_REGISTRY:
        return _ADAPTER_REGISTRY[platform_key]

    mod_path = _PLATFORM_MODULE_MAP.get(platform_key)
    if mod_path:
        try:
            mod = importlib.import_module(mod_path)
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BasePlatformAdapter)
                    and attr is not BasePlatformAdapter
                ):
                    adapter_inst = attr()
                    _ADAPTER_REGISTRY[platform_key] = adapter_inst
                    return adapter_inst
        except Exception as err:
            import sys
            sys.stderr.write(f"[WARNING] 无法加载平台适配器 {mod_path}: {err}\n")

    # 未找到专属适配器时使用兜底适配器
    fallback_url = _DEFAULT_CREATOR_URLS.get(platform_key, f"https://{platform_key}.com/")
    default_adapter = DefaultPlatformAdapter(platform_key, fallback_url)
    _ADAPTER_REGISTRY[platform_key] = default_adapter
    return default_adapter
