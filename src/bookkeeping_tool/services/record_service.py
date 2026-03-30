from __future__ import annotations

from bookkeeping_tool.categories import normalize_category
from bookkeeping_tool.models import TransactionRecord
from bookkeeping_tool.normalizers.transaction import normalize_direction, parse_amount, parse_trade_date_to_ymd
from bookkeeping_tool.repositories.import_batches import build_manual_batch_hash, create_batch
from bookkeeping_tool.repositories.transactions import create_transaction
from bookkeeping_tool.services.budget_service import list_budget_reminders, list_budget_statuses
from bookkeeping_tool.services.time_service import utc_now_iso


MANUAL_SOURCE_TYPE = "manual"
MANUAL_SOURCE_FILE = "manual"
MANUAL_FILE_NAME = "manual-entry"



def create_manual_transaction(
    connection,
    *,
    trade_date: str,
    amount: float | str,
    direction: str,
    owner: str,
    platform: str | None,
    category: str | None,
    transaction_type: str | None = None,
    currency: str = "CNY",
    note: str | None = None,
) -> dict:
    normalized_trade_date = parse_trade_date_to_ymd(trade_date)
    normalized_amount = parse_amount(amount)
    normalized_direction = normalize_direction(direction)
    normalized_category = normalize_category(normalized_direction, category)
    imported_at = utc_now_iso()
    batch_id = create_batch(
        connection,
        source_file=MANUAL_SOURCE_FILE,
        file_name=MANUAL_FILE_NAME,
        file_hash=build_manual_batch_hash(
            trade_date=normalized_trade_date,
            direction=normalized_direction,
            amount=normalized_amount,
            owner=owner,
            platform=platform,
            note=note,
        ),
        source_type=MANUAL_SOURCE_TYPE,
        owner=owner,
        platform=platform,
        imported_at=imported_at,
        status="success",
    )
    record = TransactionRecord(
        trade_date=normalized_trade_date,
        amount=normalized_amount,
        direction=normalized_direction,
        owner=owner,
        platform=platform,
        source_type=MANUAL_SOURCE_TYPE,
        source_file=MANUAL_SOURCE_FILE,
        category=normalized_category,
        transaction_type=(transaction_type.strip() if transaction_type else None),
        currency=currency,
        note=(note.strip() if note else None),
    )
    transaction_id = create_transaction(
        connection,
        batch_id=batch_id,
        raw_row_id=None,
        record=record,
        created_at=imported_at,
    )
    connection.commit()

    result = {
        "id": transaction_id,
        "batch_id": batch_id,
        "trade_date": normalized_trade_date,
        "amount": normalized_amount,
        "direction": normalized_direction,
        "owner": owner,
        "platform": platform,
        "category": normalized_category,
        "transaction_type": record.transaction_type,
        "currency": currency,
        "note": record.note,
        "source_type": MANUAL_SOURCE_TYPE,
        "source_file": MANUAL_SOURCE_FILE,
        "created_at": imported_at,
    }
    if normalized_direction == "expense":
        budget_checks = list_budget_statuses(
            connection,
            trade_date=normalized_trade_date,
            owner=owner,
            platform=platform,
        )
        result["budget_checks"] = budget_checks
        result["reminders"] = list_budget_reminders(
            connection,
            trade_date=normalized_trade_date,
            owner=owner,
            platform=platform,
        )
    else:
        result["budget_checks"] = []
        result["reminders"] = []
    return result
