from __future__ import annotations

import sqlite3

from bookkeeping_tool.models import TransactionRecord


def create_transaction(
    connection: sqlite3.Connection,
    *,
    batch_id: int,
    raw_row_id: int,
    record: TransactionRecord,
    created_at: str,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO transactions (
            batch_id, raw_row_id, trade_date, amount, direction,
            category, transaction_type, owner, platform,
            source_type, source_file, currency, note, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            batch_id,
            raw_row_id,
            record.trade_date,
            record.amount,
            record.direction,
            record.category,
            record.transaction_type,
            record.owner,
            record.platform,
            record.source_type,
            record.source_file,
            record.currency,
            record.note,
            created_at,
        ),
    )
    return int(cursor.lastrowid)
