"""Quick deployment test script"""
import urllib.request
import urllib.error
import json
import time

BASE_URL = "https://testlab11-production.up.railway.app"
API_KEY = "aicb-vinuni-2026"


def req(method, path, body=None, headers=None):
    url = BASE_URL + path
    data = json.dumps(body).encode() if body else None
    h = {"Content-Type": "application/json", **(headers or {})}
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test(name, status, resp, expect_status):
    ok = status == expect_status
    icon = "✅" if ok else "❌"
    print(f"{icon} {name} → HTTP {status}")
    print(f"   {json.dumps(resp, ensure_ascii=False)[:120]}")
    return ok


print("\n" + "="*55)
print("  Deployment Test — testlab11-production.up.railway.app")
print("="*55)

results = []

# 1. Health check
s, r = req("GET", "/health")
results.append(test("GET /health", s, r, 200))

# 2. Root info
s, r = req("GET", "/")
results.append(test("GET /", s, r, 200))

# 3. No API key → 401
s, r = req("POST", "/ask", {"question": "Hello"})
results.append(test("POST /ask (no key) → 401", s, r, 401))

# 4. Wrong API key → 401
s, r = req("POST", "/ask", {"question": "Hello"}, {"X-API-Key": "wrong-key"})
results.append(test("POST /ask (wrong key) → 401", s, r, 401))

# 5. Valid request
s, r = req("POST", "/ask", {"question": "What is Docker?"}, {"X-API-Key": API_KEY})
results.append(test("POST /ask (valid) → 200", s, r, 200))

# 6. Readiness check
s, r = req("GET", "/ready")
results.append(test("GET /ready", s, r, 200))

# 7. Rate limit — gọi 22 lần, expect 429
print("\n⏳ Rate limit test (22 requests)...")
hit_429 = False
for i in range(1, 23):
    s, r = req("POST", "/ask", {"question": f"Rate test {i}"}, {"X-API-Key": API_KEY})
    if s == 429:
        print(f"   → Hit 429 at request #{i} ✅")
        hit_429 = True
        break
    time.sleep(0.1)
results.append(("Rate limiting (429)" , hit_429))
if not hit_429:
    print("   → Never hit 429 ❌")

# Summary
passed = sum(1 for r in results if (r[1] if isinstance(r, tuple) else r))
total = len(results)
print(f"\n{'='*55}")
print(f"  Result: {passed}/{total} passed")
print("="*55 + "\n")
