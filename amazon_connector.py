"""Connects to a separately hosted Amazon API; does not bypass access controls."""
import re
from urllib.parse import urlparse
import requests

def extract_asin(value):
    value = value.strip()
    if re.fullmatch(r"[A-Za-z0-9]{10}", value):
        return value.upper()
    host = (urlparse(value).hostname or "").lower()
    match = re.search(r"/(?:dp|gp/product)/([A-Za-z0-9]{10})(?:[/?]|$)", value, re.I)
    if match and (host == "amazon.com" or ".amazon." in host):
        return match.group(1).upper()
    raise ValueError("需要10位 ASIN 或 Amazon 商品链接")

def fetch_product(value, base_url, api_key=None):
    if not base_url or not base_url.startswith("https://"):
        raise ValueError("需要管理员配置 HTTPS AMAZON_API_BASE_URL")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    response = requests.get(base_url.rstrip("/") + "/products/details",
                            params={"product": extract_asin(value)},
                            headers=headers, timeout=25)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("接口未返回 JSON 对象")
    payload = payload.get("data", payload)
    if not isinstance(payload, dict) or not (payload.get("asin") or payload.get("title")):
        raise ValueError("未读取到有效商品")
    return payload
