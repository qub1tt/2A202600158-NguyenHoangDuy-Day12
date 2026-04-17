# Deployment Information

## Public URL

https://testlab11-production.up.railway.app

## Platform

Railway (Docker deployment)

## Environment Variables Set

| Variable | Value |
|----------|-------|
| `AGENT_API_KEY` | `aicb-vinuni-2026` |
| `RATE_LIMIT_PER_MINUTE` | `10` |
| `ENVIRONMENT` | `production` |
| `PORT` | injected by Railway automatically |

---

## Test Commands

### Health Check
```bash
curl https://testlab11-production.up.railway.app/health
```
Expected:
```json
{"status":"ok","version":"1.0.0","environment":"development","uptime_seconds":42.9,"total_requests":2,"checks":{"llm":"mock"}}
```

### Readiness Check
```bash
curl https://testlab11-production.up.railway.app/ready
```
Expected: `{"ready":true}`

### No API Key → 401
```bash
curl -X POST https://testlab11-production.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
```
Expected: `{"detail":"Invalid or missing API key. Include header: X-API-Key: <key>"}`

### API Test (with authentication)
```bash
curl -X POST https://testlab11-production.up.railway.app/ask \
  -H "X-API-Key: aicb-vinuni-2026" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Docker?"}'
```
Expected:
```json
{"question":"What is Docker?","answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!","model":"gpt-4o-mini","timestamp":"..."}
```

### Rate Limiting → 429
```bash
for i in {1..15}; do
  curl -s -X POST https://testlab11-production.up.railway.app/ask \
    -H "X-API-Key: aicb-vinuni-2026" \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"Test $i\"}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('answer','') or d.get('detail',''))"
done
# Request #11+ returns HTTP 429
```

---

## Automated Test Results

```
✅ GET /health             → HTTP 200
✅ GET /                   → HTTP 200
✅ POST /ask (no key)      → HTTP 401
✅ POST /ask (wrong key)   → HTTP 401
✅ POST /ask (valid key)   → HTTP 200
✅ GET /ready              → HTTP 200
✅ Rate limit (10 req/min) → HTTP 429 at request #12

Result: 7/7 passed
```
