"""SHEIN ranking-page discovery prototype. Only accesses publicly available pages; stops on restrictions."""
from urllib.parse import urlparse, urljoin
from html.parser import HTMLParser
import re
import requests

class ProductLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()
    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        url = dict(attrs).get("href", "")
        if re.search(r"/[^/?]*-p-\d+\.html|/p-\d+\.html", url):
            self.links.add(url)

def discover_ranking(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ("www.shein.co.uk","m.shein.co.uk"):
        raise ValueError("仅允许 SHEIN UK 榜单 HTTPS 链接")
    if parsed.path != "/ranking_list":
        raise ValueError("当前只支持 ranking_list 页面")
    response = requests.get(url, timeout=20, headers={"Accept":"text/html"})
    if response.status_code in (403, 429):
        raise RuntimeError("站点限制访问，已停止。请使用获授权数据来源。")
    response.raise_for_status()
    parser = ProductLinks()
    parser.feed(response.text)
    return sorted({urljoin(url, path).split("?")[0] for path in parser.links
                   if urlparse(urljoin(url,path)).hostname in ("www.shein.co.uk","m.shein.co.uk")})
