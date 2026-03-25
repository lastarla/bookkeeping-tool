from __future__ import annotations

import sqlite3
from calendar import monthrange
from datetime import date
from typing import Any


def _apply_common_filters(
    sql: str,
    params: list[Any],
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    owner: str | None = None,
    platform: str | None = None,
    direction: str | None = None,
    category: str | None = None,
    include_neutral: bool = True,
) -> tuple[str, list[Any]]:
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
    if direction and direction != "all":
        if direction == "expense" and include_neutral:
            sql += " AND direction IN (?, ?)"
            params.extend(["expense", "neutral"])
        else:
            sql += " AND direction = ?"
            params.append(direction)
    if category:
        sql += " AND category = ?"
        params.append(category)
    if not include_neutral and direction in (None, "all"):
        sql += " AND direction != ?"
        params.append("neutral")
    return sql, params


def resolve_date_range(*, view: str, month: str | None = None, year: str | None = None) -> tuple[str, str]:
    if view == "monthly":
        if not month:
            raise ValueError("month is required for monthly view")
        year_part, month_part = month.split("-", 1)
        year_value = int(year_part)
        month_value = int(month_part)
        last_day = monthrange(year_value, month_value)[1]
        return f"{year_value:04d}-{month_value:02d}-01", f"{year_value:04d}-{month_value:02d}-{last_day:02d}"

    if view == "yearly":
        if not year:
            raise ValueError("year is required for yearly view")
        year_value = int(year)
        return f"{year_value:04d}-01-01", f"{year_value:04d}-12-31"

    raise ValueError(f"Unsupported view: {view}")


def get_overview(
    connection: sqlite3.Connection,
    *,
    start_date: str,
    end_date: str,
    owner: str | None = None,
    platform: str | None = None,
    direction: str | None = None,
    include_neutral: bool = False,
) -> dict[str, Any]:
    expense_directions = ("expense", "neutral") if include_neutral else ("expense",)
    expense_condition = ", ".join(f"'{direction_value}'" for direction_value in expense_directions)
    sql = f"""
    SELECT
        ROUND(SUM(CASE WHEN direction = 'income' THEN amount ELSE 0 END), 2) AS total_income,
        ROUND(SUM(CASE WHEN direction IN ({expense_condition}) THEN amount ELSE 0 END), 2) AS total_expense,
        COUNT(*) AS transaction_count
    FROM transactions
    WHERE 1=1
    """
    params: list[Any] = []
    sql, params = _apply_common_filters(
        sql,
        params,
        start_date=start_date,
        end_date=end_date,
        owner=owner,
        platform=platform,
        direction=direction,
        include_neutral=include_neutral,
    )
    row = connection.execute(sql, params).fetchone()
    total_income = float(row["total_income"] or 0)
    total_expense = float(row["total_expense"] or 0)
    transaction_count = int(row["transaction_count"] or 0)
    return {
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "net_amount": round(total_income - total_expense, 2),
        "transaction_count": transaction_count,
    }


def get_category_breakdown(
    connection: sqlite3.Connection,
    *,
    start_date: str,
    end_date: str,
    direction: str,
    owner: str | None = None,
    platform: str | None = None,
    include_neutral: bool = False,
) -> dict[str, Any]:
    if direction not in {"income", "expense"}:
        raise ValueError("direction must be income or expense")

    sql = """
    SELECT
        COALESCE(NULLIF(category, ''), '未分类') AS category,
        ROUND(SUM(amount), 2) AS amount,
        COUNT(*) AS count
    FROM transactions
    WHERE 1=1
    """
    params: list[Any] = []
    sql, params = _apply_common_filters(
        sql,
        params,
        start_date=start_date,
        end_date=end_date,
        owner=owner,
        platform=platform,
        direction=direction,
        include_neutral=include_neutral,
    )
    sql += " GROUP BY category ORDER BY amount DESC, category ASC"
    rows = connection.execute(sql, params).fetchall()
    return {
        "direction": direction,
        "items": [
            {
                "category": row["category"],
                "amount": float(row["amount"] or 0),
                "count": int(row["count"] or 0),
            }
            for row in rows
        ],
    }


