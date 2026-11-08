import json
import os
import sys
import cv2
import mss
import numpy as np
import pygetwindow as gw
from pyzbar.pyzbar import ZBarSymbol, decode
import requests
from rich.console import Console
from rich.panel import Panel

console = Console()
SERVER_URL = "http://127.0.0.1:8000"
RECEIPTS_FILE = "merchant_receipts.json"
KEY_CACHE = "bank_pub.key"


def cache_bank_key():
  if not os.path.exists(KEY_CACHE):
    try:
      res = requests.get(f"{SERVER_URL}/api/bank_public_key").json()
      with open(KEY_CACHE, "w") as f:
        f.write(res["bank_pub_key"])
    except Exception as e:
      console.print(
          f"[bold red]Could not fetch bank key from server: {e}[/bold red]"
      )
  with open(KEY_CACHE, "r") as f:
    return f.read().strip()


def run_scanner():
  from crypto_engine import verify_signature

  bank_pub = cache_bank_key()

  droidcam_windows = [
      w for w in gw.getWindowsWithTitle("DroidCam Client") if not w.isMinimized
  ]
  if not droidcam_windows:
    console.print(
        "[bold red]DroidCam Client window not found! Keep the DroidCam app"
        " visible on your screen.[/bold red]"
    )
    return

  win = droidcam_windows[0]
  try:
    win.activate()
  except Exception:
    pass

  console.print(
      Panel(
          f"[bold cyan]MERCHANT POS HOOKED TO DROIDCAM[/bold cyan]\nStream"
          f" Target: {win.title}\nPoint phone camera at the QR. Press 'q' to"
          " exit.",
          title="Terminal Ready",
      )
  )

  with mss.MSS() as sct:
    while True:
      monitor = {
          "top": max(win.top + 35, 0),
          "left": max(win.left + 10, 0),
          "width": max(win.width - 20, 100),
          "height": max(win.height - 120, 100),
      }

      screenshot = np.array(sct.grab(monitor))
      frame = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)

      barcodes = decode(frame, symbols=[ZBarSymbol.QRCODE])
      for barcode in barcodes:
        raw_data = barcode.data.decode("utf-8")
        try:
          packet = json.loads(raw_data)

          if not verify_signature(
              bank_pub, packet["cert"], packet["bank_sig"]
          ):
            console.print(
                Panel(
                    "[bold red]CRITICAL: FAKE ESCROW CERTIFICATE![/bold red]",
                    title="Fraud Blocked",
                )
            )
            cv2.destroyAllWindows()
            return

          if not verify_signature(
              packet["payer_pub"], packet["tx"], packet["sig"]
          ):
            console.print(
                Panel(
                    "[bold red]CRITICAL: INVALID TRANSACTION"
                    " SIGNATURE![/bold red]",
                    title="Fraud Blocked",
                )
            )
            cv2.destroyAllWindows()
            return

          receipts = []
          if os.path.exists(RECEIPTS_FILE):
            with open(RECEIPTS_FILE, "r") as f:
              receipts = json.load(f)

          if any(r["tx_hash"] == packet["tx_hash"] for r in receipts):
            console.print(
                Panel(
                    "[bold yellow]DOUBLE-SPEND ATTEMPT: Token already scanned"
                    " and logged![/bold yellow]",
                    title="Replay Blocked",
                )
            )
            cv2.destroyAllWindows()
            return

          receipts.append(packet)
          with open(RECEIPTS_FILE, "w") as f:
            json.dump(receipts, f, indent=2)

          tx = packet["tx"]
          console.print(
              Panel(
                  f"[bold green]✔ PAYMENT RECEIVED & VERIFIED OFFLINE[/bold"
                  f" green]\nFrom: [white]{tx['sender']}[/white]\nAmount: [bold"
                  f" yellow]₹{tx['amount']}[/bold yellow]\nNonce: #{tx['nonce']}"
                  f" | Hash: {packet['tx_hash'][:16]}...",
                  title="Transaction Accepted",
              )
          )
          cv2.destroyAllWindows()
          return

        except Exception:
          pass

      cv2.imshow("Merchant POS Scanner", frame)
      if cv2.waitKey(1) & 0xFF == ord("q"):
        break

  cv2.destroyAllWindows()


def sync():
  if not os.path.exists(RECEIPTS_FILE):
    console.print(
        "[bold yellow]No offline receipts stored to sync.[/bold yellow]"
    )
    return

  with open(RECEIPTS_FILE, "r") as f:
    receipts = json.load(f)

  console.print(
      f"[cyan][*] Connecting to NPCI Switch to sync {len(receipts)}"
      " receipt(s)...[/cyan]"
  )
  try:
    res = requests.post(
        f"{SERVER_URL}/api/sync_batch", json={"batch": receipts}
    ).json()
    console.print(
        Panel(
            f"[bold green]Settlement Complete![/bold green]\nTransactions"
            f" Settled: {res['settled_count']}",
            title="NPCI Clearing Result",
        )
    )
    os.remove(RECEIPTS_FILE)
  except Exception as e:
    console.print(f"[bold red]Sync failed: {e}[/bold red]")


if __name__ == "__main__":
  if len(sys.argv) > 1 and sys.argv[1] == "sync":
    sync()
  else:
    run_scanner()