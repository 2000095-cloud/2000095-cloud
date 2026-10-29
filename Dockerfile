# 供 Cloud Run / Render / Koyeb 使用（Streamlit Community Cloud 不需要）
FROM python:3.12-slim

WORKDIR /app

# 先裝依賴（利用 layer 快取，改程式碼時不必重裝）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ★平台會用 PORT 環境變數指定埠號（Cloud Run 8080 / Render 10000）
ENV PORT=8080 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

EXPOSE 8080

# 用 shell 形式讓 $PORT 能被展開
CMD streamlit run app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true
