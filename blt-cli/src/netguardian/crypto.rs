//! ztr-finding-1 cryptographic canonicalization and HMAC-SHA256 signing engine.
//!
//! Provides RFC 8785 JSON Canonicalization Scheme (JCS) encoding, SHA-256 digests,
//! and HMAC-SHA256 signature generation/verification for communication with the
//! BLT-NetGuardian ingest API (`POST /api/ingest`).

use base64::Engine;
use hmac::{Hmac, Mac};
use serde_json::Value;
use sha2::{Digest, Sha256};

type HmacSha256 = Hmac<Sha256>;

/// Canonicalize a JSON value to RFC 8785-compliant bytes (sorted keys, compact separators, UTF-8).
pub fn canonicalize_json(val: &Value) -> Result<Vec<u8>, String> {
    serde_jcs::to_vec(val).map_err(|e| format!("JCS canonicalization error: {e}"))
}

/// Canonicalize an envelope for signing by excluding the `signature` field if present.
pub fn canonicalize_envelope_for_signing(envelope: &Value) -> Result<Vec<u8>, String> {
    let mut unsigned = envelope.clone();
    if let Some(map) = unsigned.as_object_mut() {
        map.remove("signature");
    }
    canonicalize_json(&unsigned)
}

/// Compute standard lowercase SHA-256 hex string of raw bytes.
pub fn body_digest_hex(raw_body: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(raw_body);
    hex::encode(hasher.finalize())
}

/// Compute payload digest hex for either plaintext JSON or base64-encoded ciphertext.
/// Exactly one of `plaintext` or `ciphertext_b64` must be provided.
pub fn payload_digest_hex(
    plaintext: Option<&Value>,
    ciphertext_b64: Option<&str>,
) -> Result<String, String> {
    match (plaintext, ciphertext_b64) {
        (Some(_), Some(_)) => {
            Err("Exactly one payload mode permitted (dual payload detected)".into())
        }
        (None, None) => Err("Missing payload: neither plaintext nor ciphertext provided".into()),
        (Some(pt), None) => {
            let canon = canonicalize_json(pt)?;
            Ok(body_digest_hex(&canon))
        }
        (None, Some(ct_b64)) => {
            let bytes = base64::engine::general_purpose::STANDARD
                .decode(ct_b64)
                .map_err(|e| format!("Base64 decoding error: {e}"))?;
            Ok(body_digest_hex(&bytes))
        }
    }
}

/// Compute HMAC-SHA256 hex digest given secret bytes and message bytes.
pub fn hmac_sha256_hex(secret: &[u8], message: &[u8]) -> Result<String, String> {
    let mut mac = HmacSha256::new_from_slice(secret)
        .map_err(|e| format!("HMAC key initialization error: {e}"))?;
    mac.update(message);
    Ok(hex::encode(mac.finalize().into_bytes()))
}

/// Constant-time verification of an HMAC-SHA256 signature.
pub fn verify_hmac_sha256_hex(secret: &[u8], message: &[u8], signature_hex: &str) -> bool {
    let Ok(sig_bytes) = hex::decode(signature_hex) else {
        return false;
    };
    let Ok(mut mac) = HmacSha256::new_from_slice(secret) else {
        return false;
    };
    mac.update(message);
    mac.verify_slice(&sig_bytes).is_ok()
}

