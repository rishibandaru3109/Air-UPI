import os
import json
import time
import base64
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from cryptography.hazmat.primitives.asymmetric import ed25519

app = Flask(__name__, template_folder="templates")
CORS(app)

# Generate persistent demo keys
PAYER_PRIV = ed25519.Ed25519PrivateKey.generate()
PAYER_PUB = PAYER_PRIV.public_key()
PAYER_PUB_B64 = base64.b64encode(PAYER_PUB.public_bytes_raw()).decode('ascii')

BANK_PRIV = ed25519.Ed25519PrivateKey.generate()
BANK_PUB = BANK_PRIV.public_key()
BANK_PUB_B64 = base64.b64encode(BANK_PUB.public_bytes_raw()).decode('ascii')

escrow_vault = {"balance": 10000.00, "nonce": 0}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/create-voucher", methods=["POST"])
def create_voucher():
    global escrow_vault
    data = request.get_json() or {}
    amount = int(float(data.get("amount", 0)))
    payee_id = str(data.get("payee_id", "merchant@airupi"))

    if amount <= 0 or amount > escrow_vault["balance"]:
        return jsonify({"error": "Invalid amount or insufficient balance"}), 400

    escrow_vault["nonce"] += 1
    escrow_vault["balance"] -= amount
    timestamp = int(time.time())

    # Canonical string format matched to index.html
    canonical = f"rishi@airupi|{payee_id}|{amount}|{escrow_vault['nonce']}|{timestamp}"
    raw_signature = PAYER_PRIV.sign(canonical.encode('ascii'))
    sig_b64 = base64.b64encode(raw_signature).decode('ascii')

    voucher_data = {
        "v": "1",
        "payer": "rishi@airupi",
        "payee": payee_id,
        "amt": amount,
        "n": escrow_vault["nonce"],
        "t": timestamp,
        "pub": PAYER_PUB_B64,
        "sig": sig_b64
    }

    return jsonify({
        "status": "SUCCESS",
        "voucher": voucher_data,
        "remaining_balance": escrow_vault["balance"]
    })
from flask import send_from_directory

@app.route('/sw.js')
def service_worker():
    return send_from_directory('.', 'sw.js', mimetype='application/javascript')
import os
import sqlite3
from flask import jsonify

@app.route('/api/ledger/full', methods=['GET'])
def get_full_ledger():
    try:
        # Auto-detect whichever database file exists in your workspace
        db_path = 'bank.db' if os.path.exists('bank.db') else 'bank_ledger.db'
        
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Check existing table names
        tables = [row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

        merchant_data = []
        payer_data = []

        if 'merchant_transactions' in tables:
            cur.execute("SELECT * FROM merchant_transactions ORDER BY id DESC")
            merchant_data = cur.fetchall()

        if 'payer_transactions' in tables:
            cur.execute("SELECT * FROM payer_transactions ORDER BY id DESC")
            payer_data = cur.fetchall()

        # Also pull legacy table if existing from initial setup
        legacy_ledger = []
        if 'ledger' in tables:
            cur.execute("SELECT * FROM ledger ORDER BY id DESC")
            legacy_ledger = cur.fetchall()

        conn.close()

        return jsonify({
            "status": "SUCCESS",
            "database_used": db_path,
            "merchants": merchant_data,
            "payers": payer_data,
            "legacy_ledger": legacy_ledger
        })

    except Exception as e:
        return jsonify({
            "status": "ERROR",
            "error_message": str(e)
        }), 200  # Return 200 so you can read the exact error in your browser instead of 500
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)