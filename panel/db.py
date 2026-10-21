"""Tiny SQLite layer (stdlib only) for users, instances and panel settings."""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    pwhash   TEXT NOT NULL,
    created  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS instances (
    id       TEXT PRIMARY KEY,
    name     TEXT NOT NULL,
    game     TEXT NOT NULL,
    cfg      TEXT NOT NULL,
    created  INTEGER NOT NULL,
    updated  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    ts    INTEGER NOT NULL,
    kind  TEXT NOT NULL,
    ref   TEXT,
    text  TEXT NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    config.ensure_dirs()
    conn = sqlite3.connect(config.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init() -> None:
    with connect() as conn:
        conn.executescript(_SCHEMA)


# --- instances -----------------------------------------------------------------

def list_instances() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM instances ORDER BY name").fetchall()
    return [_row_to_instance(r) for r in rows]


def get_instance(iid: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM instances WHERE id=?", (iid,)).fetchone()
    return _row_to_instance(row) if row else None


def save_instance(inst: dict[str, Any]) -> dict[str, Any]:
    now = int(time.time())
    cfg = json.dumps(inst, ensure_ascii=False)
    with connect() as conn:
        exists = conn.execute("SELECT 1 FROM instances WHERE id=?", (inst["id"],)).fetchone()
        if exists:
            conn.execute("UPDATE instances SET name=?, game=?, cfg=?, updated=? WHERE id=?",
                         (inst["name"], inst["game"], cfg, now, inst["id"]))
        else:
            conn.execute("INSERT INTO instances (id,name,game,cfg,created,updated) VALUES (?,?,?,?,?,?)",
                         (inst["id"], inst["name"], inst["game"], cfg, now, now))
    return inst


def delete_instance(iid: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM instances WHERE id=?", (iid,))


def _row_to_instance(row: sqlite3.Row) -> dict[str, Any]:
    data = json.loads(row["cfg"])
    data["id"] = row["id"]
    data["name"] = row["name"]
    data["game"] = row["game"]
    data["created"] = row["created"]
    data["updated"] = row["updated"]
    return data


# --- settings ------------------------------------------------------------------

def get_setting(key: str, default: str | None = None) -> str | None:
    with connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with connect() as conn:
        conn.execute("INSERT INTO settings (key,value) VALUES (?,?) "
                     "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


# --- events (panel activity log) ----------------------------------------------

def log_event(kind: str, text: str, ref: str | None = None) -> None:
    with connect() as conn:
        conn.execute("INSERT INTO events (ts,kind,ref,text) VALUES (?,?,?,?)",
                     (int(time.time()), kind, ref, text))
        conn.execute("DELETE FROM events WHERE id NOT IN "
                     "(SELECT id FROM events ORDER BY id DESC LIMIT 500)")


def list_events(limit: int = 100) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]
