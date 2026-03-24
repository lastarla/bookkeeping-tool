from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ImportTransactionsInput:
    file_path: str
    source_hint: str | None = None
    dry_run: bool = False


@dataclass(slots=True)
class QueryTransactionsInput:
    start_date: str | None = None
    end_date: str | None = None
    owner: str | None = None
    platform: str | None = None
    direction: str | None = None
    category: str | None = None
    limit: int = 100


@dataclass(slots=True)
class SummarizeTransactionsInput:
    group_by: str = "month"
    start_date: str | None = None
    end_date: str | None = None
    owner: str | None = None
    platform: str | None = None
    include_neutral: bool = False
