import json
import base64
import sys
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def b64url_decode(s: str) -> bytes:
    s += "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s.encode())

def b64_decode(s: str) -> bytes:
    return base64.b64decode(s.encode())

def load_priv_jwk(path: str):
    jwk = json.load(open(path, "r", encoding="utf-8"))
    d = int.from_bytes(b64url_decode(jwk["d"]), "big")
    x = int.from_bytes(b64url_decode(jwk["x"]), "big")
    y = int.from_bytes(b64url_decode(jwk["y"]), "big")
    pub = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()
    return ec.derive_private_key(d, ec.SECP256R1()), pub

def eph_pub_from_jwk(jwk: dict):
    x = int.from_bytes(b64url_decode(jwk["x"]), "big")
    y = int.from_bytes(b64url_decode(jwk["y"]), "big")
    return ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()

def main():
    if len(sys.argv) != 3:
        print("Usage: python tools/org_decrypt.py private_key.jwk package.json")
        sys.exit(1)

    priv_path, pkg_path = sys.argv[1], sys.argv[2]
    priv, _ = load_priv_jwk(priv_path)

    pkg = json.load(open(pkg_path, "r", encoding="utf-8"))
    eph_pub = eph_pub_from_jwk(pkg["eph_pub_jwk"])

    # ECDH shared secret
    shared = priv.exchange(ec.ECDH(), eph_pub)

    salt = b64_decode(pkg["salt_b64"])
    iv = b64_decode(pkg["iv_b64"])
    ct = b64_decode(pkg["ciphertext_b64"])

    # HKDF -> AES key
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"blt-zero-v1",
    )
    key = hkdf.derive(shared)

    aesgcm = AESGCM(key)
    pt = aesgcm.decrypt(iv, ct, None)

    with open("report.json", "wb") as f:
        f.write(pt)

    print("✅ Decrypted -> report.json")

if __name__ == "__main__":
    main()