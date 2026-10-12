import io, json, csv, re, zipfile, os
from pathlib import Path
import pandas as pd
import streamlit as st
from amazon_connector import fetch_product

st.set_page_config(page_title="跨平台商品采集工作台", layout="wide")
st.title("跨平台商品采集工作台")
st.caption("Amazon · SHEIN · Temu ｜ Excel · SKC/SKU 图片归档")
st.warning("本版支持导入和整理；Amazon 查询仅在管理员配置外部 API 后生效。SHEIN、Temu 实时采集尚未接入。")
COLS = ["platform","product_id","url","title","category","currency","price","skc","sku","color","size","stock","main_image_url","detail_image_urls","variant_image_url"]
def safe(x):
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", str(x or "").strip()).strip(" ._")[:70] or "未标注"
def normalize(obj, platform):
    if isinstance(obj, dict):
        obj = obj.get("products", obj.get("items", obj.get("data", [obj])))
    if isinstance(obj, dict): obj = [obj]
    if not isinstance(obj, list): raise ValueError("JSON 应为商品数组")
    out = []
    for p in obj:
        if not isinstance(p, dict): continue
        variants = p.get("variants") or p.get("skus") or [{}]
        if not isinstance(variants, list): variants = [{}]
        images = p.get("images") or []
        if not isinstance(images, list): images = []
        images = [i.get("url", i.get("link","")) if isinstance(i, dict) else str(i) for i in images]
        for v in variants:
            if not isinstance(v, dict): v = {}
            row = {"platform":p.get("platform",platform),"product_id":p.get("product_id",p.get("asin",p.get("id",""))),
                   "url":p.get("url",p.get("link","")),"title":p.get("title",p.get("name","")),
                   "category":p.get("category",""),"currency":p.get("currency",""),
                   "price":v.get("price",p.get("price","")),"skc":v.get("skc",p.get("skc","")),
                   "sku":v.get("sku",v.get("asin","")),"color":v.get("color",p.get("color","")),
                   "size":v.get("size",p.get("size","")),"stock":v.get("stock",p.get("stock","")),
                   "main_image_url":p.get("main_image_url",images[0] if images else ""),
                   "detail_image_urls":";".join(images[1:]),"variant_image_url":v.get("image_url","")}
            out.append(row)
    return out

platform = st.selectbox("数据来源",["Amazon","SHEIN","Temu"])
uploaded = st.file_uploader("上传 CSV 或 JSON 商品资料",type=["csv","json"])
st.download_button("下载 CSV 模板",",".join(COLS)+"\n","template.csv","text/csv")
api_url = os.getenv("AMAZON_API_BASE_URL","")
api_key = os.getenv("AMAZON_API_KEY","")
try:
    api_url = st.secrets.get("AMAZON_API_BASE_URL",api_url)
    api_key = st.secrets.get("AMAZON_API_KEY",api_key)
except Exception:
    pass
st.subheader("Amazon 商品查询")
if not api_url:
    st.info("Amazon API 尚未部署或配置，因此此处不能实时抓取；可先试用文件导入。")
else:
    with st.form("amazon"):
        raw = st.text_area("ASIN 或 Amazon 商品链接（每行一个，最多10条）")
        go = st.form_submit_button("查询")
    if go:
        records=[]
        for value in [v.strip() for v in raw.splitlines() if v.strip()][:10]:
            try: records.extend(normalize([fetch_product(value,api_url,api_key)],"Amazon"))
            except Exception as exc: st.error(f"{value}: {exc}")
        st.session_state["api_records"]=records
try:
    if uploaded:
        if uploaded.name.lower().endswith(".json"):
            records = normalize(json.load(uploaded),"Amazon" if platform=="Amazon" else platform)
        else:
            records = list(csv.DictReader(io.StringIO(uploaded.getvalue().decode("utf-8-sig"))))
    else:
        records = st.session_state.get("api_records",[])
    frame = pd.DataFrame(records)
    for c in COLS:
        if c not in frame: frame[c]=""
    frame = frame[COLS].fillna("").astype(str)
except Exception as exc:
    st.error(f"读取资料失败：{exc}")
    st.stop()
