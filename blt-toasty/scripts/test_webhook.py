import urllib.request
import urllib.parse
import json
import time
import uuid
import hmac
import hashlib
import base64
import os

# Configuration
WEBHOOK_URL = "http://127.0.0.1:8787/webhook/gitlab"

# You can hardcode your secret here or read it from .dev.vars
WEBHOOK_SECRET = "YOUR_SECRET_TOKEN"
if os.path.exists(".dev.vars"):
    with open(".dev.vars", "r") as f:
        for line in f:
            if line.startswith("GITLAB_WEBHOOK_SECRET="):
                WEBHOOK_SECRET = line.strip().split("=", 1)[1].strip("\"'")
                break

print(f"Using secret: {WEBHOOK_SECRET}")

# Payload
payload = {
    "object_kind": "issue",
    "event_type": "issue",
    "object_attributes": {
        "id": 12345,
        "iid": 12345,
        "project_id": 1,
        "title": "SQL Injection found in search bar",
        "description": "I found a blind SQL injection at myemail@example.com",
        "state": "opened",
        "action": "open",
    },
    "project": {"id": 1},
}
body = json.dumps(payload, separators=(",", ":"))

# Calculate HMAC Signature
webhook_id = str(uuid.uuid4())
timestamp = str(int(time.time()))
message = f"{webhook_id}.{timestamp}.{body}"

raw_key = WEBHOOK_SECRET.replace("whsec_", "")
# In case the secret is not base64 encoded natively, we fall back to encoding it
try:
    key_bytes = base64.b64decode(raw_key)
except Exception:
    key_bytes = raw_key.encode("utf-8")

signature = hmac.new(key_bytes, message.encode("utf-8"), hashlib.sha256).digest()
computed_signature = base64.b64encode(signature).decode("utf-8")

# Headers
headers = {
    "Content-Type": "application/json",
    "X-Gitlab-Event": "Issue Hook",
    "X-Gitlab-Event-UUID": str(uuid.uuid4()),
    "webhook-id": webhook_id,
    "webhook-timestamp": timestamp,
    "webhook-signature": f"v1,{computed_signature}",
}

print("Sending webhook request...")
req = urllib.request.Request(WEBHOOK_URL, data=body.encode("utf-8"), headers=headers, method="POST")

try:
    with urllib.request.urlopen(req) as response:
        print(f"Status Code: {response.status}")
        print("Response:", response.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print("Response:", e.read().decode("utf-8"))
except Exception as e:
    print(f"Error: {e}")
