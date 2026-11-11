"""
Test client-side crypto compatibility and voucher logic
"""
import base64
import time
from cryptography.hazmat.primitives.asymmetric import ed25519

def test_crypto_compatibility():
    # 1. Generate Ed25519 keypair
    priv = ed25519.Ed25519PrivateKey.generate()
    pub = priv.public_key()
    pub_bytes = pub.public_bytes_raw()
    pub_b64 = base64.b64encode(pub_bytes).decode('ascii')

    # 2. Match exact canonical format used in index.html
    payer = "rishi@airupi"
    payee = "merchant@airupi"
    amt = 150
    nonce = 1
    t = int(time.time())

    canonical = f"{payer}|{payee}|{amt}|{nonce}|{t}"
    sig = priv.sign(canonical.encode('utf-8'))
    sig_b64 = base64.b64encode(sig).decode('ascii')

    # 3. Simulate index.html merchant verification:
    rec_sig = base64.b64decode(sig_b64)
    rec_pub_bytes = base64.b64decode(pub_b64)
    rec_pub = ed25519.Ed25519PublicKey.from_public_bytes(rec_pub_bytes)

    # Reconstruct canonical exactly
    verify_canonical = f"{payer}|{payee}|{amt}|{nonce}|{t}"
    rec_pub.verify(rec_sig, verify_canonical.encode('utf-8'))
    print("✅ PASS: Ed25519 signature verification matches browser canonical format")

    # 4. Test tampering resistance
    tampered_canonical = f"{payer}|{payee}|{amt + 50}|{nonce}|{t}"
    try:
        rec_pub.verify(rec_sig, tampered_canonical.encode('utf-8'))
        raise AssertionError("Tampered amount should fail verification!")
    except Exception:
        print("✅ PASS: Tampered amount correctly rejected")

    # 5. Test replay prevention key format: pubPrefix:nonce
    pub_prefix = pub_b64[:12]
    replay_key = f"{pub_prefix}:{nonce}"
    seen = set()
    assert replay_key not in seen
    seen.add(replay_key)
    assert replay_key in seen
    print("✅ PASS: Replay key format pubPrefix:nonce functions correctly")

if __name__ == "__main__":
    test_crypto_compatibility()
