from __future__ import annotations

from pathlib import Path
import sqlite3


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS import_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_hash TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL,
    owner TEXT NOT NULL,
    platform TEXT,
    imported_at TEXT NOT NULL,
    status TEXT NOT NULL,
    total_rows INTEGER NOT NULL DEFAULT 0,
    imported_rows INTEGER NOT NULL DEFAULT 0,
    skipped_rows INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS raw_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL,
    sheet_name TEXT,
    row_number INTEGER NOT NULL,
    raw_json TEXT NOT NULL,
    FOREIGN KEY(batch_id) REFERENCES import_batches(id)
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL,
    raw_row_id INTEGER,
    trade_date TEXT NOT NULL,
    amount REAL NOT NULL,
    direction TEXT NOT NULL,
    category TEXT,
    transaction_type TEXT,
    owner TEXT NOT NULL,
    platform TEXT,
    source_type TEXT NOT NULL,
    source_file TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'CNY',
    note TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(batch_id) REFERENCES import_batches(id),
    FOREIGN KEY(raw_row_id) REFERENCES raw_rows(id)
);
"""


def get_default_db_path(project_root: Path) -> Path:
    return project_root / "data" / "bookkeeping.db"


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)
    connection.commit()
