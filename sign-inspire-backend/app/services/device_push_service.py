"""
设备推送执行服务：向线下广告屏幕发送播放指令
Device 指线下数字标牌设备，不是用户手机
"""
import os
from typing import Optional

import httpx

from app.schemas.decide import AdAsset


def get_device_url(device_id: str) -> Optional[str]:
    """
    根据 device_id 解析设备控制端点 URL。
    支持：
    1. 环境变量 DEVICE_{id}_URL（如 DEVICE_sign_001_URL）
    2. 通用 DEVICE_BASE_URL + /{device_id}/update
    3. 默认 http://localhost:8080/update（开发测试用）
    """
    import re
    # 环境变量 key 通常不支持特殊字符，将 device_id 转为合法形式
    safe_id = re.sub(r"[^a-zA-Z0-9]", "_", device_id).upper()
    env_key = f"DEVICE_{safe_id}_URL"
    url = os.getenv(env_key)
    if url:
        return url.rstrip("/")

    base = os.getenv("DEVICE_BASE_URL", "http://localhost:8080")
    base = base.rstrip("/")
    return f"{base}/update"


def push_content_to_device(device_id: str, ad_content: AdAsset, timeout: float = 5.0) -> bool:
    """
    向设备推送广告内容。

    向屏幕设备的控制端点发送 POST 请求，Payload：
    {"action": "play", "url": ad_content.content_url}

    返回 True 表示推送成功，False 表示失败。
    """
    if not device_id or not ad_content:
        return False

    url = get_device_url(device_id)
    if not url:
        return False

    payload = {
        "action": "play",
        "url": ad_content.content_url or "",
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload)
            if resp.status_code in (200, 201, 204):
                return True
            print(f"⚠️ [Device Push] {device_id} 返回 {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"⚠️ [Device Push] {device_id} 请求失败: {e}")
        return False
