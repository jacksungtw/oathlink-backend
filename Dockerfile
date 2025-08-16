# 1) 基底映像
FROM python:3.11-slim

# 2) 工作目錄
WORKDIR /app

# 3) 安裝相依
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4) 複製程式
COPY . .

# 5) 讓 Railway 打健康檢查（實際用 $PORT）
EXPOSE 8000

# 6) 關鍵：用 shell 形式展開 $PORT，避免看到 '$PORT is not a valid integer'
CMD sh -c "python -m uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"