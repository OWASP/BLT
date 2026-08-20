---
layout: course
title: Cryptography for Developers
category: Cryptography
level: Advanced
duration: About 2 hours
instructor: OWASP BLT Community
featured: true
image: /assets/images/courses/crypto-for-devs.svg
prerequisites: General programming experience; no advanced mathematics required
description: Make safer engineering decisions about encoding, password storage, encryption, nonces, and signature verification.
outcomes:
  - Select a cryptographic primitive based on the property the feature needs.
  - Recognize unsafe nonce reuse, key rotation, and unverified-token patterns.
  - Put verification, validation, and authorization in the right order.
  - Choose failure behavior that does not expose a useful oracle.
lessons:
  - id: name-the-property
    title: Name the property you need
    intro: Encoding, hashing, encryption, and signing solve different problems even when their output looks similarly unreadable.
    body: |
      Encoding changes representation and is reversible without a secret. Hashing creates a fixed-size digest. Encryption protects confidentiality with a key. A signature lets someone verify origin and integrity.

      Start by naming the property. If the requirement is password verification, reversible encryption is the wrong primitive. Use a password-hashing function designed to be slow and salted.
    example:
      title: Unreadable is not encrypted
      language: Text
      code: |
        c2VjcmV0LXRva2Vu  →  secret-token
      note: Base64 is useful for transport. Anyone can decode it, so it provides no confidentiality.
    challenge:
      id: identify-password-control
      type: artifact
      title: Review the password record
      prompt: This record must support password verification without allowing recovery of the original password. Enter the missing primitive.
      answer: password hashing
      success: Correct. A salted password-hashing function supports verification without reversible storage.
      artifact:
        title: Storage requirement
        language: Design note
        code: |
          Need: verify a submitted password
          Must not: recover the original password
          Per-record random salt: yes
          Primitive: ?
  - id: uniqueness-is-part-of-the-key
    title: Uniqueness is part of the design
    intro: Modern encryption modes depend on nonces or initialization values that must follow precise reuse rules.
    body: |
      Developers tend to protect the key and treat the nonce as decoration. In several common modes, reusing a nonce with the same key can reveal relationships between messages or break authentication.

      Let a maintained cryptographic library generate the nonce. Store it beside the ciphertext, and design rotation so keys and encrypted records remain traceable.
    challenge:
      id: find-reused-nonce
      type: artifact
      title: Find the unsafe event
      prompt: Compare the mock encryption log. Enter the event ID that reused a nonce with the same key.
      answer: evt-103
      success: Event 103 repeats the key and nonce pair from event 101, so the operation must be rejected.
      artifact:
        title: Encryption log
        language: Log
        code: |
          evt-101  key=k7  nonce=8af2
          evt-102  key=k7  nonce=c410
          evt-103  key=k7  nonce=8af2
  - id: verify-before-use
    title: Verify before use
    intro: Encrypted or signed data is safe only when verification happens before the application acts on its contents.
    body: |
      Authenticated encryption produces ciphertext and an authentication tag. If tag verification fails, treat the whole message as untrusted and return one consistent error.

      The same order matters for tokens and signed payloads. Pin the accepted algorithm and key source, verify the signature, validate expiry and audience, then use claims for authorization.
    example:
      title: Safe processing order
      language: Pseudocode
      code: |
        payload = verify_and_decrypt(message, expected_key)
        if payload is invalid: reject
        if payload.audience != this_service: reject
        process(payload)
      note: Parsing unverified claims for a security decision puts trust before proof.
    observation: Before moving on, find the exact line in your own application where verification finishes and business logic begins.
    challenge:
      id: verification-order
      type: sequence
      title: Rebuild the trust boundary
      prompt: Put the token-processing steps in the only order that avoids using untrusted claims.
      answer: verify|validate|authorize
      success: Correct. The service proves integrity, validates context, and only then makes an authorization decision.
      options:
        - id: authorize
          label: Use the claims for authorization.
        - id: validate
          label: Validate expiry and audience.
        - id: verify
          label: Verify the signature with the expected key and algorithm.
  - id: rotate-with-key-identities
    title: Rotate with key identities
    intro: Rotation works when every ciphertext or signature can be connected to the key version that created it.
    body: |
      Give each key version a stable identifier and store that identifier beside the protected data. During rotation, write with the new key while retaining the old key only for the reads that still require it.

      Removing the old key before data is migrated creates an outage. Keeping it active for new writes means rotation never really finishes.
    challenge:
      id: select-decryption-key
      type: artifact
      title: Select the right key version
      prompt: The record was created before rotation and carries its key identifier. Enter the key the service must use to decrypt it.
      answer: key-v2
      success: Correct. The record identifies key-v2, so the reader does not have to guess from the creation date.
      artifact:
        title: Encrypted record
        language: JSON
        code: |
          {
            "created": "2026-06-04T10:16:00Z",
            "key_id": "key-v2",
            "ciphertext": "b7a91f..."
          }
  - id: do-not-build-an-oracle
    title: Do not build an oracle
    intro: Detailed cryptographic errors can reveal which part of a protected message was valid.
    body: |
      Return one consistent failure to the caller when signature, padding, tag, or format validation fails. Keep the detailed reason in restricted internal logs.

      Also keep the rejection path reasonably consistent. An attacker should not be able to distinguish a valid signature from a valid account by comparing messages or timing.
    challenge:
      id: uniform-failure
      type: choice
      title: Choose the safe failure
      prompt: A token fails verification. Which response gives the caller the least useful oracle?
      answer: uniform
      success: Correct. The caller receives one failure while operators retain the diagnostic detail internally.
      options:
        - id: signature
          label: Return Signature valid, but account does not exist.
        - id: algorithm
          label: Return Unsupported algorithm HS256 for this account.
        - id: uniform
          label: Return Invalid token and log the internal reason securely.
---

Most application cryptography failures are selection, storage, or verification mistakes rather than broken mathematics. This course focuses on those engineering decisions with short evidence reviews rather than mathematical puzzles.

The examples are intentionally language-neutral. In production, use a maintained library and a documented high-level construction instead of implementing a primitive yourself.
