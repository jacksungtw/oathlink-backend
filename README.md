
# OathLink Backend (MVP)

## Run
```
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```
Health check: http://localhost:8000/health

## API
- POST /inject {text, top_k} -> returns injected prompt (persona + memory + task)
- POST /rewrite {reply} -> returns rewritten reply with fixed tone/structure
- POST /memory/write {content, tags?}
- GET  /memory/search?q=...&top_k=5
