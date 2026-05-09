"""
database.py - All PostgreSQL (NeonDB) operations for PassVault.
Uses psycopg2 with parameterised queries (%s placeholders) throughout.
Connection string is read from the DATABASE_URL environment variable
(or from a .env file via python-dotenv).
"""

import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras          # RealDictCursor — dict-like row access
from dotenv import load_dotenv

# Load .env from the project root
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(dotenv_path=os.path.join(ROOT_DIR, ".env"))

_DATABASE_URL: str | None = os.getenv("DATABASE_URL")


# ------------------------------------------------------------------ #
#  Connection helper                                                   #
# ------------------------------------------------------------------ #

def _get_url() -> str:
    url = _DATABASE_URL or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set.\n"
            "Create a .env file in the project folder with:\n"
            "  DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require"
        )
    return url


@contextmanager
def _conn():
    """
    Context manager that yields a psycopg2 connection.
    Commits on clean exit, rolls back on exception, always closes.
    """
    try:
        conn = psycopg2.connect(_get_url(), cursor_factory=psycopg2.extras.RealDictCursor)
    except psycopg2.OperationalError as e:
        raise RuntimeError(f"Failed to connect to database: {e}") from e
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ------------------------------------------------------------------ #
#  Schema initialisation                                               #
# ------------------------------------------------------------------ #

def init_db() -> None:
    """Create tables and indexes if they do not exist yet."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id              SERIAL PRIMARY KEY,
                    username        TEXT    NOT NULL UNIQUE,
                    password_hash   TEXT    NOT NULL,
                    salt            TEXT    NOT NULL,
                    enc_salt        TEXT    NOT NULL,
                    created_at      TIMESTAMPTZ DEFAULT NOW(),
                    failed_attempts INTEGER     DEFAULT 0,
                    locked_until    TIMESTAMPTZ DEFAULT NULL
                );

                CREATE TABLE IF NOT EXISTS credentials (
                    id          SERIAL PRIMARY KEY,
                    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    website     TEXT    NOT NULL,
                    username    TEXT    NOT NULL,
                    password    TEXT    NOT NULL,
                    notes       TEXT    DEFAULT '',
                    created_at  TIMESTAMPTZ DEFAULT NOW(),
                    updated_at  TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_cred_user
                    ON credentials(user_id);

                CREATE INDEX IF NOT EXISTS idx_cred_website
                    ON credentials(user_id, lower(website));
            """)


# ------------------------------------------------------------------ #
#  User operations                                                     #
# ------------------------------------------------------------------ #

def create_user(username: str, password_hash: str, salt: str, enc_salt: str) -> int:
    """
    Insert a new user.
    Raises psycopg2.errors.UniqueViolation on duplicate username.
    Returns the new user id.
    """
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (username, password_hash, salt, enc_salt)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (username, password_hash, salt, enc_salt),
            )
            return cur.fetchone()["id"]


def get_user(username: str) -> dict | None:
    """Fetch a user row by username; returns a dict or None."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            return cur.fetchone()


def update_failed_attempts(username: str, attempts: int, locked_until) -> None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET failed_attempts=%s, locked_until=%s WHERE username=%s",
                (attempts, locked_until, username),
            )


def reset_failed_attempts(username: str) -> None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET failed_attempts=0, locked_until=NULL WHERE username=%s",
                (username,),
            )


# ------------------------------------------------------------------ #
#  Credential CRUD                                                     #
# ------------------------------------------------------------------ #

def add_credential(user_id: int, website: str, username: str,
                   password: str, notes: str = "") -> int:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO credentials (user_id, website, username, password, notes)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (user_id, website, username, password, notes),
            )
            return cur.fetchone()["id"]


def get_credentials(user_id: int) -> list[dict]:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM credentials WHERE user_id=%s ORDER BY lower(website)",
                (user_id,),
            )
            return cur.fetchall()


def search_credentials(user_id: int, query: str) -> list[dict]:
    pattern = f"%{query.lower()}%"
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM credentials
                WHERE user_id=%s
                  AND (lower(website) LIKE %s OR lower(username) LIKE %s)
                ORDER BY lower(website)
                """,
                (user_id, pattern, pattern),
            )
            return cur.fetchall()


def get_credential_by_id(cred_id: int, user_id: int) -> dict | None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM credentials WHERE id=%s AND user_id=%s",
                (cred_id, user_id),
            )
            return cur.fetchone()


def update_credential(cred_id: int, user_id: int, website: str,
                      username: str, password: str, notes: str) -> None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE credentials
                SET website=%s, username=%s, password=%s, notes=%s, updated_at=NOW()
                WHERE id=%s AND user_id=%s
                """,
                (website, username, password, notes, cred_id, user_id),
            )


def delete_credential(cred_id: int, user_id: int) -> None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM credentials WHERE id=%s AND user_id=%s",
                (cred_id, user_id),
            )


def count_credentials(user_id: int) -> int:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM credentials WHERE user_id=%s",
                (user_id,),
            )
            return cur.fetchone()["cnt"]
