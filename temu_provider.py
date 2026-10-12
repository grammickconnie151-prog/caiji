"""Optional Temu data-provider adapter. Review provider terms and data rights before use."""
import requests

ACTOR="lukehunter~temu-scraper"
def search_temu(token, term, max_items=20):
    if not token:
        raise ValueError("请在 Streamlit Secrets 配置 APIFY_TOKEN")
    term=term.strip()
    if not term: raise ValueError("请输入关键词")
    max_items=max(1,min(int(max_items),50))
    url=f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items"
    response=requests.post(url,headers={"Authorization":f"Bearer {token}"},
                           json={"searchTerms":[term],"startUrls":[],"maxItems":max_items},
                           timeout=115)
    response.raise_for_status()
    records=response.json()
    if not isinstance(records,list):
        raise ValueError("数据供应商未返回商品列表")
    return records
