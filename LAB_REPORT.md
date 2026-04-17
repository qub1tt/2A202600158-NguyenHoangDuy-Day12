# Day 12 Lab - Mission Answers

**Student:** Nguyen Hoang Duy  
**Student ID:** 2A202600158  
**Date:** 2026-04-17

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found in `01-localhost-vs-production/develop/app.py`

1. **API key hardcode trong code** — `OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"` và `DATABASE_URL` chứa password, nếu push lên GitHub là lộ ngay
2. **Log ra secret** — `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")` in key ra stdout
3. **Dùng `print()` thay vì proper logging** — không có log level, không có structured format, không thể filter/parse
4. **Không có health check endpoint** — platform không biết khi nào app crash để restart
5. **Port cứng và host `localhost`** — `host="localhost"` chỉ chạy được trên máy local, không nhận traffic từ bên ngoài; `port=8000` cứng thay vì đọc từ `PORT` env var
6. **`reload=True` trong production** — debug reload gây overhead và security risk

### Exercise 1.3: Comparison table

| Feature | Develop | Production | Tại sao quan trọng? |
|---------|---------|------------|---------------------|
| Config | Hardcode trong code | Đọc từ env vars (`os.getenv`) | Tránh lộ secret, dễ thay đổi giữa các môi trường |
| Secrets | `OPENAI_API_KEY = "sk-..."` trực tiếp | `.env` file, không commit lên git | Secret trong git history = bị lộ vĩnh viễn |
| Health check | Không có | `GET /health` + `GET /ready` | Platform cần biết để restart hoặc route traffic |
| Logging | `print()` | JSON structured logging với level | Dễ search, parse, alert trong log aggregator |
| Shutdown | Đột ngột (SIGKILL) | Graceful — hoàn thành request trước khi tắt | Tránh mất request đang xử lý khi deploy/restart |
| Host binding | `localhost` (127.0.0.1) | `0.0.0.0` | Container cần bind 0.0.0.0 để nhận traffic từ ngoài |
| Port | Cứng `8000` | `int(os.getenv("PORT", "8000"))` | Railway/Render inject PORT tự động |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions (`02-docker/develop/Dockerfile`)

1. **Base image:** `python:3.11` — full Python distribution (~1 GB)
2. **Working directory:** `/app`
3. **Tại sao COPY requirements.txt trước?** — Docker layer cache: nếu code thay đổi nhưng requirements không đổi, Docker dùng cached layer cho bước `pip install` → build nhanh hơn nhiều
4. **CMD vs ENTRYPOINT:** `CMD` là default command, có thể override khi `docker run`; `ENTRYPOINT` là fixed executable, `CMD` trở thành default args. Ví dụ: `ENTRYPOINT ["python"]` + `CMD ["app.py"]` → có thể override thành `docker run image script.py`

### Exercise 2.3: Multi-stage build (`02-docker/production/Dockerfile`)

- **Stage 1 (builder):** Cài gcc, libpq-dev và toàn bộ Python packages — cần build tools để compile một số dependencies
- **Stage 2 (runtime):** Chỉ copy `/root/.local` (packages đã compile) và source code — không có gcc, pip, build tools
- **Tại sao image nhỏ hơn:** Stage 2 dùng `python:3.11-slim` và không có build tools (~200-300 MB so với ~1 GB)

### Exercise 2.3: Image size comparison

- Develop (`python:3.11` single-stage): ~1.0 GB
- Production (`python:3.11-slim` multi-stage): ~200–250 MB
- Difference: ~75% nhỏ hơn

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- **URL:** https://testlab11-production.up.railway.app
- **Platform:** Railway
- **Test health check:**
```
GET /health → HTTP 200
{"status":"ok","version":"1.0.0","environment":"development","uptime_seconds":42.9,...}
```

### Exercise 3.2: So sánh `render.yaml` vs `railway.toml`

| | `railway.toml` | `render.yaml` |
|---|---|---|
| Format | TOML | YAML |
| Builder | Chỉ khai báo `builder = "DOCKERFILE"` | Khai báo `type: web`, `env: docker` |
| Health check | `healthcheckPath`, `healthcheckTimeout` | `healthCheckPath` |
| Restart policy | `restartPolicyType`, `restartPolicyMaxRetries` | Tự động |
| Env vars | Set qua CLI hoặc dashboard | Có thể khai báo trong file (không nên với secrets) |

