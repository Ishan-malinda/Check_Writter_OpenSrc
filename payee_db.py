"""Local SQLite database for saving and retrieving payee names.

Stores data in %APPDATA%/Growvia/ChequeWriter/payees.db so payee history
persists across updates, PC installations, and non-admin environments.
"""

import os
import shutil
import sqlite3
import sys
from pathlib import Path


def _resolve_db_path() -> Path:
    """Resolve database path, preferring %APPDATA% for installed applications,
    with automatic migration from legacy local payees.db.
    """
    appdata = os.environ.get("APPDATA")
    if appdata:
        app_dir = Path(appdata) / "Growvia" / "ChequeWriter"
        try:
            app_dir.mkdir(parents=True, exist_ok=True)
            appdata_db = app_dir / "payees.db"

            # Auto-migrate legacy local db if it exists and appdata db is new
            local_db = (
                Path(sys.executable).parent
                if getattr(sys, "frozen", False)
                else Path(__file__).parent
            ) / "payees.db"
            if not appdata_db.exists() and local_db.exists():
                try:
                    shutil.copy2(local_db, appdata_db)
                except Exception:
                    pass
            return appdata_db
        except Exception:
            pass

    # Fallback to local executable/source folder
    base_dir = (
        Path(sys.executable).parent
        if getattr(sys, "frozen", False)
        else Path(__file__).parent
    )
    return base_dir / "payees.db"


DB_PATH = _resolve_db_path()


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
            "ORDER BY used_count DESC, name ASC LIMIT 25",
            (prefix.strip() + "%",),
        ).fetchall()
    return [r[0] for r in rows]


def all_payees() -> list[str]:
    with _conn() as con:
        rows = con.execute(
            "SELECT name FROM payees ORDER BY used_count DESC, name ASC"
        ).fetchall()
    return [r[0] for r in rows]
