from __future__ import annotations

from contextlib import closing

import typer

from bookkeeping_tool.cli.common import open_connection, print_output, resolve_project_root

inspect_app = typer.Typer(help="查看导入批次与重复导入情况")


def register(app: typer.Typer) -> None:
    app.add_typer(inspect_app, name="inspect")


@inspect_app.command("batches")
def inspect_batches(
    limit: int = typer.Option(20, "--limit", min=1, help="返回批次数量"),
    project_root: str | None = typer.Option(None, "--project-root", help="运行数据根目录，默认使用环境变量或当前目录"),
    db: str | None = typer.Option(None, "--db", help="SQLite 数据库文件路径"),
    as_json: bool = typer.Option(False, "--json", help="输出 JSON"),
) -> None:
    resolved_project_root = resolve_project_root(project_root)
    with closing(open_connection(resolved_project_root, db)) as connection:
        rows = connection.execute(
            """
            SELECT id, file_name, owner, platform, source_type, status, total_rows, imported_rows, skipped_rows, imported_at
            FROM import_batches
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        result = [dict(row) for row in rows]

    print_output(result, as_json=as_json)


@inspect_app.command("duplicates")
def inspect_duplicates(
    project_root: str | None = typer.Option(None, "--project-root", help="运行数据根目录，默认使用环境变量或当前目录"),
    db: str | None = typer.Option(None, "--db", help="SQLite 数据库文件路径"),
    as_json: bool = typer.Option(False, "--json", help="输出 JSON"),
) -> None:
    resolved_project_root = resolve_project_root(project_root)
    with closing(open_connection(resolved_project_root, db)) as connection:
        rows = connection.execute(
            """
            SELECT file_hash, COUNT(*) AS duplicate_count, GROUP_CONCAT(file_name, ', ') AS file_names
            FROM import_batches
            GROUP BY file_hash
            HAVING COUNT(*) > 1
            ORDER BY duplicate_count DESC, file_hash ASC
            """
        ).fetchall()
        result = [dict(row) for row in rows]

    print_output(result, as_json=as_json)
