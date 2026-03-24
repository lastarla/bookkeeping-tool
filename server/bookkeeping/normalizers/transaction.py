from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from server.bookkeeping.models import DIRECTION_MAP


def parse_trade_date_to_ymd(value: Any) -> str:
    # pandas handles strings, datetime, and Excel serials well.
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        raise ValueError(f"Cannot parse trade date: {value!r}")
    if isinstance(dt, pd.Series):
        raise ValueError("trade date should be scalar")
    # ensure python datetime-like
    if hasattr(dt, "to_pydatetime"):
        dt = dt.to_pydatetime()
    if not isinstance(dt, datetime):
        dt = datetime.fromisoformat(str(dt))
    return dt.date().isoformat()


def parse_amount(value: Any) -> float:
    if value is None:
        raise ValueError("amount is required")
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    s = s.replace(",", "")
    if s == "":
        raise ValueError("amount is empty")
    return float(s)


def normalize_direction(value: Any) -> str:
    if value is None:
        raise ValueError("direction is required")
    s = str(value).strip()
    mapped = DIRECTION_MAP.get(s)
    if mapped:
        return mapped
    # fallback: accept already-normalized values
    if s in {"income", "expense", "neutral"}:
        return s
    raise ValueError(f"Unknown direction: {value!r}")
