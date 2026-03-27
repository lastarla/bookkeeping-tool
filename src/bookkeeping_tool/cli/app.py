from __future__ import annotations

from importlib import import_module

import typer

COMMAND_MODULES = [
    "bookkeeping_tool.cli.import_cmd",
    "bookkeeping_tool.cli.query_cmd",
    "bookkeeping_tool.cli.summary_cmd",
    "bookkeeping_tool.cli.record_cmd",
    "bookkeeping_tool.cli.budget_cmd",
    "bookkeeping_tool.cli.serve_cmd",
    "bookkeeping_tool.cli.reset_cmd",
    "bookkeeping_tool.cli.inspect_cmd",
]


def create_app() -> typer.Typer:
    app = typer.Typer(help="bookkeeping 本地记账工具 CLI")
    for module_name in COMMAND_MODULES:
        import_module(module_name).register(app)
    return app


def main() -> None:
    create_app()()


if __name__ == "__main__":
    main()
