from __future__ import annotations

import json
import sqlite3

from bookkeeping_tool.models import RawRow


def create_raw_row(connection: sqlite3.Connection, batch_id: int, raw_row: RawRow) -> int:
    cursor = connection.execute(
        """
        INSERT INTO raw_rows (batch_id, sheet_name, row_number, raw_json)
        VALUES (?, ?, ?, ?)
        """,
        (batch_id, raw_row.sheet_name, raw_row.row_number, json.dumps(raw_row.raw_data, ensure_ascii=False)),
    )
    return int(cursor.lastrowid)
