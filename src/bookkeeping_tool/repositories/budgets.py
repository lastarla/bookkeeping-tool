from __future__ import annotations

import sqlite3


def upsert_budget(
    connection: sqlite3.Connection,
    *,
    scope: str,
    period_key: str,
    amount: float,
    currency: str,
    owner: str | None,
    platform: str | None,
    created_at: str,
    updated_at: str,
) -> int:
    existing = get_budget(connection, scope=scope, period_key=period_key, owner=owner, platform=platform)
    if existing is None:
        cursor = connection.execute(
            """
            INSERT INTO budgets (scope, period_key, amount, currency, owner, platform, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (scope, period_key, amount, currency, owner, platform, created_at, updated_at),
        )
        return int(cursor.lastrowid)

    connection.execute(
        """
        UPDATE budgets
        SET amount = ?, currency = ?, updated_at = ?
        WHERE id = ?
        """,
        (amount, currency, updated_at, int(existing["id"])),
    )
    return int(existing["id"])



def get_budget(
    connection: sqlite3.Connection,
    *,
    scope: str,
    period_key: str,
    owner: str | None,
    platform: str | None,
):
    return connection.execute(
        """
        SELECT * FROM budgets
        WHERE scope = ?
          AND period_key = ?
          AND owner IS ?
          AND platform IS ?
        """,
        (scope, period_key, owner, platform),
    ).fetchone()
