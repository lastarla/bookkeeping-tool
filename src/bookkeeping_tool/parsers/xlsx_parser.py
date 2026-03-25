from __future__ import annotations

import math
from datetime import date, datetime
from decimal import Decimal

import pandas as pd

from bookkeeping_tool.models import RawRow


SCALAR_TYPES = (str, int, float, bool, type(None))


def _to_json_safe(value):
    if isinstance(value, SCALAR_TYPES):
        if isinstance(value, float) and math.isnan(value):
            return None
        return value
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if pd.isna(value):
        return None
    return str(value)


def parse_xlsx_rows(file_path: str) -> list[RawRow]:
    xls = pd.ExcelFile(file_path)
    rows: list[RawRow] = []
    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name=sheet_name)
        for idx, record in enumerate(df.to_dict(orient="records"), start=1):
            rows.append(
                RawRow(
                    row_number=idx,
                    raw_data={key: _to_json_safe(value) for key, value in record.items()},
                    sheet_name=sheet_name,
                )
            )
    return rows
