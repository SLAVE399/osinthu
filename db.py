"""
SQLite storage layer.

Tables:
  users          - wallet / referral / spin data
  settings       - key/value bot settings (maintenance mode, banner image)
  admins         - dynamic list of admin user IDs
  force_channels - dynamically managed list of channels users must join
"""

import sqlite3
import time
from contextlib import contextmanager

DB_PATH = "bot.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                credits INTEGER DEFAULT 0,
                referred_by INTEGER,
                is_verified INTEGER DEFAULT 0,
                joined_at INTEGER,
                last_spin INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS force_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT UNIQUE,
                invite_link TEXT,
                title TEXT
            )
            """
        )
        conn.commit()


# ---------------------------------------------------------------- users ----
def get_user(user_id: int):
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return cur.fetchone()


def create_user(user_id: int, name: str, referred_by: int = None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO users (user_id, name, credits, referred_by, is_verified, joined_at) "
            "VALUES (?, ?, 0, ?, 1, ?)",
            (user_id, name, referred_by, int(time.time())),
        )
        conn.commit()


def update_credits(user_id: int, delta: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET credits = credits + ? WHERE user_id = ?", (delta, user_id)
        )
        conn.commit()


def set_verified(user_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE users SET is_verified = 1 WHERE user_id = ?", (user_id,))
        conn.commit()


def get_referral_count(user_id: int) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT COUNT(*) as c FROM users WHERE referred_by = ?", (user_id,)
        )
        return cur.fetchone()["c"]


def update_last_spin(user_id: int, ts: int):
    with get_conn() as conn:
        conn.execute("UPDATE users SET last_spin = ? WHERE user_id = ?", (ts, user_id))
        conn.commit()


def count_users() -> int:
    with get_conn() as conn:
        cur = conn.execute("SELECT COUNT(*) as c FROM users")
        return cur.fetchone()["c"]


# ------------------------------------------------------------- settings ----
def get_setting(key: str, default=None):
    with get_conn() as conn:
        cur = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()


# --------------------------------------------------------------- admins ----
def is_admin(user_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
        return cur.fetchone() is not None


def add_admin(user_id: int):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
        conn.commit()


def list_admins():
    with get_conn() as conn:
        cur = conn.execute("SELECT user_id FROM admins")
        return [r["user_id"] for r in cur.fetchall()]


# --------------------------------------------------------- force channels --
def add_force_channel(chat_id: str, invite_link: str, title: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO force_channels (chat_id, invite_link, title) "
            "VALUES (?, ?, ?)",
            (chat_id, invite_link, title),
        )
        conn.commit()


def remove_force_channel(channel_row_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM force_channels WHERE id = ?", (channel_row_id,))
        conn.commit()


def list_force_channels():
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM force_channels ORDER BY id")
        return cur.fetchall()
