from __future__ import annotations

import sqlite3
from typing import Any


def query_transactions(
    connection: sqlite3.Connection,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    owner: str | None = None,
    platform: str | None = None,
    direction: str | None = None,
    category: str | None = None,
    include_neutral: bool = True,
    limit: int = 100,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM transactions WHERE 1=1"
    params: list[Any] = []

    if start_date:
        sql += " AND trade_date >= ?"
        params.append(start_date)
    if end_date:
        sql += " AND trade_date <= ?"
        params.append(end_date)
    if owner:
        sql += " AND owner = ?"
        params.append(owner)
    if platform:
        sql += " AND platform = ?"
        params.append(platform)
    if direction:
        if direction == 'expense' and include_neutral:
            sql += " AND direction IN (?, ?)"
            params.extend(['expense', 'neutral'])
        else:
            sql += " AND direction = ?"
            params.append(direction)
    elif not include_neutral:
        sql += " AND direction != ?"
        params.append('neutral')
    if category is not None:
        if category == '':
            sql += " AND (category IS NULL OR category = '')"
        else:
            sql += " AND category = ?"
            params.append(category)

    sql += " ORDER BY trade_date DESC, id DESC LIMIT ?"
    params.append(limit)

    rows = connection.execute(sql, params).fetchall()
    return [dict(row) for row in rows]
