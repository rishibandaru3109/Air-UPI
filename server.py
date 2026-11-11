import os
import sqlite3
import time
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

app = Flask(__name__, template_folder="templates")
CORS(app)

# ---------------------------------------------------------------------------
# Database: browser-side sync ledger (separate from npci_server.py's bank.db)
# ---------------------------------------------------------------------------
SYNC_DB = "airupi_sync.db"

def get_db():
    """Get a database connection with WAL mode and foreign keys enabled."""
    conn = sqlite3.connect(SYNC_DB)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn

def init_sync_db():
    """Create the sync ledger tables if they don't exist."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS payer_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            payer TEXT NOT NULL,
            payee TEXT NOT NULL,
            amount INTEGER NOT NULL,
            nonce INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            pub_key TEXT NOT NULL,
            signature TEXT NOT NULL,
            received_at INTEGER NOT NULL,
            UNIQUE(pub_key, nonce)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS merchant_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            payer TEXT NOT NULL,
            payee TEXT NOT NULL,
            amount INTEGER NOT NULL,
            nonce INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            pub_key TEXT NOT NULL,
            signature TEXT NOT NULL,
            received_at INTEGER NOT NULL,
            UNIQUE(pub_key, nonce)
        )
    """)
    conn.commit()
    conn.close()

init_sync_db()

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json", mimetype="application/manifest+json")

@app.route("/sw.js")
def service_worker():
    return send_from_directory("static/js", "sw.js", mimetype="application/javascript")

# ---------------------------------------------------------------------------
# Sync API: Payer
# ---------------------------------------------------------------------------
@app.route("/api/sync/payer", methods=["POST"])
def sync_payer():
    data = request.get_json()
    if not data or "records" not in data:
        return jsonify({"error": "Missing records"}), 400

    device_id = data.get("deviceId", "UNKNOWN")
    records = data["records"]
    synced_nonces = []

    conn = get_db()
    try:
        for rec in records:
            # Validate required fields
            if not all(k in rec for k in ("payer", "payee", "amt", "n", "t", "pub", "sig")):
                continue

            try:
                conn.execute(
                    """INSERT INTO payer_transactions
                       (device_id, payer, payee, amount, nonce, timestamp, pub_key, signature, received_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (device_id, rec["payer"], rec["payee"], int(rec["amt"]),
                     int(rec["n"]), int(rec["t"]), rec["pub"], rec["sig"],
                     int(time.time()))
                )
                synced_nonces.append(rec["n"])
            except sqlite3.IntegrityError:
                # Already exists (idempotent) — still report as synced
                synced_nonces.append(rec["n"])

        conn.commit()
    finally:
        conn.close()

    return jsonify({"status": "RECEIVED", "synced": synced_nonces})

# ---------------------------------------------------------------------------
# Sync API: Merchant
# ---------------------------------------------------------------------------
@app.route("/api/sync/merchant", methods=["POST"])
def sync_merchant():
    data = request.get_json()
    if not data or "records" not in data:
        return jsonify({"error": "Missing records"}), 400

    device_id = data.get("deviceId", "UNKNOWN")
    records = data["records"]
    synced_nonces = []

    conn = get_db()
    try:
        for rec in records:
            # Validate required fields
            if not all(k in rec for k in ("payer", "payee", "amt", "n", "t", "pub", "sig")):
                continue

            try:
                conn.execute(
                    """INSERT INTO merchant_transactions
                       (device_id, payer, payee, amount, nonce, timestamp, pub_key, signature, received_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (device_id, rec["payer"], rec["payee"], int(rec["amt"]),
                     int(rec["n"]), int(rec["t"]), rec["pub"], rec["sig"],
                     int(time.time()))
                )
                synced_nonces.append(rec["n"])
            except sqlite3.IntegrityError:
                # Already exists (idempotent) — still report as synced
                synced_nonces.append(rec["n"])

        conn.commit()
    finally:
        conn.close()

    return jsonify({"status": "RECEIVED", "synced": synced_nonces})

# ---------------------------------------------------------------------------
# Ledger API: read all synced transactions
# ---------------------------------------------------------------------------
@app.route("/api/ledger/full", methods=["GET"])
def get_full_ledger():
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT * FROM payer_transactions ORDER BY id DESC")
        payer_data = [dict(row) for row in cur.fetchall()]

        cur.execute("SELECT * FROM merchant_transactions ORDER BY id DESC")
        merchant_data = [dict(row) for row in cur.fetchall()]

        conn.close()

        return jsonify({
            "status": "SUCCESS",
            "database": SYNC_DB,
            "payers": payer_data,
            "merchants": merchant_data
        })

    except Exception as e:
        return jsonify({
            "status": "ERROR",
            "error_message": str(e)
        }), 500

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
