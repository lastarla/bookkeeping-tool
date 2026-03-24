from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_mapping(mapping_path: Path) -> dict[str, list[str]]:
    with mapping_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return {str(k): [str(x) for x in v] for k, v in data.items()}


def find_first_present(row: dict[str, Any], candidates: list[str]) -> Any:
    for key in candidates:
        if key in row:
            return row.get(key)
    return None


def normalize_row_fields(row: dict[str, Any], mapping: dict[str, list[str]]) -> dict[str, Any]:
    """Map source columns to internal standard fields.

    Returns a dict with keys like trade_date, amount, direction, category, transaction_type.
    Missing fields will be absent.
    """

    normalized: dict[str, Any] = {}
    for field, aliases in mapping.items():
        value = find_first_present(row, aliases)
        if value is not None:
            normalized[field] = value
    return normalized
