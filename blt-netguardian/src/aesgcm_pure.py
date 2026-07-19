"""Pure-Python AES-256-GCM used as a fallback when pyca/cryptography is absent.

The Cloudflare Workers Python runtime does not ship ``cryptography``, so the
evidence-encryption feature would otherwise be unavailable in production. This
module implements AES-256-GCM exactly per NIST SP 800-38D with the same wire
format as :class:`cryptography.hazmat.primitives.ciphers.aead.AESGCM`
(``encrypt`` returns ``ciphertext || 16-byte tag``; ``decrypt`` expects the same
layout). Ciphertext produced by a scanner using ``cryptography`` therefore
decrypts here, and vice-versa.

Only 12-byte nonces (the GCM-recommended size, and what this codebase uses) are
supported. Payloads are tiny finding evidence blobs, so raw-Python speed is a
non-issue.
"""

from __future__ import annotations

import hmac

# --- AES core -------------------------------------------------------------

_SBOX = (
    0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5, 0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
    0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0, 0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0,
    0xB7, 0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC, 0x34, 0xA5, 0xE5, 0xF1, 0x71, 0xD8, 0x31, 0x15,
    0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A, 0x07, 0x12, 0x80, 0xE2, 0xEB, 0x27, 0xB2, 0x75,
    0x09, 0x83, 0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0, 0x52, 0x3B, 0xD6, 0xB3, 0x29, 0xE3, 0x2F, 0x84,
    0x53, 0xD1, 0x00, 0xED, 0x20, 0xFC, 0xB1, 0x5B, 0x6A, 0xCB, 0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF,
    0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85, 0x45, 0xF9, 0x02, 0x7F, 0x50, 0x3C, 0x9F, 0xA8,
    0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5, 0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2,
    0xCD, 0x0C, 0x13, 0xEC, 0x5F, 0x97, 0x44, 0x17, 0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19, 0x73,
    0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A, 0x90, 0x88, 0x46, 0xEE, 0xB8, 0x14, 0xDE, 0x5E, 0x0B, 0xDB,
    0xE0, 0x32, 0x3A, 0x0A, 0x49, 0x06, 0x24, 0x5C, 0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79,
    0xE7, 0xC8, 0x37, 0x6D, 0x8D, 0xD5, 0x4E, 0xA9, 0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08,
    0xBA, 0x78, 0x25, 0x2E, 0x1C, 0xA6, 0xB4, 0xC6, 0xE8, 0xDD, 0x74, 0x1F, 0x4B, 0xBD, 0x8B, 0x8A,
    0x70, 0x3E, 0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E, 0x61, 0x35, 0x57, 0xB9, 0x86, 0xC1, 0x1D, 0x9E,
    0xE1, 0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E, 0x94, 0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
    0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68, 0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB, 0x16,
)

_RCON = (0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36, 0x6C, 0xD8, 0xAB, 0x4D)


def _xtime(a: int) -> int:
    a <<= 1
    if a & 0x100:
        a ^= 0x11B
    return a & 0xFF


def _mul(a: int, b: int) -> int:
    """Multiply two bytes in GF(2^8) used by AES MixColumns."""
    result = 0
    for _ in range(8):
        if b & 1:
            result ^= a
        b >>= 1
        a = _xtime(a)
    return result


