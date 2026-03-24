from __future__ import annotations

from pathlib import Path
from typing import Any

from server.bookkeeping.db import connect, get_default_db_path
from server.bookkeeping.services.import_service import import_transactions
from server.bookkeeping.services.query_service import query_transactions
from server.bookkeeping.services.summary_service import summarize_transactions
from server.bookkeeping.skill.schema import ImportTransactionsInput, QueryTransactionsInput, SummarizeTransactionsInput


def handle_import_transactions(project_root: str | Path, payload: ImportTransactionsInput) -> dict[str, Any]:
    if payload.dry_run:
        return {
            "status": "dry_run",
            "file_path": payload.file_path,
        }
    return import_transactions(project_root=project_root, file_path=payload.file_path)


def handle_query_transactions(project_root: str | Path, payload: QueryTransactionsInput) -> list[dict[str, Any]]:
    project_root = Path(project_root)
    connection = connect(get_default_db_path(project_root))
    return query_transactions(
        connection,
        start_date=payload.start_date,
        end_date=payload.end_date,
        owner=payload.owner,
        platform=payload.platform,
        direction=payload.direction,
        category=payload.category,
        limit=payload.limit,
    )


def handle_summarize_transactions(project_root: str | Path, payload: SummarizeTransactionsInput) -> list[dict[str, Any]]:
    project_root = Path(project_root)
    connection = connect(get_default_db_path(project_root))
    return summarize_transactions(
        connection,
        group_by=payload.group_by,
        start_date=payload.start_date,
        end_date=payload.end_date,
        owner=payload.owner,
        platform=payload.platform,
        include_neutral=payload.include_neutral,
    )
