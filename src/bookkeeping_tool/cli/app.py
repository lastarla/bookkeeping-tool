from __future__ import annotations

import typer

from bookkeeping_tool.cli import import_cmd, inspect_cmd, query_cmd, reset_cmd, serve_cmd, summary_cmd

app = typer.Typer(help="bookkeeping 本地记账工具 CLI")

import_cmd.register(app)
query_cmd.register(app)
summary_cmd.register(app)
serve_cmd.register(app)
reset_cmd.register(app)
inspect_cmd.register(app)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
