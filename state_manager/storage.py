"""
Storage — SQLite backend for versioned state persistence.
Session-scoped: each session has its own version history.
"""
import sqlite3
import json
import os
from shared.config import STATE_VERSIONS_DIR
import logging

logger = logging.getLogger(__name__)
DB_PATH = str(STATE_VERSIONS_DIR / "state.db")


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL DEFAULT 'default',
            version INTEGER NOT NULL,
            state_json TEXT NOT NULL,
            asset_manifest TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT DEFAULT '',
            UNIQUE(session_id, version)
        )
    """)
    conn.commit()
    return conn


def save_version(version: int, state_json: dict, asset_paths: list = None,
                 description: str = "", session_id: str = "default"):
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO versions (session_id, version, state_json, asset_manifest, description) VALUES (?, ?, ?, ?, ?)",
        (session_id, version, json.dumps(state_json, default=str), json.dumps(asset_paths or []), description)
    )
    conn.commit()
    conn.close()
    logger.info(f"Saved version {version} for session {session_id}")


def load_version(version: int, session_id: str = "default") -> dict:
    conn = _get_conn()
    row = conn.execute(
        "SELECT state_json FROM versions WHERE session_id=? AND version=?",
        (session_id, version)
    ).fetchone()
    conn.close()
    if not row:
        raise KeyError(f"Version {version} not found for session {session_id}")
    return json.loads(row[0])


def list_versions(session_id: str = "default") -> list:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT version, created_at, description FROM versions WHERE session_id=? ORDER BY version",
        (session_id,)
    ).fetchall()
    conn.close()
    return [{"version": r[0], "created_at": r[1], "description": r[2]} for r in rows]


def get_latest_version(session_id: str = "default") -> int:
    conn = _get_conn()
    row = conn.execute(
        "SELECT MAX(version) FROM versions WHERE session_id=?",
        (session_id,)
    ).fetchone()
    conn.close()
    return row[0] if row[0] else 0
