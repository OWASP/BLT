import json
import base64
import time
import os
import re

try:
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
except ImportError:
    print("Error: The 'cryptography' library is required.")
    print("Please install it by running: pip install cryptography")
    exit(1)


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def generate_jwt():
    print("Generating new RS256 keypair...")
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Export public key
    public_key = private_key.public_key()
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("utf-8")

    # Update .dev.vars
    dev_vars_path = ".dev.vars"
    dev_vars_content = ""
    if os.path.exists(dev_vars_path):
        with open(dev_vars_path, "r") as f:
            dev_vars_content = f.read()

    # Create one-line version of public key by replacing newlines with literal \n
    pub_key_oneline = pub_pem.replace("\n", "\\n")

    if "MCP_PUBLIC_KEY=" in dev_vars_content:
        dev_vars_content = re.sub(r"MCP_PUBLIC_KEY=.*", f'MCP_PUBLIC_KEY="{pub_key_oneline}"', dev_vars_content)
    else:
        if dev_vars_content and not dev_vars_content.endswith("\n"):
            dev_vars_content += "\n"
        dev_vars_content += f'MCP_PUBLIC_KEY="{pub_key_oneline}"\n'

    with open(dev_vars_path, "w") as f:
        f.write(dev_vars_content)

    print(f"SUCCESS: Updated {dev_vars_path} with new MCP_PUBLIC_KEY")

    # Construct JWT
    header = {"alg": "RS256", "typ": "JWT"}

    now = int(time.time())
    payload = {
        "iss": "owasp-blt-service",
        "aud": "toasty-mcp",
        "sub": "local-admin",
        "role": "developer",
        "iat": now,
        "exp": now + (86400 * 30),  # 30 day expiration for local dev
    }

    header_b64 = base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())

    signature_b64 = base64url_encode(signature)
    token = f"{header_b64}.{payload_b64}.{signature_b64}"

    with open(".test_token", "w") as f:
        f.write(token)

    print("\n" + "=" * 80)
    print("SUCCESSFULLY GENERATED ADMIN DASHBOARD TOKEN")
    print("=" * 80 + "\n")
    print(token)
    print("\n" + "=" * 80)
    print("\nInstructions:")
    print("1. Copy the token string above.")
    print("2. Open your React Dashboard in the browser.")
    print("3. Open Developer Tools (F12) -> Console.")
    print("4. Paste and run this command:")
    print(f"   localStorage.setItem('dashboard_token', '{token[:20]}...');")
    print("   (replace with the full token!)")
    print("5. Refresh the page.")


if __name__ == "__main__":
    generate_jwt()
