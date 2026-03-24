from __future__ import annotations

import sqlite3
from typing import Any


ALLOWED_GROUP_BY = {
    "month": "substr(trade_date, 1, 7)",
    "category": "coalesce(category, '')",
    "owner": "owner",
    "platform": "platform",
    "direction": "direction",
}


def summarize_transactions(
    connection: sqlite3.Connection,
    *,
    group_by: str,
    start_date: str | None = None,
    end_date: str | None = None,
    owner: str | None = None,
    platform: str | None = None,
    include_neutral: bool = False,
) -> list[dict[str, Any]]:
    group_expr = ALLOWED_GROUP_BY.get(group_by)
    if not group_expr:
        raise ValueError(f"Unsupported group_by: {group_by}")

    sql = f"SELECT {group_expr} AS group_key, COUNT(*) AS transaction_count, ROUND(SUM(amount), 2) AS total_amount FROM transactions WHERE 1=1"
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
    if not include_neutral:
        sql += " AND direction != ?"
        params.append("neutral")

    sql += " GROUP BY group_key ORDER BY total_amount DESC, group_key ASC"
    rows = connection.execute(sql, params).fetchall()
    return [dict(row) for row in rows]
