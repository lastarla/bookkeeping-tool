from __future__ import annotations

from contextlib import closing

import typer

from server.bookkeeping.cli.common import open_connection, print_output, require_confirmation, resolve_project_root


def register(app: typer.Typer) -> None:
    @app.command("reset")
    def reset_command(
        yes: bool = typer.Option(False, "--yes", help="确认清空数据库"),
        project_root: str | None = typer.Option(None, "--project-root", help="项目根目录，默认自动推导"),
        db: str | None = typer.Option(None, "--db", help="SQLite 数据库文件路径"),
        as_json: bool = typer.Option(False, "--json", help="输出 JSON"),
    ) -> None:
        require_confirmation(yes, "reset 会清空数据库，请显式传入 --yes")
        resolved_project_root = resolve_project_root(project_root)

        with closing(open_connection(resolved_project_root, db)) as connection:
            connection.execute("DELETE FROM transactions")
            connection.execute("DELETE FROM raw_rows")
            connection.execute("DELETE FROM import_batches")
            connection.commit()
            result = {
                "status": "success",
                "tables": {
                    "transactions": 0,
                    "raw_rows": 0,
                    "import_batches": 0,
                },
            }

        print_output(result, as_json=as_json)
