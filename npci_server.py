import os
import sqlite3
from cryptography.hazmat.primitives.asymmetric import ed25519
from crypto_engine import pub_to_b64, sign_data, verify_signature
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="NPCI Mock Bank & Settlement Switch")

KEY_FILE = "bank_private.key"

if os.path.exists(KEY_FILE):
  with open(KEY_FILE, "rb") as f:
    BANK_PRIV = ed25519.Ed25519PrivateKey.from_private_bytes(f.read())
else:
  BANK_PRIV = ed25519.Ed25519PrivateKey.generate()
  with open(KEY_FILE, "wb") as f:
    f.write(BANK_PRIV.private_bytes_raw())

BANK_PUB_B64 = pub_to_b64(BANK_PRIV.public_key())


def init_db():
  conn = sqlite3.connect("bank.db")
  c = conn.cursor()
  c.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            vpa TEXT PRIMARY KEY,
            balance REAL,
            escrow_locked REAL
        )
    """)
  c.execute("""
        CREATE TABLE IF NOT EXISTS settled_txs (
            tx_hash TEXT PRIMARY KEY,
            sender TEXT,
            recipient TEXT,
            amount REAL
        )
    """)
  c.execute(
      "INSERT OR IGNORE INTO accounts VALUES ('rishi@okaxis', 5000.0, 0.0)"
  )
  c.execute(
      "INSERT OR IGNORE INTO accounts VALUES ('canteen@ybl', 10000.0, 0.0)"
  )
  conn.commit()
  conn.close()


init_db()


class LoadEscrowReq(BaseModel):
  vpa: str
  amount: float
  payer_pub_key: str


class SyncBatchReq(BaseModel):
  batch: list


@app.get("/api/bank_public_key")
def get_bank_key():
  return {"bank_pub_key": BANK_PUB_B64}


@app.post("/api/load_escrow")
def load_escrow(req: LoadEscrowReq):
  conn = sqlite3.connect("bank.db")
  c = conn.cursor()
  c.execute("SELECT balance FROM accounts WHERE vpa = ?", (req.vpa,))
  row = c.fetchone()
  if not row or row[0] < req.amount:
    conn.close()
    raise HTTPException(status_code=400, detail="Insufficient Bank Balance")

  c.execute(
      "UPDATE accounts SET balance = balance - ?, escrow_locked = escrow_locked"
      " + ? WHERE vpa = ?",
      (req.amount, req.amount, req.vpa),
  )
  conn.commit()
  conn.close()

  cert_payload = {
      "vpa": req.vpa,
      "payer_pub_key": req.payer_pub_key,
      "locked_amount": req.amount,
  }
  bank_signature = sign_data(BANK_PRIV, cert_payload)

  return {"certificate": cert_payload, "bank_signature": bank_signature}


@app.post("/api/sync_batch")
def sync_batch(req: SyncBatchReq):
  conn = sqlite3.connect("bank.db")
  c = conn.cursor()
  settled = 0

  for item in req.batch:
    tx = item["tx"]
    sig = item["sig"]
    payer_pub = item["payer_pub"]
    tx_hash = item["tx_hash"]

    if not verify_signature(payer_pub, tx, sig):
      continue

    c.execute("SELECT 1 FROM settled_txs WHERE tx_hash = ?", (tx_hash,))
    if c.fetchone():
      continue

    c.execute(
        "UPDATE accounts SET escrow_locked = escrow_locked - ? WHERE vpa = ?",
        (tx["amount"], tx["sender"]),
    )
    c.execute(
        "UPDATE accounts SET balance = balance + ? WHERE vpa = ?",
        (tx["amount"], tx["recipient"]),
    )
    c.execute(
        "INSERT INTO settled_txs VALUES (?, ?, ?, ?)",
        (tx_hash, tx["sender"], tx["recipient"], tx["amount"]),
    )
    settled += 1

  conn.commit()
  conn.close()
  return {"status": "SUCCESS", "settled_count": settled}


@app.get("/api/accounts")
def list_accounts():
  conn = sqlite3.connect("bank.db")
  c = conn.cursor()
  c.execute("SELECT vpa, balance, escrow_locked FROM accounts")
  rows = c.fetchall()
  conn.close()
  return [
      {"vpa": r[0], "balance": r[1], "escrow_locked": r[2]} for r in rows
  ]