"""The pure-Python AES-256-GCM fallback must match pyca/cryptography exactly.

This guards the Cloudflare Workers deployment, where ``cryptography`` is
unavailable and :mod:`aesgcm_pure` backs evidence encryption.
"""

from __future__ import annotations

import os

import pytest

from aesgcm_pure import AESGCMPure

cryptography_aead = pytest.importorskip(
    "cryptography.hazmat.primitives.ciphers.aead"
)
AESGCM = cryptography_aead.AESGCM


def test_pure_roundtrip():
    key = os.urandom(32)
    nonce = os.urandom(12)
    pt = b'{"rule_id":"sqli","password":"hunter2"}'
    aad = b"org-a"
    ct = AESGCMPure(key).encrypt(nonce, pt, aad)
    assert AESGCMPure(key).decrypt(nonce, ct, aad) == pt


def test_pure_matches_cryptography_wire_format():
    for _ in range(50):
        key = os.urandom(32)
        nonce = os.urandom(12)
        pt = os.urandom(1 + (os.urandom(1)[0] % 96))
        aad = os.urandom(os.urandom(1)[0] % 48)
        ref = AESGCM(key).encrypt(nonce, pt, aad or None)
        mine = AESGCMPure(key).encrypt(nonce, pt, aad or None)
        assert ref == mine
        # cross-decrypt both directions
        assert AESGCMPure(key).decrypt(nonce, ref, aad or None) == pt
        assert AESGCM(key).decrypt(nonce, mine, aad or None) == pt


def test_pure_rejects_tampered_tag():
    key = os.urandom(32)
    nonce = os.urandom(12)
    ct = bytearray(AESGCMPure(key).encrypt(nonce, b"secret", b"aad"))
    ct[-1] ^= 0x01
    with pytest.raises(ValueError):
        AESGCMPure(key).decrypt(nonce, bytes(ct), b"aad")


def test_pure_rejects_bad_nonce_and_key():
    with pytest.raises(ValueError):
        AESGCMPure(b"short")
    with pytest.raises(ValueError):
        AESGCMPure(os.urandom(32)).encrypt(os.urandom(16), b"x", b"")
