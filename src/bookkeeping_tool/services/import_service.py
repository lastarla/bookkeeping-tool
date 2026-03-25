from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bookkeeping_tool.db import connect, get_default_db_path, init_db
from bookkeeping_tool.models import TransactionRecord
from bookkeeping_tool.normalizers.field_mapping import load_mapping_for_source, normalize_row_fields
from bookkeeping_tool.normalizers.transaction import normalize_direction, parse_amount, parse_trade_date_to_ymd
from bookkeeping_tool.parsers.csv_parser import parse_csv_rows
from bookkeeping_tool.parsers.filename_meta import parse_file_meta
from bookkeeping_tool.parsers.xlsx_parser import parse_xlsx_rows
from bookkeeping_tool.repositories.import_batches import create_batch, get_batch_by_hash, update_batch_stats
from bookkeeping_tool.repositories.raw_rows import create_raw_row
from bookkeeping_tool.repositories.transactions import create_transaction
from bookkeeping_tool.services.file_hash import sha256_file


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def import_transactions(
    *,
    project_root: str | Path,
    file_path: str | Path,
    db_path: str | Path | None = None,
    original_file_name: str | None = None,
    mapping_dir: str | Path | None = None,
) -> dict[str, Any]:
    project_root = Path(project_root)
    effective_file_path = Path(file_path)
    if original_file_name:
        effective_file_path = effective_file_path.with_name(original_file_name)
    file_meta = parse_file_meta(effective_file_path)
    file_meta.source_file = str(file_path)

    mapping = load_mapping_for_source(file_meta.source_type, mapping_dir)

    file_hash = sha256_file(file_meta.source_file)

    db_path = Path(db_path) if db_path else get_default_db_path(project_root)
    connection = connect(db_path)
    init_db(connection)

    existing = get_batch_by_hash(connection, file_hash)
    if existing is not None:
        return {
            "status": "duplicate",
            "batch_id": int(existing["id"]),
            "file_name": existing["file_name"],
            "owner": existing["owner"],
            "platform": existing["platform"],
        }

    imported_at = utc_now_iso()
    batch_id = create_batch(
        connection,
        source_file=file_meta.source_file,
        file_name=file_meta.file_name,
        file_hash=file_hash,
        source_type=file_meta.source_type,
        owner=file_meta.owner,
        platform=file_meta.platform,
        imported_at=imported_at,
        status="partial",
    )

    if file_meta.source_type == "csv":
        raw_rows = parse_csv_rows(file_meta.source_file)
    else:
        raw_rows = parse_xlsx_rows(file_meta.source_file)

    total_rows = 0
    imported_rows = 0
    skipped_rows = 0
    created_at = imported_at

    for raw_row in raw_rows:
        total_rows += 1
        try:
            raw_row_id = create_raw_row(connection, batch_id, raw_row)

            normalized = normalize_row_fields(raw_row.raw_data, mapping)
            trade_date = parse_trade_date_to_ymd(normalized.get("trade_date"))
            amount = parse_amount(normalized.get("amount"))
            direction = normalize_direction(normalized.get("direction"))

            record = TransactionRecord(
                trade_date=trade_date,
                amount=amount,
                direction=direction,
                category=(str(normalized.get("category")).strip() if normalized.get("category") is not None else None),
                transaction_type=(
                    str(normalized.get("transaction_type")).strip()
                    if normalized.get("transaction_type") is not None
                    else None
                ),
                owner=file_meta.owner,
                platform=file_meta.platform,
                source_type=file_meta.source_type,
                source_file=file_meta.source_file,
            )

            create_transaction(
                connection,
                batch_id=batch_id,
                raw_row_id=raw_row_id,
                record=record,
                created_at=created_at,
            )
            imported_rows += 1
        except Exception:
            skipped_rows += 1

    status = "success" if skipped_rows == 0 else ("failed" if imported_rows == 0 else "partial")
    update_batch_stats(
        connection,
        batch_id,
        status=status,
        total_rows=total_rows,
        imported_rows=imported_rows,
        skipped_rows=skipped_rows,
    )
    connection.commit()

    return {
        "status": status,
        "batch_id": batch_id,
        "file_name": file_meta.file_name,
        "owner": file_meta.owner,
        "platform": file_meta.platform,
        "total_rows": total_rows,
        "imported_rows": imported_rows,
        "skipped_rows": skipped_rows,
    }
