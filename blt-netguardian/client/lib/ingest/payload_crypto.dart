/// AES-256-GCM payload encryption matching `src/payload_crypto.py`.
library;

import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:cryptography/cryptography.dart';

const encAlg = 'aes-256-gcm';
const nonceBytes = 12;
const keyBytes = 32;

class PayloadCryptoException implements Exception {
  PayloadCryptoException(this.message);
  final String message;
  @override
  String toString() => 'PayloadCryptoException: $message';
}

Uint8List payloadKeyFromB64(String b64) {
  final key = base64Decode(b64.trim());
  if (key.length != keyBytes) {
    throw PayloadCryptoException('payload key must be 32 bytes (base64)');
  }
  return Uint8List.fromList(key);
}

Uint8List randomNonce() {
  final rng = Random.secure();
  return Uint8List.fromList(List<int>.generate(nonceBytes, (_) => rng.nextInt(256)));
}

/// Encrypt [payload] as compact JSON; return base64(nonce || ciphertext || tag).
Future<String> encryptPayload({
  required Uint8List key,
  required Map<String, Object?> payload,
  required List<int> aad,
  Uint8List? nonce,
}) async {
  if (key.length != keyBytes) {
    throw PayloadCryptoException('key must be 32 bytes for AES-256-GCM');
  }
  final n = nonce ?? randomNonce();
  if (n.length != nonceBytes) {
    throw PayloadCryptoException('nonce must be 12 bytes for AES-256-GCM');
  }
  final plaintext = utf8.encode(
    jsonEncode(payload),
  );
  final algorithm = AesGcm.with256bits();
  final box = await algorithm.encrypt(
    plaintext,
    secretKey: SecretKey(key),
    nonce: n,
    aad: aad,
  );
  final blob = Uint8List.fromList([...n, ...box.cipherText, ...box.mac.bytes]);
  return base64Encode(blob);
}

Future<Map<String, Object?>> decryptPayload({
  required Uint8List key,
  required String tokenB64,
  required List<int> aad,
}) async {
  if (key.length != keyBytes) {
    throw PayloadCryptoException('key must be 32 bytes for AES-256-GCM');
  }
  late final Uint8List blob;
  try {
    blob = Uint8List.fromList(base64Decode(tokenB64));
  } catch (e) {
    throw PayloadCryptoException('ciphertext is not valid base64');
  }
  if (blob.length <= nonceBytes + 16) {
    throw PayloadCryptoException('ciphertext too short');
  }
  final nonce = blob.sublist(0, nonceBytes);
  final mac = blob.sublist(blob.length - 16);
  final cipherText = blob.sublist(nonceBytes, blob.length - 16);
  final algorithm = AesGcm.with256bits();
  try {
    final clear = await algorithm.decrypt(
      SecretBox(cipherText, nonce: nonce, mac: Mac(mac)),
      secretKey: SecretKey(key),
      aad: aad,
    );
    final decoded = jsonDecode(utf8.decode(clear));
    if (decoded is! Map) {
      throw PayloadCryptoException('decrypted payload must be a JSON object');
    }
    return decoded.map((k, v) => MapEntry(k.toString(), v as Object?));
  } catch (e) {
    if (e is PayloadCryptoException) rethrow;
    throw PayloadCryptoException('decryption failed (wrong key or tampered ciphertext)');
  }
}
