from __future__ import annotations

from contextlib import closing

import typer

from bookkeeping_tool.cli.common import fail, open_connection, print_output, resolve_project_root
from bookkeeping_tool.services.dashboard_service import (
    get_category_breakdown,
    get_monthly_trend,
    get_overview,
    get_yearly_trend,
    resolve_date_range,
)

summary_app = typer.Typer(help="汇总与概览命令")


def register(app: typer.Typer) -> None:
    app.add_typer(summary_app, name="summary")


@summary_app.command("overview")
def summary_overview(
    view: str = typer.Option(..., "--view", help="monthly 或 yearly"),
    month: str | None = typer.Option(None, "--month", help="月份，格式 YYYY-MM"),
    year: str | None = typer.Option(None, "--year", help="年份，格式 YYYY"),
    owner: str | None = typer.Option(None, "--owner", help="owner 过滤"),
    platform: str | None = typer.Option(None, "--platform", help="platform 过滤"),
    direction: str = typer.Option("all", "--direction", help="all / income / expense"),
    include_neutral: bool = typer.Option(False, "--include-neutral/--exclude-neutral", help="是否计入不计收支"),
    project_root: str | None = typer.Option(None, "--project-root", help="运行数据根目录，默认使用环境变量或当前目录"),
    db: str | None = typer.Option(None, "--db", help="SQLite 数据库文件路径"),
    as_json: bool = typer.Option(False, "--json", help="输出 JSON"),
) -> None:
    resolved_project_root = resolve_project_root(project_root)
    try:
        start_date, end_date = resolve_date_range(view=view, month=month, year=year)
        with closing(open_connection(resolved_project_root, db)) as connection:
            result = get_overview(
                connection,
                start_date=start_date,
                end_date=end_date,
                owner=owner,
                platform=platform,
                direction=direction,
                include_neutral=include_neutral,
            )
    except Exception as exc:
        fail(f"汇总失败：{exc}")

    print_output(result, as_json=as_json)


@summary_app.command("trend")
def summary_trend(
    view: str = typer.Option(..., "--view", help="monthly 或 yearly"),
    year: str = typer.Option(..., "--year", help="年份，格式 YYYY"),
    owner: str | None = typer.Option(None, "--owner", help="owner 过滤"),
    platform: str | None = typer.Option(None, "--platform", help="platform 过滤"),
    include_neutral: bool = typer.Option(False, "--include-neutral/--exclude-neutral", help="是否计入不计收支"),
    year_count: int = typer.Option(5, "--year-count", min=1, help="yearly 模式返回的年份数量"),
    project_root: str | None = typer.Option(None, "--project-root", help="运行数据根目录，默认使用环境变量或当前目录"),
    db: str | None = typer.Option(None, "--db", help="SQLite 数据库文件路径"),
    as_json: bool = typer.Option(False, "--json", help="输出 JSON"),
) -> None:
    resolved_project_root = resolve_project_root(project_root)
    try:
        with closing(open_connection(resolved_project_root, db)) as connection:
            result = (
                get_monthly_trend(
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
    except Exception as exc:
        fail(f"趋势汇总失败：{exc}")

    print_output(result, as_json=as_json)


@summary_app.command("category")
def summary_category(
    view: str = typer.Option(..., "--view", help="monthly 或 yearly"),
    direction: str = typer.Option(..., "--direction", help="income 或 expense"),
    month: str | None = typer.Option(None, "--month", help="月份，格式 YYYY-MM"),
    year: str | None = typer.Option(None, "--year", help="年份，格式 YYYY"),
    owner: str | None = typer.Option(None, "--owner", help="owner 过滤"),
    platform: str | None = typer.Option(None, "--platform", help="platform 过滤"),
    include_neutral: bool = typer.Option(False, "--include-neutral/--exclude-neutral", help="是否计入不计收支"),
    project_root: str | None = typer.Option(None, "--project-root", help="运行数据根目录，默认使用环境变量或当前目录"),
    db: str | None = typer.Option(None, "--db", help="SQLite 数据库文件路径"),
    as_json: bool = typer.Option(False, "--json", help="输出 JSON"),
) -> None:
    resolved_project_root = resolve_project_root(project_root)
    try:
        start_date, end_date = resolve_date_range(view=view, month=month, year=year)
        with closing(open_connection(resolved_project_root, db)) as connection:
            result = get_category_breakdown(
                connection,
                start_date=start_date,
                end_date=end_date,
                direction=direction,
                owner=owner,
                platform=platform,
                include_neutral=include_neutral,
            )
    except Exception as exc:
        fail(f"分类汇总失败：{exc}")

    print_output(result, as_json=as_json)
