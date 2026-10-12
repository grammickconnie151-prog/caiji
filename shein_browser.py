"""SHEIN UK browser diagnostic; does not circumvent access controls."""
import re
import shutil
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from shein_ranking import PATTERN, HOSTS

def diagnose_ranking(url, max_items=100):
    parsed=urlparse(url.strip())
    if parsed.scheme!="https" or parsed.hostname not in HOSTS or parsed.path!="/ranking_list":
        raise ValueError("仅支持 SHEIN UK HTTPS ranking_list 网址")
    result={"status":None,"final_url":"","title":"","signals":[],"links":[],"screenshot":None}
    with sync_playwright() as pw:
        executable=shutil.which("chromium") or shutil.which("chromium-browser")
        browser=pw.chromium.launch(headless=True, executable_path=executable, args=["--no-sandbox"])
        try:
            page=browser.new_page(viewport={"width":1365,"height":900},locale="en-GB")
            response=page.goto(url,wait_until="domcontentloaded",timeout=30000)
            result["status"]=response.status if response else None
            page.wait_for_timeout(3000)
            result["final_url"]=page.url
            result["title"]=page.title()
            body=page.locator("body").inner_text(timeout=10000)[:15000].lower()
            patterns={"可能有验证码":r"captcha|verify you are human|security check|human verification",
                      "可能被拒绝访问":r"access denied|forbidden|unusual traffic|request blocked",
                      "可能需要登录":r"sign in to continue|log in to continue"}
            result["signals"]=[label for label,pat in patterns.items() if re.search(pat,body)]
            if "/risk/action/limit" in urlparse(result["final_url"]).path:\n                result["signals"].append("SHEIN 风控限制页（实际页面显示 403）")\n            if result["status"] in (403,429):
                result["signals"].append(f"HTTP {result['status']}：限制访问")
            if not result["signals"] and result["status"] not in (403,429):
                found=set()
                for _ in range(5):
                    links=page.locator("a[href]").evaluate_all("(els) => els.map(e => e.href)")
                    for link in links:
                        if PATTERN.search(link) and urlparse(link).hostname in HOSTS:
                            found.add(link.split("?")[0])
                    if len(found)>=max_items:break
                    page.mouse.wheel(0,1600)
                    page.wait_for_timeout(1100)
                result["links"]=sorted(found)[:max_items]
            result["screenshot"]=page.screenshot(type="png",full_page=False)
            return result
        finally:
            browser.close()
