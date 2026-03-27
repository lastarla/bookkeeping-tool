from __future__ import annotations

from contextlib import closing

import typer

from bookkeeping_tool.cli.common import fail, open_connection, parse_json_input, print_output, resolve_project_root

record_app = typer.Typer(help="手工记录单笔收入/支出")


ALLOWED_DIRECTIONS = {"income", "expense"}


@record_app.command("add")
def record_add(
    trade_date: str = typer.Option(..., "--trade-date", help="交易日期，格式 YYYY-MM-DD"),
    amount: float = typer.Option(..., "--amount", help="金额"),
    direction: str = typer.Option(..., "--direction", help="income / expense"),
    owner: str = typer.Option(..., "--owner", help="owner"),
    platform: str | None = typer.Option(None, "--platform", help="platform"),
    category: str | None = typer.Option(None, "--category", help="分类"),
    transaction_type: str | None = typer.Option(None, "--transaction-type", help="交易类型"),
    currency: str = typer.Option("CNY", "--currency", help="币种"),
    note: str | None = typer.Option(None, "--note", help="备注"),
    payload: str | None = typer.Option(None, "--payload", help="JSON 结构输入"),
    project_root: str | None = typer.Option(None, "--project-root", help="运行数据根目录，默认使用环境变量或当前目录"),
    db: str | None = typer.Option(None, "--db", help="SQLite 数据库文件路径"),
    as_json: bool = typer.Option(False, "--json", help="输出 JSON"),
) -> None:
    if payload:
        try:
            payload_data = parse_json_input(payload)
            trade_date = str(payload_data.get("trade_date") or trade_date)
            amount = payload_data.get("amount", amount)
            direction = str(payload_data.get("direction") or direction)
            owner = str(payload_data.get("owner") or owner)
            platform = payload_data.get("platform", platform)
            category = payload_data.get("category", category)
            transaction_type = payload_data.get("transaction_type", transaction_type)
            currency = str(payload_data.get("currency") or currency)
            note = payload_data.get("note", note)
        except Exception as exc:
            fail(f"payload 解析失败：{exc}")

    if direction not in ALLOWED_DIRECTIONS:
        fail("direction 必须是 income 或 expense", exit_code=2)

    resolved_project_root = resolve_project_root(project_root)
    try:
        with closing(open_connection(resolved_project_root, db)) as connection:
            from bookkeeping_tool.services.record_service import create_manual_transaction

            result = create_manual_transaction(
                connection,
                trade_date=trade_date,
                amount=amount,
                direction=direction,
                owner=owner,
                platform=platform,
                category=category,
                transaction_type=transaction_type,
                currency=currency,
                note=note,
            )
    except Exception as exc:
        fail(f"记账失败：{exc}")

    print_output(result, as_json=as_json)


@record_app.command("expense")
def record_expense(
    trade_date: str = typer.Option(..., "--trade-date", help="交易日期，格式 YYYY-MM-DD"),
    amount: float = typer.Option(..., "--amount", help="金额"),
    owner: str = typer.Option(..., "--owner", help="owner"),
    platform: str | None = typer.Option(None, "--platform", help="platform"),
    category: str | None = typer.Option(None, "--category", help="分类"),
    transaction_type: str | None = typer.Option(None, "--transaction-type", help="交易类型"),
    currency: str = typer.Option("CNY", "--currency", help="币种"),
    note: str | None = typer.Option(None, "--note", help="备注"),
    payload: str | None = typer.Option(None, "--payload", help="JSON 结构输入"),
    project_root: str | None = typer.Option(None, "--project-root", help="运行数据根目录，默认使用环境变量或当前目录"),
    db: str | None = typer.Option(None, "--db", help="SQLite 数据库文件路径"),
    as_json: bool = typer.Option(False, "--json", help="输出 JSON"),
) -> None:
    record_add(
        trade_date=trade_date,
        amount=amount,
        direction="expense",
        owner=owner,
        platform=platform,
        category=category,
        transaction_type=transaction_type,
        currency=currency,
        note=note,
        payload=payload,
        project_root=project_root,
        db=db,
        as_json=as_json,
    )


@record_app.command("income")
def record_income(
    trade_date: str = typer.Option(..., "--trade-date", help="交易日期，格式 YYYY-MM-DD"),
    amount: float = typer.Option(..., "--amount", help="金额"),
    owner: str = typer.Option(..., "--owner", help="owner"),
    platform: str | None = typer.Option(None, "--platform", help="platform"),
    category: str | None = typer.Option(None, "--category", help="分类"),
    transaction_type: str | None = typer.Option(None, "--transaction-type", help="交易类型"),
    currency: str = typer.Option("CNY", "--currency", help="币种"),
    note: str | None = typer.Option(None, "--note", help="备注"),
    payload: str | None = typer.Option(None, "--payload", help="JSON 结构输入"),
    project_root: str | None = typer.Option(None, "--project-root", help="运行数据根目录，默认使用环境变量或当前目录"),
    db: str | None = typer.Option(None, "--db", help="SQLite 数据库文件路径"),
    as_json: bool = typer.Option(False, "--json", help="输出 JSON"),
) -> None:
    record_add(
        trade_date=trade_date,
        amount=amount,
        direction="income",
        owner=owner,
        platform=platform,
        category=category,
        transaction_type=transaction_type,
        currency=currency,
        note=note,
        payload=payload,
        project_root=project_root,
        db=db,
        as_json=as_json,
    )


def register(app: typer.Typer) -> None:
    app.add_typer(record_app, name="record")
