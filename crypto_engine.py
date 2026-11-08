import base64
import hashlib
import json
from cryptography.hazmat.primitives.asymmetric import ed25519

def generate_keypair():
    priv = ed25519.Ed25519PrivateKey.generate()
    pub = priv.public_key()
    return priv, pub

def pub_to_b64(pub_key) -> str:
    raw = pub_key.public_bytes_raw()
    return base64.b64encode(raw).decode("utf-8")

def b64_to_pub(b64_str: str):
    raw = base64.b64decode(b64_str.encode("utf-8"))
    return ed25519.Ed25519PublicKey.from_public_bytes(raw)

def sign_data(priv_key, data_dict: dict) -> str:
    payload = json.dumps(data_dict, sort_keys=True).encode("utf-8")
    sig = priv_key.sign(payload)
    return base64.b64encode(sig).decode("utf-8")

def verify_signature(pub_key_b64: str, data_dict: dict, sig_b64: str) -> bool:
    try:
        pub = b64_to_pub(pub_key_b64)
        sig = base64.b64decode(sig_b64.encode("utf-8"))
        payload = json.dumps(data_dict, sort_keys=True).encode("utf-8")
        pub.verify(sig, payload)
        return True
    except Exception:
        return False

def compute_tx_hash(tx_data: dict, sig_b64: str) -> str:
    content = json.dumps(tx_data, sort_keys=True) + sig_b64
    return hashlib.sha256(content.encode("utf-8")).hexdigest()