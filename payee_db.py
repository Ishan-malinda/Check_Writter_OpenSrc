"""Local SQLite database for saving and retrieving payee names."""

import sqlite3
from pathlib import Path

import sys

if getattr(sys, "frozen", False):
    DB_PATH = Path(sys.executable).parent / "payees.db"
else:
    DB_PATH = Path(__file__).parent / "payees.db"


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "CREATE TABLE IF NOT EXISTS payees "
        "(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL COLLATE NOCASE, "
        "used_count INTEGER DEFAULT 1, last_used TEXT DEFAULT (date('now')))"
    )
    con.commit()
    return con


def save_payee(name: str):
    name = name.strip()
    if not name:
        return
    with _conn() as con:
        con.execute(
            "INSERT INTO payees (name) VALUES (?) "
            "ON CONFLICT(name) DO UPDATE SET "
            "used_count = used_count + 1, last_used = date('now')",
            (name,),
        )


def search_payees(prefix: str) -> list[str]:
    """Return payee names starting with prefix, ordered by usage frequency."""
    if not prefix:
        return []
    with _conn() as con:
        rows = con.execute(
            "SELECT name FROM payees WHERE name LIKE ? "
            "ORDER BY used_count DESC, name ASC LIMIT 20",
            (prefix.strip() + "%",),
        ).fetchall()
    return [r[0] for r in rows]


def all_payees() -> list[str]:
    with _conn() as con:
        rows = con.execute(
            "SELECT name FROM payees ORDER BY used_count DESC, name ASC"
        ).fetchall()
    return [r[0] for r in rows]
