"""Experimental browser-rendered SHEIN listing discovery; no evasion or authentication."""
import re
import shutil
from urllib.parse import urlparse, urljoin
from playwright.sync_api import sync_playwright, TimeoutError as BrowserTimeout
from shein_ranking import PATTERN, HOSTS

def discover_dynamic(url, max_items=100):
    parsed=urlparse(url.strip())
    if parsed.scheme!="https" or parsed.hostname not in HOSTS or parsed.path!="/ranking_list":
        raise ValueError("只支持 SHEIN UK HTTPS 榜单网址")
    with sync_playwright() as pw:
        system_chromium = shutil.which("chromium") or shutil.which("chromium-browser")
        browser=pw.chromium.launch(headless=True, executable_path=system_chromium, args=["--no-sandbox"])
        try:
            page=browser.new_page(viewport={"width":1400,"height":900},locale="en-GB")
            response=page.goto(url, wait_until="domcontentloaded",timeout=30000)
            if response and response.status in (403,429):
                raise RuntimeError(f"站点限制访问 HTTP {response.status}，已停止")
            page.wait_for_timeout(3000)
            found=set()
            for _ in range(5):
                for link in page.locator("a[href]").evaluate_all("(els) => els.map(e => e.href)"):
                    if PATTERN.search(link) and urlparse(link).hostname in HOSTS:
                        found.add(link.split("?")[0])
                if len(found)>=max_items:break
                page.mouse.wheel(0,1600)
                page.wait_for_timeout(1200)
            return sorted(found)[:max_items], page.title()
        except BrowserTimeout:
            raise RuntimeError("页面加载超时")
        finally:
            browser.close()
