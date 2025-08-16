# Python 3.11 slim image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    DB_PATH=/app/data/memory.db

WORKDIR /app

# system deps (optional but safe)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# install python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# copy code
COPY app.py storage.py /app/

# ensure data dir exists (for SQLite)
RUN mkdir -p /app/data

EXPOSE 8080

# Railway 會帶入 $PORT；本地預設 8080
CMD ["sh", "-c", "python -m uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
