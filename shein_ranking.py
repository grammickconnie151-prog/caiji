"""Conservative SHEIN UK ranking page link discovery and diagnostics."""
from urllib.parse import urlparse, urljoin
from html.parser import HTMLParser
import re
import requests

PATTERN = re.compile(r"/(?:[^/?#]+-)?p-\d+\.html(?:[?#]|$)", re.I)
HOSTS = {"www.shein.co.uk", "m.shein.co.uk"}

class ProductLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        for key in ("href", "data-href"):
            value = d.get(key) or ""
            if PATTERN.search(value):
                self.links.add(value)

def discover_ranking(url):
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or parsed.hostname not in HOSTS or parsed.path != "/ranking_list":
        raise ValueError("请输入 SHEIN UK 的 HTTPS ranking_list 榜单链接")
    response = requests.get(url, timeout=20, headers={"Accept": "text/html", "User-Agent": "ProductResearch/0.1"})
    if response.status_code in (403, 429):
        raise RuntimeError(f"网站限制访问（HTTP {response.status_code}），请使用获授权的数据来源")
    response.raise_for_status()
    parser = ProductLinks()
    parser.feed(response.text)
    # HTML can contain product URLs in embedded data, not only anchor tags.
    raw = re.findall(r'(?:https?:)?//(?:www\.|m\.)?shein\.co\.uk/[^"\s<>\\]+?-p-\d+\.html|/[^"\s<>\\]+?-p-\d+\.html', response.text, re.I)
    candidates = parser.links.union(raw)
    links = sorted({urljoin(url, p).split("?")[0] for p in candidates if urlparse(urljoin(url,p)).hostname in HOSTS})
    return links
