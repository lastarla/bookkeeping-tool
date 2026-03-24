from __future__ import annotations

import sqlite3


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
