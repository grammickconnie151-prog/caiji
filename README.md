# 跨平台商品采集工作台（网页 MVP）

Streamlit 网页，可处理 Amazon/SHEIN/Temu 来源的已获取数据，手工关联图片，按商品/颜色/尺码命名并导出 Excel 与 ZIP。

## 部署
1. 在 Streamlit Community Cloud 选择此仓库 `main`、入口 `app.py`。
2. 首先以 CSV/JSON 导入模式测试；**未配置 API 时不支持实时采集**。
3. Amazon 实时查询需另行部署得到授权的 API 服务，在 Streamlit Secrets 配置 `AMAZON_API_BASE_URL`（HTTPS 地址），可选 `AMAZON_API_KEY`。密钥不得提交到 GitHub。
4. 图片处理针对手动上传、已有使用授权的图片；SHEIN/Temu 实时接口尚未接入。

## 本地启动
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 数据字段
`platform,product_id,url,title,category,currency,price,skc,sku,color,size,stock,main_image_url,detail_image_urls,variant_image_url`

仓库当前为公开仓库，不要在此存储任何账号、密码、API Key 或非公开业务数据。生产部署前需要身份验证、数据库及持久化文件存储；Streamlit 临时会话不等于长期储存。
