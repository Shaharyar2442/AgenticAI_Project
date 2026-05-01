"""
Storage — SQLite backend for versioned state persistence.
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
            version INTEGER PRIMARY KEY,
            state_json TEXT NOT NULL,
            asset_manifest TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT DEFAULT ''
        )
    """)
    conn.commit()
    return conn


def save_version(version: int, state_json: dict, asset_paths: list = None, description: str = ""):
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO versions (version, state_json, asset_manifest, description) VALUES (?, ?, ?, ?)",
        (version, json.dumps(state_json, default=str), json.dumps(asset_paths or []), description)
    )
    conn.commit()
    conn.close()
    logger.info(f"Saved version {version}")


def load_version(version: int) -> dict:
    conn = _get_conn()
    row = conn.execute("SELECT state_json FROM versions WHERE version=?", (version,)).fetchone()
    conn.close()
    if not row:
        raise KeyError(f"Version {version} not found")
    return json.loads(row[0])


def list_versions() -> list:
    conn = _get_conn()
    rows = conn.execute("SELECT version, created_at, description FROM versions ORDER BY version").fetchall()
    conn.close()
    return [{"version": r[0], "created_at": r[1], "description": r[2]} for r in rows]


def get_latest_version() -> int:
    conn = _get_conn()
    row = conn.execute("SELECT MAX(version) FROM versions").fetchone()
    conn.close()
    return row[0] if row[0] else 0