/// Prepares and signs a `ztr-finding-1` envelope.
///
/// Computes and inserts `payload_digest` if absent, canonicalizes the envelope
/// (excluding the `signature` field), signs it using the hex-encoded secret,
/// inserts the resulting `signature` string into the envelope, and returns the signature hex.
pub fn sign_envelope(envelope: &mut Value, secret_hex: &str) -> Result<String, String> {
    let secret = hex::decode(secret_hex).map_err(|e| format!("Invalid hex secret: {e}"))?;

    // 1. Ensure payload_digest is populated
    let needs_digest = match envelope.get("payload_digest") {
        Some(Value::String(s)) => s.is_empty(),
        Some(Value::Null) | None => true,
        _ => false,
    };

    if needs_digest {
        let plaintext = envelope.get("payload_plaintext");
        let ciphertext = envelope.get("payload_ciphertext").and_then(|v| v.as_str());
        let digest = payload_digest_hex(plaintext, ciphertext)?;
        envelope["payload_digest"] = Value::String(digest);
    }

    // 2. Canonicalize unsigned envelope
    let message = canonicalize_envelope_for_signing(envelope)?;

    // 3. Compute HMAC-SHA256
    let sig = hmac_sha256_hex(&secret, &message)?;

    // 4. Attach signature
    envelope["signature"] = Value::String(sig.clone());
    Ok(sig)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_canonicalize_json_sorts_keys() {
        let val = json!({"b": 1, "a": 2});
        let canon = canonicalize_json(&val).unwrap();
        assert_eq!(canon, br#"{"a":2,"b":1}"#);
    }

    #[test]
    fn test_canonicalize_json_handles_unicode() {
        let val = json!({"title": "café"});
        let canon = canonicalize_json(&val).unwrap();
        let s = String::from_utf8(canon).unwrap();
        assert_eq!(s, r#"{"title":"café"}"#);
    }

    #[test]
    fn test_signature_field_excluded_from_signing_input() {
        let envelope = json!({
            "version": "ztr-finding-1",
            "nonce": "n1",
            "signature": "deadbeef"
        });
        let unsigned = canonicalize_envelope_for_signing(&envelope).unwrap();
        let s = String::from_utf8(unsigned).unwrap();
        assert!(!s.contains("signature"));
        assert!(s.contains(r#""nonce":"n1""#));
    }

    #[test]
    fn test_body_digest_hex() {
        let raw = b"hello world";
        // sha256("hello world")
        assert_eq!(
            body_digest_hex(raw),
            "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        );
    }

    #[test]
    fn test_canonical_vectors_parity_with_python_backend() {
        // Matches blt-netguardian/tests/fixtures/canonical_vectors.json
        let mut envelope = json!({
            "version": "ztr-finding-1",
            "org_id": "org-demo",
            "sender_id": "scanner-1",
            "kid": "k1",
            "alg": "hmac-sha256",
            "issued_at": "2026-05-28T12:00:00Z",
            "nonce": "1748433600-abc",
            "plaintext_mode": true,
            "payload_plaintext": {
                "rule_id": "semgrep.test",
                "severity": "high",
                "title": "Test finding",
                "target": "https://example.com"
            }
        });
        let secret_hex = "736563726574";

        let sig = sign_envelope(&mut envelope, secret_hex).unwrap();

        // Exact values verified against Python backend
        assert_eq!(
            envelope["payload_digest"],
            "849d3d642065b4722904d0333ee8b2d435475e7e3ab9c6f7e44ae203a24e9bef"
        );
        assert_eq!(
            sig,
            "007e45fd05c38d9a7bce3a7ea80cf5edff7a7d2fa5199d93ccdf5fb243a1b3ce"
        );
        assert_eq!(envelope["signature"], sig);

        // Constant-time verification
        let secret = hex::decode(secret_hex).unwrap();
        let unsigned_msg = canonicalize_envelope_for_signing(&envelope).unwrap();
        assert!(verify_hmac_sha256_hex(&secret, &unsigned_msg, &sig));
        assert!(!verify_hmac_sha256_hex(
            &secret,
            &unsigned_msg,
            "0000000000000000"
        ));
    }

    #[test]
    fn test_tampered_envelope_fails_verification() {
        let mut envelope = json!({
            "version": "ztr-finding-1",
            "org_id": "org-demo",
            "sender_id": "scanner-1",
            "kid": "k1",
            "alg": "hmac-sha256",
            "issued_at": "2026-05-28T12:00:00Z",
            "nonce": "1748433600-abc",
            "plaintext_mode": true,
            "payload_plaintext": {
                "rule_id": "test",
                "severity": "low",
                "title": "Test",
                "target": "https://example.com"
            }
        });
        let secret_hex = "736563726574";
        let sig = sign_envelope(&mut envelope, secret_hex).unwrap();

        // Tamper with nonce
        envelope["nonce"] = json!("tampered-nonce");
        let secret = hex::decode(secret_hex).unwrap();
        let tampered_msg = canonicalize_envelope_for_signing(&envelope).unwrap();
        assert!(!verify_hmac_sha256_hex(&secret, &tampered_msg, &sig));
    }

    #[test]
    fn test_payload_digest_invalid_modes() {
        let pt = json!({"a": 1});
        assert!(payload_digest_hex(Some(&pt), Some("YQ==")).is_err());
        assert!(payload_digest_hex(None, None).is_err());
    }
}
