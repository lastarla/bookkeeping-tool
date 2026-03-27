from __future__ import annotations

from contextlib import closing

import typer

from bookkeeping_tool.cli.common import fail, open_connection, print_output, resolve_project_root

budget_app = typer.Typer(help="设置与查询预算")


@budget_app.command("set")
def budget_set(
    scope: str = typer.Option(..., "--scope", help="day / month / year"),
    period: str = typer.Option(..., "--period", help="day=YYYY-MM-DD, month=YYYY-MM, year=YYYY"),
    amount: float = typer.Option(..., "--amount", help="预算金额"),
    owner: str | None = typer.Option(None, "--owner", help="owner"),
    platform: str | None = typer.Option(None, "--platform", help="platform"),
    currency: str = typer.Option("CNY", "--currency", help="币种"),
    project_root: str | None = typer.Option(None, "--project-root", help="运行数据根目录，默认使用环境变量或当前目录"),
    db: str | None = typer.Option(None, "--db", help="SQLite 数据库文件路径"),
    as_json: bool = typer.Option(False, "--json", help="输出 JSON"),
) -> None:
    if scope not in {"day", "month", "year"}:
        fail("scope 必须是 day / month / year", exit_code=2)

    resolved_project_root = resolve_project_root(project_root)
    try:
        with closing(open_connection(resolved_project_root, db)) as connection:
            from bookkeeping_tool.services.budget_service import set_budget

            result = set_budget(
                connection,
                scope=scope,
                period_key=period,
                amount=amount,
                owner=owner,
                platform=platform,
                currency=currency,
            )
    except Exception as exc:
        fail(f"设置预算失败：{exc}")

    print_output(result, as_json=as_json)


@budget_app.command("check")
def budget_check(
    scope: str = typer.Option(..., "--scope", help="day / month / year"),
    trade_date: str = typer.Option(..., "--trade-date", help="交易日期，格式 YYYY-MM-DD"),
    owner: str | None = typer.Option(None, "--owner", help="owner"),
    platform: str | None = typer.Option(None, "--platform", help="platform"),
    project_root: str | None = typer.Option(None, "--project-root", help="运行数据根目录，默认使用环境变量或当前目录"),
    db: str | None = typer.Option(None, "--db", help="SQLite 数据库文件路径"),
    as_json: bool = typer.Option(False, "--json", help="输出 JSON"),
) -> None:
    if scope not in {"day", "month", "year"}:
        fail("scope 必须是 day / month / year", exit_code=2)

    resolved_project_root = resolve_project_root(project_root)
    try:
        with closing(open_connection(resolved_project_root, db)) as connection:
            from bookkeeping_tool.services.budget_service import get_budget_status

            result = get_budget_status(
                connection,
                scope=scope,
                trade_date=trade_date,
                owner=owner,
                platform=platform,
            )
    except Exception as exc:
        fail(f"预算检查失败：{exc}")

    print_output(result, as_json=as_json)


def register(app: typer.Typer) -> None:
    app.add_typer(budget_app, name="budget")
