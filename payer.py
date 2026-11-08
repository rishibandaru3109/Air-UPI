import json
import os
import sys
from cryptography.hazmat.primitives.asymmetric import ed25519
from crypto_engine import (
    compute_tx_hash,
    generate_keypair,
    pub_to_b64,
    sign_data,
)
import cv2
import numpy as np
import qrcode
import requests
from rich.console import Console
from rich.panel import Panel

console = Console()
SERVER_URL = "http://127.0.0.1:8000"
WALLET_FILE = "payer_wallet.json"


def init_wallet():
  priv, pub = generate_keypair()
  pub_b64 = pub_to_b64(pub)

  console.print(
      "[bold yellow][*] Contacting Bank Server to lock ₹500 in"
      " Escrow...[/bold yellow]"
  )
  try:
    res = requests.post(
        f"{SERVER_URL}/api/load_escrow",
        json={
            "vpa": "rishi@okaxis",
            "amount": 500.0,
            "payer_pub_key": pub_b64,
        },
    ).json()
  except Exception as e:
    console.print(
        f"[bold red][-] Failed to connect to server: {e}[/bold red]"
    )
    return

  wallet = {
      "vpa": "rishi@okaxis",
      "priv_bytes": priv.private_bytes_raw().hex(),
      "pub_b64": pub_b64,
      "balance": 500.0,
      "nonce": 0,
      "prev_hash": "GENESIS_ROOT_HASH",
      "certificate": res["certificate"],
      "bank_sig": res["bank_signature"],
  }
  with open(WALLET_FILE, "w") as f:
    json.dump(wallet, f, indent=2)

  console.print(
      Panel(
          "[bold green]Offline Escrow Vault Loaded![/bold green]\n"
          f"Payer: {wallet['vpa']}\n"
          f"Locked Balance: ₹{wallet['balance']}\n"
          "Ready for offline transactions.",
          title="Setup Complete",
      )
  )


def make_payment(recipient: str, amount: float):
  if not os.path.exists(WALLET_FILE):
    console.print(
        "[bold red]Wallet not loaded! Run 'py payer.py' while server is up"
        " first.[/bold red]"
    )
    return

  with open(WALLET_FILE, "r") as f:
    w = json.load(f)

  if w["balance"] < amount:
    console.print(
        f"[bold red]Insufficient Escrow Funds! Available:"
        f" ₹{w['balance']}[/bold red]"
    )
    return

  priv = ed25519.Ed25519PrivateKey.from_private_bytes(
      bytes.fromhex(w["priv_bytes"])
  )

  w["nonce"] += 1
  w["balance"] -= amount

  tx_data = {
      "nonce": w["nonce"],
      "sender": w["vpa"],
      "recipient": recipient,
      "amount": amount,
      "prev_hash": w["prev_hash"],
  }

  sig = sign_data(priv, tx_data)
  tx_hash = compute_tx_hash(tx_data, sig)
  w["prev_hash"] = tx_hash

  with open(WALLET_FILE, "w") as f:
    json.dump(w, f, indent=2)

  qr_payload = {
      "cert": w["certificate"],
      "bank_sig": w["bank_sig"],
      "tx": tx_data,
      "sig": sig,
      "payer_pub": w["pub_b64"],
      "tx_hash": tx_hash,
  }

  console.print(
      Panel(
          f"[bold cyan]PAYMENT TOKEN GENERATED[/bold cyan]\n"
          f"Paying: [white]{recipient}[/white]\n"
          f"Amount: [bold green]₹{amount}[/bold green]\n"
          f"Nonce: #{tx_data['nonce']} | Hash: {tx_hash[:16]}...\n"
          f"Remaining Escrow: ₹{w['balance']}",
          title="Ready to Beam",
      )
  )

  qr = qrcode.QRCode(box_size=8, border=2)
  qr.add_data(json.dumps(qr_payload))
  qr.make(fit=True)
  qr_img = np.array(qr.make_image(fill_color="black", back_color="white"))
  qr_img = cv2.cvtColor(qr_img.astype(np.uint8) * 255, cv2.COLOR_GRAY2BGR)

  console.print(
      "[dim]Displaying signed QR. Press ANY key on the QR window to"
      " dismiss.[/dim]"
  )
  cv2.imshow("Payer Signed Token (Merchant Scans This)", qr_img)
  cv2.waitKey(0)
  cv2.destroyAllWindows()


if __name__ == "__main__":
  if len(sys.argv) > 1 and sys.argv[1] == "pay":
    amt = float(sys.argv[2]) if len(sys.argv) > 2 else 150.0
    make_payment("canteen@ybl", amt)
  else:
    init_wallet()