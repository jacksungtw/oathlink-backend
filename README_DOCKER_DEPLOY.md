# OathLink Backend (Docker on Railway)

This repository uses a Dockerfile so that Railway will enable **Volumes**.

## Files
- `Dockerfile` – container build
- `.dockerignore` – ignore dev files
- `railway.json` – optional Railway hints
- `app.py`, `storage.py`, `requirements.txt` – your app

## Local test
```bash
docker build -t oathlink .
docker run --rm -it -p 8000:8000 -e DB_PATH=/data/memory.db -v $(pwd)/data:/data oathlink
# then open http://localhost:8000/health
```

## Deploy on Railway
1. Push these files to GitHub (root path).
2. Railway → New → **Deploy from GitHub** → choose this repo (it detects Dockerfile).
3. After first deploy, go to Service **Settings → Volumes → Add Volume**:
   - Mount Path: `/data`
4. Service **Variables**:
   - `DB_PATH=/data/memory.db`
   - `AUTH_TOKEN=<your-long-random-string>`
5. Redeploy.
6. Test:
```bash
curl https://<your>.up.railway.app/health
curl -X POST https://<your>.up.railway.app/memory/write   -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json"   -d '{"content":"願主偏好：先結論→理由→行動","tags":["persona","seed"]}'
```
