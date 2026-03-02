/**
 * BLT-SafeCloak — crypto.js
 * End-to-end encryption helpers using the Web Crypto API (AES-GCM, 256-bit)
 */

const Crypto = (() => {
  const ENC = 'AES-GCM';
  const KEY_BITS = 256;
  const enc = new TextEncoder();
  const dec = new TextDecoder();

  /** Generate a new AES-GCM key */
  async function generateKey() {
    return crypto.subtle.generateKey({ name: ENC, length: KEY_BITS }, true, ['encrypt', 'decrypt']);
  }

  /** Export a CryptoKey to base64 string */
  async function exportKey(key) {
    const raw = await crypto.subtle.exportKey('raw', key);
    return btoa(String.fromCharCode(...new Uint8Array(raw)));
  }

  /** Import a base64 key string to CryptoKey */
  async function importKey(b64) {
    const raw = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
    return crypto.subtle.importKey('raw', raw, { name: ENC }, true, ['encrypt', 'decrypt']);
  }

  /** Derive a CryptoKey from a passphrase using PBKDF2.
   *  @param {string} passphrase - Secret passphrase
   *  @param {string} salt - Required: callers MUST provide a unique salt per key context (e.g. storageKey).
   *                         The default 'blt-safecloak-v1' is only used as a last resort and weakens isolation.
   */
  async function deriveKey(passphrase, salt) {
    if (!salt) console.warn('deriveKey: no salt provided — pass a context-specific salt for stronger key isolation');
    const keyMaterial = await crypto.subtle.importKey(
      'raw', enc.encode(passphrase), 'PBKDF2', false, ['deriveKey']
    );
    return crypto.subtle.deriveKey(
      { name: 'PBKDF2', salt: enc.encode(salt || 'blt-safecloak-v1'), iterations: 100000, hash: 'SHA-256' },
      keyMaterial,
      { name: ENC, length: KEY_BITS },
      true, ['encrypt', 'decrypt']
    );
  }

  /** Encrypt a string, returns { iv, ciphertext } as base64 */
  async function encrypt(plaintext, key) {
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const ct = await crypto.subtle.encrypt({ name: ENC, iv }, key, enc.encode(plaintext));
    return {
      iv: btoa(String.fromCharCode(...iv)),
      ciphertext: btoa(String.fromCharCode(...new Uint8Array(ct)))
    };
  }

  /** Decrypt { iv, ciphertext } base64 pair, returns plaintext string */
  async function decrypt({ iv, ciphertext }, key) {
    const ivBuf = Uint8Array.from(atob(iv), c => c.charCodeAt(0));
    const ctBuf = Uint8Array.from(atob(ciphertext), c => c.charCodeAt(0));
    const pt = await crypto.subtle.decrypt({ name: ENC, iv: ivBuf }, key, ctBuf);
    return dec.decode(pt);
  }

  /** Compute SHA-256 hash of a string, returns hex string */
  async function sha256(text) {
    const buf = await crypto.subtle.digest('SHA-256', enc.encode(text));
    return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
  }

  /** Generate a random session ID */
  function randomId(len = 8) {
    // chars.length is 32 (2^5), so the bitmask 0x1f gives an unbiased index (no modulo bias)
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    return Array.from(crypto.getRandomValues(new Uint8Array(len)))
      .map(b => chars[b & 0x1f]).join('');
  }

  /** Encrypt an object and store in localStorage */
  async function saveEncrypted(storageKey, obj, passphrase) {
    const key = await deriveKey(passphrase, storageKey);
    const json = JSON.stringify(obj);
    const encrypted = await encrypt(json, key);
    localStorage.setItem(storageKey, JSON.stringify(encrypted));
  }

  /** Load and decrypt an object from localStorage */
  async function loadEncrypted(storageKey, passphrase) {
    const raw = localStorage.getItem(storageKey);
    if (!raw) return null;
    try {
      const key = await deriveKey(passphrase, storageKey);
      const payload = JSON.parse(raw);
      const json = await decrypt(payload, key);
      return JSON.parse(json);
    } catch {
      return null;
    }
  }

  return { generateKey, exportKey, importKey, deriveKey, encrypt, decrypt, sha256, randomId, saveEncrypted, loadEncrypted };
})();