def get_monthly_trend(
    connection: sqlite3.Connection,
    *,
    year: str,
    owner: str | None = None,
    platform: str | None = None,
    include_neutral: bool = False,
) -> dict[str, Any]:
    start_date = f"{int(year):04d}-01-01"
    end_date = f"{int(year):04d}-12-31"
    expense_directions = ("expense", "neutral") if include_neutral else ("expense",)
    expense_condition = ", ".join(f"'{direction_value}'" for direction_value in expense_directions)
    sql = f"""
    SELECT
        substr(trade_date, 1, 7) AS month,
        ROUND(SUM(CASE WHEN direction = 'income' THEN amount ELSE 0 END), 2) AS income,
        ROUND(SUM(CASE WHEN direction IN ({expense_condition}) THEN amount ELSE 0 END), 2) AS expense
    FROM transactions
    WHERE 1=1
    """
    params: list[Any] = []
    sql, params = _apply_common_filters(
        sql,
        params,
        start_date=start_date,
        end_date=end_date,
        owner=owner,
        platform=platform,
        include_neutral=include_neutral,
    )
    sql += " GROUP BY month ORDER BY month ASC"
    rows = {row["month"]: row for row in connection.execute(sql, params).fetchall()}

    labels: list[str] = []
    income: list[float] = []
    expense: list[float] = []
    for month_value in range(1, 13):
        label = f"{int(year):04d}-{month_value:02d}"
        row = rows.get(label)
        labels.append(label)
        income.append(float(row["income"] or 0) if row else 0.0)
        expense.append(float(row["expense"] or 0) if row else 0.0)

    return {
        "labels": labels,
        "income": income,
        "expense": expense,
    }


def get_yearly_trend(
    connection: sqlite3.Connection,
    *,
    end_year: str,
    year_count: int = 5,
    owner: str | None = None,
    platform: str | None = None,
    include_neutral: bool = False,
) -> dict[str, Any]:
    end_year_value = int(end_year)
    start_year_value = end_year_value - max(year_count - 1, 0)
    start_date = f"{start_year_value:04d}-01-01"
    end_date = f"{end_year_value:04d}-12-31"
    expense_directions = ("expense", "neutral") if include_neutral else ("expense",)
    expense_condition = ", ".join(f"'{direction_value}'" for direction_value in expense_directions)
    sql = f"""
    SELECT
        substr(trade_date, 1, 4) AS year,
        ROUND(SUM(CASE WHEN direction = 'income' THEN amount ELSE 0 END), 2) AS income,
        ROUND(SUM(CASE WHEN direction IN ({expense_condition}) THEN amount ELSE 0 END), 2) AS expense
    FROM transactions
    WHERE 1=1
    """
    params: list[Any] = []
    sql, params = _apply_common_filters(
        sql,
        params,
        start_date=start_date,
        end_date=end_date,
        owner=owner,
        platform=platform,
        include_neutral=include_neutral,
    )
    sql += " GROUP BY year ORDER BY year ASC"
    rows = {row["year"]: row for row in connection.execute(sql, params).fetchall()}

    labels: list[str] = []
    income: list[float] = []
    expense: list[float] = []
    for year_value in range(start_year_value, end_year_value + 1):
        label = f"{year_value:04d}"
        row = rows.get(label)
        labels.append(label)
        income.append(float(row["income"] or 0) if row else 0.0)
        expense.append(float(row["expense"] or 0) if row else 0.0)

    return {
        "labels": labels,
        "income": income,
        "expense": expense,
    }


def build_drilldown_filters(
    *,
    source: str,
    view: str,
    direction: str | None = None,
    category: str | None = None,
    point_key: str | None = None,
    month: str | None = None,
    year: str | None = None,
) -> dict[str, Any]:
    start_date, end_date = resolve_date_range(view=view, month=month, year=year)

    if source == "category":
        return {
            "start_date": start_date,
            "end_date": end_date,
            "direction": direction,
            "category": category,
        }

    if source == "trend":
        if not point_key:
            raise ValueError("point_key is required for trend drilldown")
        if view == "monthly":
            point_start, point_end = resolve_date_range(view="monthly", month=point_key)
        else:
            point_start, point_end = resolve_date_range(view="yearly", year=point_key)
        return {
            "start_date": point_start,
            "end_date": point_end,
            "direction": direction,
            "category": None,
        }

    raise ValueError(f"Unsupported drilldown source: {source}")


def get_default_period() -> dict[str, str]:
    today = date.today()
    return {
        "month": today.strftime("%Y-%m"),
        "year": today.strftime("%Y"),
    }
