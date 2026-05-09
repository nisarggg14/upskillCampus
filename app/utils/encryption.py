"""
encryption.py - Handles all encryption/decryption operations
Uses Fernet symmetric encryption (AES-128-CBC under the hood)
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class EncryptionManager:
    """
    Manages encryption and decryption of passwords.
    Uses a master-password-derived key so every user has a unique encryption key.
    """

    def __init__(self):
        self._fernet = None

    # ------------------------------------------------------------------ #
    #  Key derivation                                                       #
    # ------------------------------------------------------------------ #

    def derive_key(self, master_password: str, salt: bytes) -> bytes:
        """
        Derive a 32-byte key from the master password + salt using PBKDF2-HMAC-SHA256.
        Returns the raw key bytes (NOT base64-encoded).
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480_000,   # NIST-recommended minimum (2023)
        )
        return kdf.derive(master_password.encode("utf-8"))

    def init_cipher(self, master_password: str, salt: bytes) -> None:
        """Initialise the Fernet cipher from master_password + salt."""
        raw_key = self.derive_key(master_password, salt)
        fernet_key = base64.urlsafe_b64encode(raw_key)
        self._fernet = Fernet(fernet_key)

    # ------------------------------------------------------------------ #
    #  Encrypt / Decrypt                                                    #
    # ------------------------------------------------------------------ #

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string; returns a UTF-8 token string."""
        if self._fernet is None:
            raise RuntimeError("Cipher not initialised. Call init_cipher() first.")
        token = self._fernet.encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, token: str) -> str:
        """Decrypt a token string; returns the original plaintext."""
        if self._fernet is None:
            raise RuntimeError("Cipher not initialised. Call init_cipher() first.")
        plaintext = self._fernet.decrypt(token.encode("utf-8"))
        return plaintext.decode("utf-8")

    # ------------------------------------------------------------------ #
    #  Salt helpers                                                         #
    # ------------------------------------------------------------------ #

    @staticmethod
    def generate_salt() -> bytes:
        """Generate a cryptographically-secure 16-byte salt."""
        return os.urandom(16)

    @staticmethod
    def salt_to_hex(salt: bytes) -> str:
        return salt.hex()

    @staticmethod
    def hex_to_salt(hex_str: str) -> bytes:
        return bytes.fromhex(hex_str)

    # ------------------------------------------------------------------ #
    #  Export helpers  (for the encrypted-export feature)                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def encrypt_export(data: str, passphrase: str) -> bytes:
        """Encrypt export data with a user-supplied passphrase."""
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480_000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
        f = Fernet(key)
        encrypted = f.encrypt(data.encode("utf-8"))
        # Prepend salt so we can re-derive the key on import
        return salt + encrypted

    @staticmethod
    def decrypt_export(blob: bytes, passphrase: str) -> str:
        """Decrypt an export blob produced by encrypt_export()."""
        salt, encrypted = blob[:16], blob[16:]
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480_000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
        f = Fernet(key)
        return f.decrypt(encrypted).decode("utf-8")
