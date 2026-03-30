from __future__ import annotations

import hashlib
import sqlite3
import uuid


def get_batch_by_hash(connection: sqlite3.Connection, file_hash: str):
    return connection.execute(
        "SELECT * FROM import_batches WHERE file_hash = ?",
        (file_hash,),
    ).fetchone()


def create_batch(
    connection: sqlite3.Connection,
    *,
    source_file: str,
    file_name: str,
    file_hash: str,
    source_type: str,
    owner: str,
    platform: str,
    imported_at: str,
    status: str,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO import_batches (
            source_file, file_name, file_hash, source_type,
            owner, platform, imported_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (source_file, file_name, file_hash, source_type, owner, platform, imported_at, status),
    )
    return int(cursor.lastrowid)


def update_batch_stats(
    connection: sqlite3.Connection,
    batch_id: int,
    *,
    status: str,
    total_rows: int,
    imported_rows: int,
    skipped_rows: int,
) -> None:
    connection.execute(
        """
        UPDATE import_batches
        SET status = ?, total_rows = ?, imported_rows = ?, skipped_rows = ?
        WHERE id = ?
        """,
        (status, total_rows, imported_rows, skipped_rows, batch_id),
    )


def build_manual_batch_hash(*, trade_date: str, direction: str, amount: float, owner: str, platform: str | None, note: str | None) -> str:
    raw = "|".join([trade_date, direction, f"{amount:.2f}", owner, platform or "", note or "", uuid.uuid4().hex])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
