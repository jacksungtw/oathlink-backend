# 依需要可改成 python:3.11-slim
FROM python:3.11-slim

WORKDIR /app

# 輕量安裝系統依賴（如需）
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# 先複製需求再安裝，利用快取
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 再把程式碼放進去
COPY app.py storage.py /app/

# Railway 會注入 $PORT，這裡只標註 8080 以利本地測試
EXPOSE 8080

# 這行只是文檔化；真正啟動由 railway.json 的 startCommand 控制
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]