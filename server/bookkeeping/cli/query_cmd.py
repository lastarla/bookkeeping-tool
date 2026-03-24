from __future__ import annotations

from contextlib import closing

import typer

from server.bookkeeping.cli.common import fail, open_connection, print_output, resolve_project_root
from server.bookkeeping.services.query_service import query_transactions


def register(app: typer.Typer) -> None:
    @app.command("query")
    def query_command(
        start_date: str | None = typer.Option(None, "--start-date", help="开始日期，格式 YYYY-MM-DD"),
        end_date: str | None = typer.Option(None, "--end-date", help="结束日期，格式 YYYY-MM-DD"),
        owner: str | None = typer.Option(None, "--owner", help="owner 过滤"),
        platform: str | None = typer.Option(None, "--platform", help="platform 过滤"),
        direction: str | None = typer.Option(None, "--direction", help="income / expense / neutral"),
        category: str | None = typer.Option(None, "--category", help="分类过滤；空字符串表示未分类"),
        include_neutral: bool = typer.Option(True, "--include-neutral/--exclude-neutral", help="是否包含不计收支"),
        limit: int = typer.Option(100, "--limit", min=1, help="返回条数上限"),
        project_root: str | None = typer.Option(None, "--project-root", help="项目根目录，默认自动推导"),
        db: str | None = typer.Option(None, "--db", help="SQLite 数据库文件路径"),
        as_json: bool = typer.Option(False, "--json", help="输出 JSON"),
    ) -> None:
        resolved_project_root = resolve_project_root(project_root)
        try:
            with closing(open_connection(resolved_project_root, db)) as connection:
                rows = query_transactions(
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
        except Exception as exc:
            fail(f"查询失败：{exc}")

        print_output(rows, as_json=as_json)