st.subheader("编辑商品 SKU / SKC 资料")
edited = st.data_editor(frame, num_rows="dynamic", hide_index=True, use_container_width=True)
buf = io.BytesIO()
with pd.ExcelWriter(buf,engine="xlsxwriter") as writer:
    edited.to_excel(writer,index=False,sheet_name="商品SKU明细")
    sheet=writer.sheets["商品SKU明细"]
    sheet.freeze_panes(1,0)
    sheet.set_column(0,len(COLS)-1,26)
st.download_button("导出 Excel",buf.getvalue(),"product_sku.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.subheader("SHEIN UK 榜单链接发现（试验）")
ranking_url = st.text_input("粘贴 SHEIN UK ranking_list 链接")
if st.button("尝试发现商品链接"):
    if not ranking_url.strip():
        st.error("请先填写链接")
    else:
        try:
            from shein_ranking import discover_ranking
            links = discover_ranking(ranking_url.strip())
            st.session_state["ranking_links"] = links
            if links:
                st.success(f"从静态页面发现 {len(links)} 个候选商品链接")
            else:
                st.warning("静态页面未发现链接。榜单可能依赖动态加载；当前没有启用浏览器自动抓取。")
        except Exception as exc:
            st.error(f"发现失败：{exc}")
if st.session_state.get("ranking_links"):
    found = pd.DataFrame({"platform":"SHEIN","url":st.session_state["ranking_links"]})
    st.dataframe(found,use_container_width=True)
    st.download_button("下载候选链接 CSV",found.to_csv(index=False).encode("utf-8-sig"),"shein_links.csv","text/csv")

st.subheader("SHEIN 动态浏览器采集（实验）")
st.caption("需要云端已安装 Chromium；如果站点拒绝访问则停止，不处理验证码。")
dynamic_url = st.text_input("SHEIN UK 榜单网址（浏览器模式）", key="dynamic_url")
if st.button("使用浏览器尝试提取商品链接"):
    if not dynamic_url:
        st.warning("请输入榜单网址")
    else:
        try:
            from shein_browser import discover_dynamic
            links, title = discover_dynamic(dynamic_url)
            st.write("页面标题：", title)
            if links:
                st.success(f"发现 {len(links)} 个候选链接")
                st.dataframe(pd.DataFrame({"url":links}))
                st.download_button("下载链接 CSV",pd.DataFrame({"url":links}).to_csv(index=False).encode("utf-8-sig"),"shein_dynamic_links.csv")
            else:
                st.warning("浏览器加载后仍未发现商品链接。可能是动态接口或访问限制。")
        except Exception as exc:
            st.error(f"浏览器采集未成功：{exc}")
            st.info("如出现 Executable doesn't exist，说明云端未安装 Chromium 浏览器。")

st.subheader("图片归档与重命名")
photos=st.file_uploader("上传已获授权的图片（可以多选）",type=["jpg","jpeg","png","webp"],accept_multiple_files=True)
if len(edited) and photos:
    rowid=st.selectbox("关联到哪条 SKU 商品记录",range(len(edited)),format_func=lambda i:f"{i+1} - {edited.iloc[i].get('title','')}")
    kind=st.selectbox("图片类别",["颜色图","详情图","主图"])
    mode=st.radio("命名方式",["SKC + 颜色","SKU + 颜色 + 规格"],horizontal=True)
    if st.button("生成图片 ZIP"):
        row=edited.iloc[rowid]
        base=safe(row.get("skc") or row.get("product_id"))+"_"+safe(row.get("color"))
        if mode.startswith("SKU"):base=safe(row.get("sku") or row.get("product_id"))+"_"+safe(row.get("color"))+"_"+safe(row.get("size"))
        out=io.BytesIO()
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as archive:
            for i,p in enumerate(photos,1):
                name=f"{safe(row.get('platform'))}/{safe(row.get('product_id'))}/{safe(kind)}/{base}_{i:02d}{Path(p.name).suffix.lower()}"
                archive.writestr(name,p.getvalue())
        st.download_button("下载图片 ZIP",out.getvalue(),"product_images.zip",mime="application/zip")
st.caption("图片归属目前需要手工选择；真实 SKU→图片自动映射、批量远程图片下载、平台采集接口仍需开发。")
