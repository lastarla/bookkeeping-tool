from __future__ import annotations

from calendar import monthrange

from bookkeeping_tool.repositories.budgets import get_budget, upsert_budget
from bookkeeping_tool.services.dashboard_service import get_overview
from bookkeeping_tool.services.time_service import utc_now_iso

WARNING_THRESHOLD = 0.8
SCOPE_LABELS = {
    "day": "日",
    "month": "月",
    "year": "年",
}
STATUS_TO_SEVERITY = {
    "unset": "info",
    "normal": "info",
    "warning": "warning",
    "exceeded": "critical",
}


def build_budget_period_key(scope: str, trade_date: str) -> str:
    year, month, day = trade_date.split("-", 2)
    if scope == "year":
        return year
    if scope == "month":
        return f"{year}-{month}"
    if scope == "day":
        return trade_date
    raise ValueError("scope must be day, month, or year")



def resolve_budget_date_range(scope: str, period_key: str) -> tuple[str, str]:
    if scope == "year":
        return f"{period_key}-01-01", f"{period_key}-12-31"
    if scope == "month":
        year, month = period_key.split("-", 1)
        last_day = monthrange(int(year), int(month))[1]
        return f"{year}-{month}-01", f"{year}-{month}-{last_day:02d}"
    if scope == "day":
        return period_key, period_key
    raise ValueError("scope must be day, month, or year")



def build_budget_trade_date(scope: str, period_key: str) -> str:
    if scope == "year":
        return f"{period_key}-01-01"
    if scope == "month":
        return f"{period_key}-01"
    if scope == "day":
        return period_key
    raise ValueError("scope must be day, month, or year")



def set_budget(
    connection,
    *,
    scope: str,
    period_key: str,
    amount: float,
    owner: str | None,
    platform: str | None,
    currency: str = "CNY",
) -> dict:
    now = utc_now_iso()
    budget_id = upsert_budget(
        connection,
        scope=scope,
        period_key=period_key,
        amount=amount,
        currency=currency,
        owner=owner,
        platform=platform,
        created_at=now,
        updated_at=now,
    )
    connection.commit()
    row = get_budget(connection, scope=scope, period_key=period_key, owner=owner, platform=platform)
    result = {
        "id": budget_id,
        "scope": scope,
        "scope_label": SCOPE_LABELS[scope],
        "period_key": period_key,
        "amount": float(row["amount"]),
        "currency": row["currency"],
        "owner": row["owner"],
        "platform": row["platform"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    result["reminder"] = build_budget_reminder(
        get_budget_status(
            connection,
            scope=scope,
            trade_date=build_budget_trade_date(scope, period_key),
            owner=owner,
            platform=platform,
        )
    )
    return result



def build_budget_reminder(budget_status: dict) -> dict | None:
    status = budget_status["status"]
    if status == "normal":
        return None
    scope = budget_status["scope"]
    return {
        "type": "budget",
        "scope": scope,
        "scope_label": SCOPE_LABELS[scope],
        "status": status,
        "severity": STATUS_TO_SEVERITY[status],
        "period_key": budget_status["period_key"],
        "budget_amount": budget_status.get("budget_amount"),
        "current_expense": budget_status.get("current_expense"),
        "usage_ratio": budget_status.get("usage_ratio"),
        "currency": budget_status.get("currency", "CNY"),
        "message": budget_status["message"],
        "channel_text": budget_status["message"],
    }



def get_budget_status(connection, *, scope: str, trade_date: str, owner: str | None, platform: str | None) -> dict:
    period_key = build_budget_period_key(scope, trade_date)
    budget = get_budget(connection, scope=scope, period_key=period_key, owner=owner, platform=platform)
    if budget is None:
        return {
            "scope": scope,
            "scope_label": SCOPE_LABELS[scope],
            "period_key": period_key,
            "status": "unset",
            "severity": STATUS_TO_SEVERITY["unset"],
            "budget_amount": None,
            "current_expense": None,
            "usage_ratio": None,
            "currency": "CNY",
            "message": f"未设置{SCOPE_LABELS[scope]}预算",
        }

    start_date, end_date = resolve_budget_date_range(scope, period_key)
    overview = get_overview(
        connection,
        start_date=start_date,
        end_date=end_date,
        owner=owner,
        platform=platform,
        direction="expense",
        include_neutral=False,
    )
    budget_amount = float(budget["amount"])
    current_expense = float(overview["total_expense"])
    usage_ratio = 0.0 if budget_amount <= 0 else round(current_expense / budget_amount, 4)

    scope_label = SCOPE_LABELS[scope]
    status = "normal"
    message = f"{scope_label}预算使用正常"
    if usage_ratio >= 1:
        status = "exceeded"
        message = f"{scope_label}预算已超限"
    elif usage_ratio >= WARNING_THRESHOLD:
        status = "warning"
        message = f"{scope_label}预算已达到80%"

    return {
        "scope": scope,
        "scope_label": SCOPE_LABELS[scope],
        "period_key": period_key,
        "status": status,
        "severity": STATUS_TO_SEVERITY[status],
        "budget_amount": budget_amount,
        "current_expense": round(current_expense, 2),
        "usage_ratio": usage_ratio,
        "currency": budget["currency"],
        "owner": budget["owner"],
        "platform": budget["platform"],
        "message": message,
    }



def list_budget_statuses(connection, *, trade_date: str, owner: str | None, platform: str | None) -> list[dict]:
    return [
        get_budget_status(connection, scope=scope, trade_date=trade_date, owner=owner, platform=platform)
        for scope in ("day", "month", "year")
    ]



def list_budget_reminders(connection, *, trade_date: str, owner: str | None, platform: str | None) -> list[dict]:
    reminders: list[dict] = []
    for status in list_budget_statuses(connection, trade_date=trade_date, owner=owner, platform=platform):
        reminder = build_budget_reminder(status)
        if reminder is not None:
            reminders.append(reminder)
    return reminders
