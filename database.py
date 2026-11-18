import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path("gesture_login.db")
LOCK_SECONDS = 30
MAX_FAILED_ATTEMPTS = 3


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                gesture_salt TEXT NOT NULL,
                gesture_hash TEXT NOT NULL,
                failed_attempts INTEGER DEFAULT 0,
                locked_until TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS login_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                status TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL
            )
            """
        )


def create_user(username: str, password_salt: str, password_hash: str, gesture_salt: str, gesture_hash: str) -> bool:
    try:
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO users (username, password_salt, password_hash, gesture_salt, gesture_hash)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username, password_salt, password_hash, gesture_salt, gesture_hash),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def get_user(username: str):
    with connect() as conn:
        return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def is_locked(user) -> bool:
    locked_until = user["locked_until"]
    if not locked_until:
        return False
    return datetime.now() < datetime.fromisoformat(locked_until)


def lock_remaining_seconds(user) -> int:
    if not user["locked_until"]:
        return 0
    remaining = datetime.fromisoformat(user["locked_until"]) - datetime.now()
    return max(0, int(remaining.total_seconds()))


def record_failed_attempt(username: str):
    user = get_user(username)
    if user is None:
        return

    failed = user["failed_attempts"] + 1
    locked_until = None

    if failed >= MAX_FAILED_ATTEMPTS:
        locked_until = (datetime.now() + timedelta(seconds=LOCK_SECONDS)).isoformat(timespec="seconds")
        failed = 0

    with connect() as conn:
        conn.execute(
            "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE username = ?",
            (failed, locked_until, username),
        )


def reset_failed_attempts(username: str):
    with connect() as conn:
        conn.execute(
            "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE username = ?",
            (username,),
        )


def log_login(username: str, status: str, reason: str = ""):
    with connect() as conn:
        conn.execute(
            "INSERT INTO login_logs (username, status, reason, created_at) VALUES (?, ?, ?, ?)",
            (username, status, reason, datetime.now().isoformat(timespec="seconds")),
        )


def show_logs(limit: int = 10):
    with connect() as conn:
        return conn.execute(
            "SELECT username, status, reason, created_at FROM login_logs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
