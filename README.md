# ⚡ AirUPI

### Offline-first payment authorization using cryptographically signed QR vouchers.

**Built by Unpaid Interns**

---

## Overview

What happens when the internet goes down, but a payment still needs to happen?

**AirUPI** is an experimental offline-first payment authorization system that explores how QR-based transactions can be exchanged and verified locally, without requiring an active internet connection during the exchange.

Using digital signatures, local transaction ledgers, and deferred synchronization, AirUPI demonstrates an alternative approach to payment authorization in connectivity-constrained environments.

## ✨ Features

- **Offline QR Exchange** — Generate and scan payment vouchers without internet connectivity during the exchange.
- **Ed25519 Cryptography** — Digitally sign and verify transaction vouchers.
- **Dual Ledgers** — Maintain separate payer and merchant transaction histories.
- **Replay Protection** — Detect previously accepted vouchers using persistent local tracking.
- **Deferred Synchronization** — Submit locally recorded transactions when connectivity returns.
- **SQLite Backend** — Store received synchronization records.
- **Progressive Web App** — Cache application resources for offline access.
- **Receipt-inspired UI** — A distinctive interface built around the physical experience of transactions.

## ⚙️ How It Works

```text
       PAYER
         |
         v
   Create Transaction
         |
         v
   Sign Payment Voucher
         |
         v
      QR CODE
         |
         v
   MERCHANT SCANNER
         |
         v
   Local Verification
         |
         v
   Local Transaction Records
         |
         v
   Connectivity Restored
         |
         v
   Flask Synchronization API
         |
         v
      SQLite
```

1. **Create:** The payer generates a transaction voucher.
2. **Sign:** The voucher is digitally signed using Ed25519.
3. **Exchange:** The merchant scans the generated QR code.
4. **Verify:** The merchant validates the signature locally and checks replay protection.
5. **Record:** Both sides maintain their respective transaction records.
6. **Synchronize:** Pending records are submitted to the backend when connectivity returns.

## 🧰 Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Cryptography | TweetNaCl.js, Ed25519 |
| QR Generation | QRCode.js |
| QR Scanning | jsQR |
| Backend | Python, Flask |
| Database | SQLite |
| Offline Support | Service Workers, PWA |

## 🚀 Getting Started

### Prerequisites

- Python
- Git
- A modern web browser

### 1. Clone the repository

```bash
git clone https://github.com/rishibandaru3109/Air-UPI.git
```

### 2. Enter the project directory

```bash
cd Air-UPI
```

### 3. Install dependencies

```powershell
py -m pip install flask
```

### 4. Start the application

```powershell
py server.py
```

### 5. Access AirUPI

Open the local application address displayed by the server in your browser.

To access the application from another device on the same Wi-Fi network, use the host computer's current local IP address:

```text
http://<YOUR_LOCAL_IP>:5000
```

Replace `<YOUR_LOCAL_IP>` with your own computer's current local IPv4 address. This address can change when you switch networks or reconnect.

## 🧪 Running Tests

Run the backend test suite:

```powershell
py -m unittest test_server.py -v
```

Run the cryptographic compatibility tests:

```powershell
py -m unittest test_crypto_compat.py -v
```

Automated tests cover selected backend and cryptographic behaviours. Manual browser and multi-device testing is also necessary.

## 🔐 Security & Scope

AirUPI is an experimental payment authorization prototype, not a production financial system.

- No integration with real UPI, NPCI, or banking infrastructure.
- Wallet balances and backend records are simulated.
- Local replay protection does not provide global protection across disconnected devices.
- Conflicting offline transactions may require reconciliation after connectivity returns.
- Digital signatures establish possession of a signing key, not proof of available funds or real-world identity.

## 🛣️ Future Scope

- Stronger payer identity verification.
- Improved transaction reconciliation.
- Enhanced cross-device security.
- More robust offline storage and recovery.
- Expanded merchant-side receipt functionality.

## 👥 Team

**Unpaid Interns**

An experimental exploration of offline-first payments, cryptography, and resilient web applications.

---

**AirUPI — Payments beyond connectivity.**