def _key_expansion(key: bytes) -> list:
    """Expand a 32-byte key into 15 round keys (each 16 bytes)."""
    nk = 8
    nr = 14
    words = [list(key[4 * i:4 * i + 4]) for i in range(nk)]
    for i in range(nk, 4 * (nr + 1)):
        temp = list(words[i - 1])
        if i % nk == 0:
            temp = temp[1:] + temp[:1]
            temp = [_SBOX[b] for b in temp]
            temp[0] ^= _RCON[i // nk - 1]
        elif i % nk == 4:
            temp = [_SBOX[b] for b in temp]
        words.append([words[i - nk][j] ^ temp[j] for j in range(4)])
    round_keys = []
    for r in range(nr + 1):
        rk = bytes(words[4 * r + c][b] for c in range(4) for b in range(4))
        round_keys.append(rk)
    return round_keys


def _add_round_key(state: list, rk: bytes) -> None:
    for i in range(16):
        state[i] ^= rk[i]


def _sub_bytes(state: list) -> None:
    for i in range(16):
        state[i] = _SBOX[state[i]]


def _shift_rows(state: list) -> None:
    # state is column-major: index = col*4 + row
    new = list(state)
    for r in range(1, 4):
        for c in range(4):
            new[c * 4 + r] = state[((c + r) % 4) * 4 + r]
    state[:] = new


def _mix_columns(state: list) -> None:
    for c in range(4):
        i = c * 4
        s0, s1, s2, s3 = state[i], state[i + 1], state[i + 2], state[i + 3]
        state[i] = _mul(s0, 2) ^ _mul(s1, 3) ^ s2 ^ s3
        state[i + 1] = s0 ^ _mul(s1, 2) ^ _mul(s2, 3) ^ s3
        state[i + 2] = s0 ^ s1 ^ _mul(s2, 2) ^ _mul(s3, 3)
        state[i + 3] = _mul(s0, 3) ^ s1 ^ s2 ^ _mul(s3, 2)


def _encrypt_block(round_keys: list, block: bytes) -> bytes:
    state = list(block)
    nr = 14
    _add_round_key(state, round_keys[0])
    for rnd in range(1, nr):
        _sub_bytes(state)
        _shift_rows(state)
        _mix_columns(state)
        _add_round_key(state, round_keys[rnd])
    _sub_bytes(state)
    _shift_rows(state)
    _add_round_key(state, round_keys[nr])
    return bytes(state)


# --- GCM ------------------------------------------------------------------

def _gf_mult(x: int, y: int) -> int:
    """Multiply in GF(2^128) per NIST SP 800-38D (bit-reversed representation)."""
    z = 0
    v = y
    for i in range(127, -1, -1):
        if (x >> i) & 1:
            z ^= v
        if v & 1:
            v = (v >> 1) ^ (0xE1 << 120)
        else:
            v >>= 1
    return z


def _ghash(h: int, data: bytes) -> int:
    y = 0
    for i in range(0, len(data), 16):
        block = data[i:i + 16]
        if len(block) < 16:
            block = block + b"\x00" * (16 - len(block))
        y ^= int.from_bytes(block, "big")
        y = _gf_mult(y, h)
    return y


def _inc32(block: bytes) -> bytes:
    prefix = block[:12]
    counter = (int.from_bytes(block[12:], "big") + 1) & 0xFFFFFFFF
    return prefix + counter.to_bytes(4, "big")


def _gctr(round_keys: list, icb: bytes, data: bytes) -> bytes:
    if not data:
        return b""
    out = bytearray()
    cb = icb
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        keystream = _encrypt_block(round_keys, cb)
        out.extend(bytes(a ^ b for a, b in zip(chunk, keystream[:len(chunk)])))
        cb = _inc32(cb)
    return bytes(out)


class AESGCMPure:
    """AES-256-GCM with the same interface/wire format as cryptography's AESGCM."""

    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError("AESGCMPure requires a 32-byte (AES-256) key")
        self._round_keys = _key_expansion(key)
        self._h = int.from_bytes(_encrypt_block(self._round_keys, b"\x00" * 16), "big")

    def _tag(self, nonce: bytes, ciphertext: bytes, aad: bytes) -> bytes:
        j0 = nonce + b"\x00\x00\x00\x01"
        len_block = (len(aad) * 8).to_bytes(8, "big") + (len(ciphertext) * 8).to_bytes(8, "big")

        def _pad(b: bytes) -> bytes:
            rem = len(b) % 16
            return b + (b"\x00" * (16 - rem)) if rem else b

        ghash_input = _pad(aad) + _pad(ciphertext) + len_block
        s = _ghash(self._h, ghash_input)
        e_j0 = _encrypt_block(self._round_keys, j0)
        return bytes(a ^ b for a, b in zip(s.to_bytes(16, "big"), e_j0))

    def encrypt(self, nonce: bytes, data: bytes, associated_data) -> bytes:
        if len(nonce) != 12:
            raise ValueError("AESGCMPure supports only 12-byte nonces")
        aad = associated_data or b""
        j0 = nonce + b"\x00\x00\x00\x01"
        ciphertext = _gctr(self._round_keys, _inc32(j0), data)
        tag = self._tag(nonce, ciphertext, aad)
        return ciphertext + tag

    def decrypt(self, nonce: bytes, data: bytes, associated_data) -> bytes:
        if len(nonce) != 12:
            raise ValueError("AESGCMPure supports only 12-byte nonces")
        if len(data) < 16:
            raise ValueError("ciphertext too short for GCM tag")
        aad = associated_data or b""
        ciphertext, tag = data[:-16], data[-16:]
        expected = self._tag(nonce, ciphertext, aad)
        if not hmac.compare_digest(expected, tag):
            raise ValueError("GCM tag verification failed")
        j0 = nonce + b"\x00\x00\x00\x01"
        return _gctr(self._round_keys, _inc32(j0), ciphertext)
