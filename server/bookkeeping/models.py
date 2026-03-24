from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DIRECTION_MAP = {
    "收入": "income",
    "支出": "expense",
    "不计收支": "neutral",
}


@dataclass(slots=True)
class FileMeta:
    owner: str
    platform: str | None
    source_type: str
    source_file: str
    file_name: str


@dataclass(slots=True)
class RawRow:
    row_number: int
    raw_data: dict[str, Any]
    sheet_name: str | None = None


@dataclass(slots=True)
class TransactionRecord:
    trade_date: str
    amount: float
    direction: str
    owner: str
    platform: str | None
    source_type: str
    source_file: str
    category: str | None = None
    transaction_type: str | None = None
    currency: str = "CNY"
    note: str | None = None
