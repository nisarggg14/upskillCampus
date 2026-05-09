"""
auth.py - Authentication logic: registration, login, session management,
          login-attempt limiting, and session timeout.
"""

import hashlib
import os
import time
from datetime import datetime, timedelta

import psycopg2.errors

from app.database import database as db
from app.utils.encryption import EncryptionManager


# ------------------------------------------------------------------ #
#  Constants                                                           #
# ------------------------------------------------------------------ #

MAX_ATTEMPTS   = 5          # lock after this many wrong passwords
LOCKOUT_MINS   = 15         # how long the account stays locked
SESSION_TIMEOUT_SECS = 300  # 5-minute inactivity timeout


# ------------------------------------------------------------------ #
#  Password hashing (PBKDF2-HMAC-SHA256)                               #
# ------------------------------------------------------------------ #

def _hash_password(password: str, salt: bytes) -> str:
    """Return a hex-encoded PBKDF2-HMAC-SHA256 hash."""
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        480_000,    # iteration count
    )
    return dk.hex()


def _verify_password(password: str, salt_hex: str, stored_hash: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    return _hash_password(password, salt) == stored_hash


# ------------------------------------------------------------------ #
#  Public API                                                          #
# ------------------------------------------------------------------ #

def register_user(username: str, master_password: str) -> dict:
    """
    Register a new user.
    Returns {"success": True, "user_id": ...} or {"success": False, "error": "..."}.
    """
    username = username.strip().lower()
    if not username or not master_password:
        return {"success": False, "error": "Username and password are required."}

    if len(master_password) < 8:
        return {"success": False, "error": "Master password must be at least 8 characters."}

    # Salt for hashing the master password
    hash_salt  = os.urandom(32)
    pw_hash    = _hash_password(master_password, hash_salt)

    # Separate salt for the encryption key (stored in enc_salt column)
    enc_mgr   = EncryptionManager()
    enc_salt  = enc_mgr.generate_salt()

    try:
        user_id = db.create_user(
            username    = username,
            password_hash = pw_hash,
            salt        = hash_salt.hex(),
            enc_salt    = enc_mgr.salt_to_hex(enc_salt),
        )
        return {"success": True, "user_id": user_id}
    except psycopg2.errors.UniqueViolation:
        return {"success": False, "error": "Username already taken."}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def login_user(username: str, master_password: str) -> dict:
    """
    Attempt login.
    Returns {"success": True, "user": <Row>, "enc_salt": <bytes>}
    or      {"success": False, "error": "..."}.
    """
    username = username.strip().lower()
    user = db.get_user(username)

    if user is None:
        return {"success": False, "error": "Invalid username or password."}

    # Check lockout
    if user["locked_until"]:
        locked_until = user["locked_until"]
        # psycopg2 returns aware datetime; normalise to naive UTC for comparison
        if hasattr(locked_until, "tzinfo") and locked_until.tzinfo is not None:
            import datetime as _dt
            locked_until = locked_until.replace(tzinfo=None)
        if datetime.utcnow() < locked_until:
            remaining = int((locked_until - datetime.utcnow()).total_seconds() / 60) + 1
            return {"success": False,
                    "error": f"Account locked. Try again in {remaining} minute(s)."}
        else:
            # Lockout expired — reset
            db.reset_failed_attempts(username)
            user = db.get_user(username)   # refresh

    # Verify password
    if not _verify_password(master_password, user["salt"], user["password_hash"]):
        attempts = user["failed_attempts"] + 1
        if attempts >= MAX_ATTEMPTS:
            locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINS)
            db.update_failed_attempts(username, attempts, locked_until)
            return {"success": False,
                    "error": f"Too many failed attempts. Account locked for {LOCKOUT_MINS} minutes."}
        db.update_failed_attempts(username, attempts, None)
        remaining_attempts = MAX_ATTEMPTS - attempts
        return {"success": False,
                "error": f"Invalid password. {remaining_attempts} attempt(s) remaining."}

    # Success
    db.reset_failed_attempts(username)
    enc_salt = bytes.fromhex(user["enc_salt"])
    return {"success": True, "user": user, "enc_salt": enc_salt}


# ------------------------------------------------------------------ #
#  Session                                                             #
# ------------------------------------------------------------------ #

class Session:
    """Lightweight in-memory session with idle timeout."""

    def __init__(self, user_id: int, username: str, enc_manager: EncryptionManager):
        self.user_id     = user_id
        self.username    = username
        self.enc_manager = enc_manager
        self._last_active = time.monotonic()

    def touch(self) -> None:
        """Reset the idle timer."""
        self._last_active = time.monotonic()

    def is_expired(self) -> bool:
        return (time.monotonic() - self._last_active) > SESSION_TIMEOUT_SECS

    def seconds_remaining(self) -> int:
        elapsed = time.monotonic() - self._last_active
        return max(0, int(SESSION_TIMEOUT_SECS - elapsed))
