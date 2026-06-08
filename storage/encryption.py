"""AES-256-GCM encryption helpers for PHTA health data.

All persistent health records must be encrypted at rest per Rule M-5.
This module provides the primitives: key generation, encrypt, decrypt.

Usage:
    key = EncryptionKey.generate()
    key.save_to_env("HEALTH_DB_ENCRYPTION_KEY")

    ciphertext = encrypt(plaintext_bytes, key)
    plaintext = decrypt(ciphertext, key)
"""

from __future__ import annotations

import os
import secrets
from base64 import urlsafe_b64decode, urlsafe_b64encode

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# ── public API ──────────────────────────────────────────────────────

class EncryptionKey:
    """Thin wrapper around a 256-bit key with serialisation helpers."""

    __slots__ = ("_raw",)

    def __init__(self, raw: bytes) -> None:
        if len(raw) != 32:
            raise ValueError("Encryption key must be exactly 32 bytes (AES-256)")
        self._raw = raw

    @classmethod
    def generate(cls) -> EncryptionKey:
        """Generate a cryptographically random 256-bit key."""
        return cls(AESGCM.generate_key(bit_length=256))

    @classmethod
    def from_base64(cls, b64: str) -> EncryptionKey:
        return cls(urlsafe_b64decode(b64 + "=="))

    @classmethod
    def from_env(cls, env_var: str = "HEALTH_DB_ENCRYPTION_KEY") -> EncryptionKey:
        val = os.environ.get(env_var)
        if not val:
            raise RuntimeError(f"Environment variable {env_var} is not set")
        return cls.from_base64(val)

    def to_base64(self) -> str:
        return urlsafe_b64encode(self._raw).rstrip(b"=").decode("ascii")

    @property
    def raw(self) -> bytes:
        return self._raw


def encrypt(plaintext: bytes, key: EncryptionKey) -> bytes:
    """Return *nonce || ciphertext*.  Nonce is 12 bytes (NIST-recommended)."""
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(key.raw).encrypt(nonce, plaintext, associated_data=None)
    return nonce + ciphertext


def decrypt(payload: bytes, key: EncryptionKey) -> bytes:
    """Recover plaintext from *nonce || ciphertext*."""
    if len(payload) < 28:  # 12 nonce + 16 tag minimum
        raise ValueError("Ciphertext too short to be valid AES-256-GCM")
    nonce = payload[:12]
    ciphertext = payload[12:]
    return AESGCM(key.raw).decrypt(nonce, ciphertext, associated_data=None)


def generate_key_command() -> None:
    """CLI entry-point: *phta-keygen*."""
    key = EncryptionKey.generate()
    print(f"Add this to your environment:\n\nexport HEALTH_DB_ENCRYPTION_KEY={key.to_base64()}")
