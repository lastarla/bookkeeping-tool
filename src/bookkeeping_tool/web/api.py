from __future__ import annotations

from pathlib import Path
from contextlib import closing
import tempfile

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from bookkeeping_tool.db import connect, get_default_db_path, init_db
from bookkeeping_tool.services.dashboard_service import (
    build_drilldown_filters,
    get_category_breakdown,
    get_default_period,
    get_monthly_trend,
    get_overview,
    get_yearly_trend,
    resolve_date_range,
)
from bookkeeping_tool.services.query_service import query_transactions


class RecordPayload(BaseModel):
    trade_date: str
    amount: float
    direction: str
    owner: str
    platform: str | None = None
    category: str | None = None
    transaction_type: str | None = None
    currency: str = "CNY"
    note: str | None = None


class BudgetPayload(BaseModel):
    scope: str
    period_key: str
    amount: float
    owner: str | None = None
    platform: str | None = None
    currency: str = "CNY"


def list_owners(connection) -> list[str]:
    rows = connection.execute(
        """
        SELECT DISTINCT owner
        FROM transactions
        WHERE owner IS NOT NULL AND owner != ''
        ORDER BY owner ASC
        """
    ).fetchall()
    return [str(row[0]) for row in rows]


def list_platforms(connection) -> list[str]:
    rows = connection.execute(
        """
        SELECT DISTINCT platform
        FROM transactions
        WHERE platform IS NOT NULL AND platform != ''
        ORDER BY platform ASC
        """
    ).fetchall()
    return [str(row[0]) for row in rows]


def create_api_router(project_root: Path) -> APIRouter:
    router = APIRouter(prefix="/api")
    project_root = Path(project_root)

    def with_connection(handler):
        with closing(connect(get_default_db_path(project_root))) as connection:
            init_db(connection)
            return handler(connection)

    @router.get("/meta/default-period")
    def default_period() -> dict[str, str]:
        return get_default_period()

    @router.get("/meta/owners")
    def owners() -> list[str]:
        return with_connection(list_owners)

    @router.get("/meta/platforms")
    def platforms() -> list[str]:
        return with_connection(list_platforms)

    @router.get("/dashboard/overview")
    def dashboard_overview(
        view: str = Query(..., pattern="^(monthly|yearly)$"),
        month: str | None = None,
        year: str | None = None,
        direction: str = Query("all", pattern="^(all|income|expense)$"),
        owner: str | None = None,
        platform: str | None = None,
        include_neutral: bool = False,
    ) -> dict:
        start_date, end_date = resolve_date_range(view=view, month=month, year=year)
        return with_connection(
            lambda connection: get_overview(
                connection,
                start_date=start_date,
                end_date=end_date,
                owner=owner,
                platform=platform,
                direction=direction,
                include_neutral=include_neutral,
            )
        )

    @router.get("/dashboard/category-breakdown")
    def dashboard_category_breakdown(
        view: str = Query(..., pattern="^(monthly|yearly)$"),
        month: str | None = None,
        year: str | None = None,
        direction: str = Query(..., pattern="^(income|expense)$"),
        owner: str | None = None,
        platform: str | None = None,
        include_neutral: bool = False,
    ) -> dict:
        start_date, end_date = resolve_date_range(view=view, month=month, year=year)
        return with_connection(
            lambda connection: get_category_breakdown(
                connection,
                start_date=start_date,
                end_date=end_date,
                direction=direction,
                owner=owner,
                platform=platform,
                include_neutral=include_neutral,
            )
        )

    @router.get("/dashboard/trend")
    def dashboard_trend(
        view: str = Query(..., pattern="^(monthly|yearly)$"),
        year: str = Query(...),
        owner: str | None = None,
        platform: str | None = None,
        include_neutral: bool = False,
        year_count: int = 5,
    ) -> dict:
        return with_connection(
            lambda connection: get_monthly_trend(
                connection,
                year=year,
                owner=owner,
                platform=platform,
                include_neutral=include_neutral,
            )
            if view == "monthly"
            else get_yearly_trend(
                connection,
                end_year=year,
                year_count=year_count,
                owner=owner,
                platform=platform,
                include_neutral=include_neutral,
            )
        )

    @router.get("/dashboard/drilldown")
    def dashboard_drilldown(
        source: str = Query(..., pattern="^(category|trend)$"),
        view: str = Query(..., pattern="^(monthly|yearly)$"),
        month: str | None = None,
        year: str | None = None,
        direction: str | None = Query(None, pattern="^(income|expense)$"),
        category: str | None = None,
        point_key: str | None = None,
        owner: str | None = None,
        platform: str | None = None,
        include_neutral: bool = False,
        limit: int = 100,
    ) -> list[dict]:
        filters = build_drilldown_filters(
            source=source,
            view=view,
            direction=direction,
            category=category,
            point_key=point_key,
            month=month,
            year=year,
        )
        return with_connection(
            lambda connection: query_transactions(
                connection,
                start_date=filters["start_date"],
                end_date=filters["end_date"],
                owner=owner,
                platform=platform,
                direction=filters.get("direction"),
                category=filters.get("category"),
                include_neutral=include_neutral,
                limit=limit,
            )
        )

    @router.get("/transactions")
    def transactions(
        start_date: str | None = None,
        end_date: str | None = None,
        owner: str | None = None,
        platform: str | None = None,
        direction: str | None = Query(None, pattern="^(income|expense|neutral)$"),
        category: str | None = None,
        include_neutral: bool = False,
        limit: int = 100,
    ) -> list[dict]:
        return with_connection(
            lambda connection: query_transactions(
                connection,
                start_date=start_date,
                end_date=end_date,
                owner=owner,
                platform=platform,
                direction=direction,
                category=category,
                include_neutral=include_neutral,
                limit=limit,
            )
        )

    @router.post("/record")
    def create_record(payload: RecordPayload) -> dict:
        from bookkeeping_tool.services.record_service import create_manual_transaction

        try:
            return with_connection(
                lambda connection: create_manual_transaction(
                    connection,
                    trade_date=payload.trade_date,
                    amount=payload.amount,
                    direction=payload.direction,
                    owner=payload.owner,
                    platform=payload.platform,
                    category=payload.category,
                    transaction_type=payload.transaction_type,
                    currency=payload.currency,
                    note=payload.note,
                )
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/budget")
    def save_budget(payload: BudgetPayload) -> dict:
        from bookkeeping_tool.services.budget_service import set_budget

        try:
            return with_connection(
                lambda connection: set_budget(
                    connection,
                    scope=payload.scope,
                    period_key=payload.period_key,
                    amount=payload.amount,
                    owner=payload.owner,
                    platform=payload.platform,
                    currency=payload.currency,
                )
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/budget/check")
    def check_budget(
        scope: str = Query(..., pattern="^(day|month|year)$"),
        trade_date: str = Query(...),
        owner: str | None = None,
        platform: str | None = None,
    ) -> dict:
        from bookkeeping_tool.services.budget_service import get_budget_status

        try:
            return with_connection(
                lambda connection: get_budget_status(
                    connection,
                    scope=scope,
                    trade_date=trade_date,
                    owner=owner,
                    platform=platform,
                )
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/import")
    async def import_bill(file: UploadFile = File(...)) -> dict:
        from bookkeeping_tool.services.import_service import import_transactions

        suffix = Path(file.filename or "upload").suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(await file.read())
            temp_path = Path(temp_file.name)
        try:
            return import_transactions(project_root=project_root, file_path=temp_path, original_file_name=file.filename)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            temp_path.unlink(missing_ok=True)

    return router
