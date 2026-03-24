from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any


Mapping = dict[str, list[str]]


def _normalize_mapping(data: dict[str, Any]) -> Mapping:
    return {str(k): [str(x) for x in v] for k, v in data.items()}


def load_mapping(mapping_path: Path) -> Mapping:
    with mapping_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return _normalize_mapping(data)


def load_default_mapping(source_type: str) -> Mapping:
    resource_name = f"{source_type}.json"
    with resources.files("server.configs.mappings").joinpath(resource_name).open("r", encoding="utf-8") as f:
        data = json.load(f)
    return _normalize_mapping(data)


def load_mapping_for_source(source_type: str, mapping_dir: str | Path | None = None) -> Mapping:
    if mapping_dir:
        return load_mapping(Path(mapping_dir) / f"{source_type}.json")
    return load_default_mapping(source_type)


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