---

## Part 4: API Security

### Exercise 4.1: API Key authentication

- **API key được check ở đâu:** Trong dependency `verify_api_key()` dùng `APIKeyHeader`, inject vào endpoint qua `Depends()`
- **Khi sai key:** Trả về `HTTP 401` với message `"Invalid or missing API key"`
- **Rotate key:** Thay đổi `AGENT_API_KEY` env var và redeploy — không cần sửa code

### Exercise 4.3: Rate limiting

- **Algorithm:** Sliding Window Counter — mỗi user có một `deque` timestamps, loại bỏ timestamps cũ hơn 60 giây, đếm còn lại
- **Limit:** 10 requests/minute (set qua `RATE_LIMIT_PER_MINUTE=10` env var)
- **Bypass cho admin:** Tạo RateLimiter riêng với limit cao hơn (ví dụ `rate_limiter_admin = RateLimiter(max_requests=100)`) và áp dụng theo role

### Exercise 4.4: Cost guard implementation

```python
def check_budget(user_id: str, estimated_cost: float) -> bool:
    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"
    
    current = float(r.get(key) or 0)
    if current + estimated_cost > 10:
        return False
    
    r.incrbyfloat(key, estimated_cost)
    r.expire(key, 32 * 24 * 3600)  # 32 days TTL
    return True
```

Logic: dùng Redis key theo tháng (`budget:user123:2026-04`), cộng dồn chi phí, block khi vượt $10/tháng, TTL 32 ngày để tự reset.

### Test results

```
✅ POST /ask (no key)    → HTTP 401 {"detail": "Invalid or missing API key..."}
✅ POST /ask (wrong key) → HTTP 401 {"detail": "Invalid or missing API key..."}
✅ POST /ask (valid key) → HTTP 200 {"question":"...","answer":"...","model":"gpt-4o-mini",...}
✅ Rate limit hit 429    → at request #12 (limit=10/min, sliding window)
```

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks

```python
@app.get("/health")
def health():
    # Liveness: process còn sống, trả về uptime, version, checks
    return {"status": "ok", "uptime_seconds": ..., "version": "1.0.0"}

@app.get("/ready")
def ready():
    # Readiness: chỉ 200 khi _is_ready=True (sau lifespan startup)
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    return {"ready": True}
```

- `/health` = liveness probe: platform restart container nếu fail
- `/ready` = readiness probe: load balancer không route traffic khi app đang khởi động hoặc shutdown

### Exercise 5.2: Graceful shutdown

```python
@asynccontextmanager
async def lifespan(app):
    global _is_ready
    _is_ready = True
    yield                  # app chạy ở đây
    _is_ready = False      # stop nhận request mới
    # uvicorn timeout_graceful_shutdown=30 chờ in-flight requests xong

signal.signal(signal.SIGTERM, _handle_signal)
```

Khi nhận SIGTERM: set `_is_ready=False` → load balancer ngừng route → uvicorn chờ tối đa 30s cho request hiện tại hoàn thành → exit.

### Exercise 5.3: Stateless design

**Anti-pattern (stateful):**
```python
conversation_history = {}  # mất khi restart, không share giữa instances

@app.post("/ask")
def ask(user_id: str, question: str):
    history = conversation_history.get(user_id, [])
```

**Correct (stateless với Redis):**
```python
@app.post("/ask")
def ask(user_id: str, question: str):
    history = r.lrange(f"history:{user_id}", 0, -1)  # shared state
```

Khi scale ra 3 instances, mỗi instance đọc/ghi cùng Redis → conversation vẫn liên tục dù request đến instance khác nhau.

### Exercise 5.4: Load balancing

```bash
docker compose up --scale agent=3
```

- Nginx round-robin phân tán requests sang 3 agent instances
- Nếu 1 instance die: health check fail → Nginx tự loại khỏi pool → traffic chuyển sang 2 instances còn lại
- Stateless design đảm bảo không mất session khi failover

### Exercise 5.5: Test stateless

Khi chạy `docker compose up --scale agent=3` và gửi requests liên tục, conversation history được lưu trong Redis (shared) nên dù request rơi vào instance khác nhau, context vẫn được giữ nguyên.
