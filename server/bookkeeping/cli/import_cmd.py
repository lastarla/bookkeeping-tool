from __future__ import annotations

from pathlib import Path

import typer

from server.bookkeeping.cli.common import fail, print_output, resolve_project_root, resolve_db_path
from server.bookkeeping.services.import_service import import_transactions


def register(app: typer.Typer) -> None:
    @app.command("import")
    def import_command(
        file_path: str = typer.Argument(..., help="账单文件路径，支持 CSV/XLSX"),
        project_root: str | None = typer.Option(None, "--project-root", help="项目根目录，默认自动推导"),
        db: str | None = typer.Option(None, "--db", help="SQLite 数据库文件路径"),
        original_file_name: str | None = typer.Option(None, "--original-file-name", help="覆盖用于解析 owner/platform 的原始文件名"),
        as_json: bool = typer.Option(False, "--json", help="输出 JSON"),
    ) -> None:
        resolved_project_root = resolve_project_root(project_root)
        source_path = Path(file_path).expanduser().resolve()
        if not source_path.exists() or not source_path.is_file():
            fail(f"文件不存在：{source_path}", exit_code=2)

        try:
            result = import_transactions(
                project_root=resolved_project_root,
                file_path=source_path,
                db_path=resolve_db_path(resolved_project_root, db),
                original_file_name=original_file_name,
            )
        except Exception as exc:
            fail(f"导入失败：{exc}")

        print_output(result, as_json=as_json)
