"""
AirUPI Server Test Suite — validates sync endpoints, idempotency,
database constraints, and service worker routing.
"""
import json
import os
import sys
import sqlite3

# Ensure we test with a fresh database
TEST_DB = "airupi_sync_test.db"

# Patch the DB path before importing
sys.path.insert(0, os.path.dirname(__file__))
import server
server.SYNC_DB = TEST_DB

# Remove old test DB if present
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

# Re-initialize with test DB
server.init_sync_db()

app = server.app
app.config['TESTING'] = True
client = app.test_client()

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  ✅ PASS: {name}")
        passed += 1
    else:
        print(f"  ❌ FAIL: {name} — {detail}")
        failed += 1

print("=" * 60)
print("AirUPI Server Test Suite")
print("=" * 60)

# --- Test 1: Root route ---
print("\n[1] Route: GET /")
r = client.get("/")
test("Returns 200", r.status_code == 200)
test("Returns HTML", b"AirUPI" in r.data)

# --- Test 2: Manifest route ---
print("\n[2] Route: GET /manifest.json")
r = client.get("/manifest.json")
test("Returns 200", r.status_code == 200)
test("Valid JSON manifest", b"AirUPI" in r.data)
test("Correct content-type", "application/manifest+json" in r.content_type)

# --- Test 3: Service Worker route ---
print("\n[3] Route: GET /sw.js")
r = client.get("/sw.js")
test("Returns 200", r.status_code == 200)
test("Contains cache logic", b"CACHE_NAME" in r.data)
test("JS content-type", "javascript" in r.content_type)

# --- Test 4: Payer sync endpoint ---
print("\n[4] Route: POST /api/sync/payer")
payload = {
    "deviceId": "DEV-TEST01",
    "records": [
        {
            "v": "1",
            "payer": "rishi@airupi",
            "payee": "merchant@airupi",
            "amt": 150,
            "n": 1,
            "t": 1700000000,
            "pub": "dGVzdHB1YmtleTEyMzQ1Njc4OTAxMjM0NTY=",
            "sig": "dGVzdHNpZ25hdHVyZTEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNA=="
        }
    ]
}
r = client.post("/api/sync/payer", json=payload)
data = r.get_json()
test("Returns 200", r.status_code == 200)
test("Status is RECEIVED (not SETTLED)", data.get("status") == "RECEIVED", f"got: {data.get('status')}")
test("Synced nonces returned", 1 in data.get("synced", []))

# --- Test 5: Idempotent re-sync ---
print("\n[5] Idempotent re-sync (same payer record)")
r2 = client.post("/api/sync/payer", json=payload)
data2 = r2.get_json()
test("Returns 200 on duplicate", r2.status_code == 200)
test("Still reports as synced", 1 in data2.get("synced", []))

# Verify only 1 row exists
conn = sqlite3.connect(TEST_DB)
count = conn.execute("SELECT COUNT(*) FROM payer_transactions WHERE nonce=1").fetchone()[0]
conn.close()
test("No duplicate rows in DB", count == 1, f"got {count} rows")

# --- Test 6: Merchant sync endpoint ---
print("\n[6] Route: POST /api/sync/merchant")
merchant_payload = {
    "deviceId": "DEV-MERCH01",
    "records": [
        {
            "v": "1",
            "payer": "rishi@airupi",
            "payee": "merchant@airupi",
            "amt": 200,
            "n": 2,
            "t": 1700000100,
            "pub": "bWVyY2hhbnRwdWJrZXkxMjM0NTY3ODkwMTI=",
            "sig": "bWVyY2hhbnRzaWduYXR1cmUxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MA=="
        }
    ]
}
r = client.post("/api/sync/merchant", json=merchant_payload)
data = r.get_json()
test("Returns 200", r.status_code == 200)
test("Status is RECEIVED", data.get("status") == "RECEIVED")
test("Synced nonces returned", 2 in data.get("synced", []))

# --- Test 7: Invalid payloads ---
print("\n[7] Invalid payloads")
r = client.post("/api/sync/payer", json={})
test("Missing records → 400", r.status_code == 400)

r = client.post("/api/sync/payer", json={"deviceId": "X", "records": [{"amt": 50}]})
data = r.get_json()
test("Incomplete record skipped (no nonces synced)", len(data.get("synced", [])) == 0)

# --- Test 8: Ledger full endpoint ---
print("\n[8] Route: GET /api/ledger/full")
r = client.get("/api/ledger/full")
data = r.get_json()
test("Returns 200", r.status_code == 200)
test("Status SUCCESS", data.get("status") == "SUCCESS")
test("Payer data present", len(data.get("payers", [])) >= 1)
test("Merchant data present", len(data.get("merchants", [])) >= 1)

# --- Test 9: UNIQUE constraint on (pub_key, nonce) ---
print("\n[9] UNIQUE constraint enforcement")
payload_dup = {
    "deviceId": "DEV-ATTACK",
    "records": [
        {
            "v": "1",
            "payer": "evil@airupi",
            "payee": "merchant@airupi",
            "amt": 9999,
            "n": 1,
            "t": 1700099999,
            "pub": "dGVzdHB1YmtleTEyMzQ1Njc4OTAxMjM0NTY=",
            "sig": "ZmFrZXNpZ25hdHVyZTEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNA=="
        }
    ]
}
r = client.post("/api/sync/payer", json=payload_dup)
data = r.get_json()
test("Duplicate (pub_key,nonce) is idempotent (200)", r.status_code == 200)

conn = sqlite3.connect(TEST_DB)
count = conn.execute(
    "SELECT COUNT(*) FROM payer_transactions WHERE pub_key=? AND nonce=1",
    ("dGVzdHB1YmtleTEyMzQ1Njc4OTAxMjM0NTY=",)
).fetchone()[0]
conn.close()
test("Original record unchanged (still 1 row)", count == 1, f"got {count}")

# --- Test 10: Database uses WAL mode ---
print("\n[10] Database configuration")
conn = sqlite3.connect(TEST_DB)
journal = conn.execute("PRAGMA journal_mode").fetchone()[0]
conn.close()
test("WAL journal mode active", journal == "wal", f"got: {journal}")

# --- Cleanup ---
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
for f in [TEST_DB + "-wal", TEST_DB + "-shm"]:
    if os.path.exists(f):
        os.remove(f)

print("\n" + "=" * 60)
print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
