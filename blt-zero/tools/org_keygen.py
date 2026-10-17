import json
from cryptography.hazmat.primitives.asymmetric import ec
import base64

def b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

def main():
    priv = ec.generate_private_key(ec.SECP256R1())
    pub = priv.public_key()

    nums = pub.public_numbers()
    x = nums.x.to_bytes(32, "big")
    y = nums.y.to_bytes(32, "big")

    pub_jwk = {
        "kty": "EC",
        "crv": "P-256",
        "x": b64url(x),
        "y": b64url(y),
        "ext": True,
    }

    # Private key JWK needs 'd'
    priv_nums = priv.private_numbers()
    d = priv_nums.private_value.to_bytes(32, "big")
    priv_jwk = { **pub_jwk, "d": b64url(d) }

    key_id = x[:8].hex()

    with open("public_key.jwk", "w", encoding="utf-8") as f:
        json.dump(pub_jwk, f, indent=2)
    with open("private_key.jwk", "w", encoding="utf-8") as f:
        json.dump(priv_jwk, f, indent=2)

    print("✅ Generated:")
    print(" - public_key.jwk  (share with BLT-Zero admin)")
    print(" - private_key.jwk (KEEP SECRET)")
    print("key_id:", key_id)
    print("alg: ECDH_P256_HKDF_SHA256_AESGCM")

if __name__ == "__main__":
    main()