from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

import typer

from bookkeeping_tool.db import connect, get_default_db_path, init_db


PROJECT_ROOT_ENV_VAR = "BOOKKEEPING_PROJECT_ROOT"


def resolve_project_root(project_root: str | None = None) -> Path:
    if project_root:
        return Path(project_root).expanduser().resolve()

    env_project_root = os.environ.get(PROJECT_ROOT_ENV_VAR)
    if env_project_root:
        return Path(env_project_root).expanduser().resolve()

    return Path.cwd().resolve()


def resolve_db_path(project_root: Path, db_path: str | None = None) -> Path:
    if db_path:
        return Path(db_path).expanduser().resolve()
    return get_default_db_path(project_root)


def open_connection(project_root: Path, db_path: str | None = None) -> sqlite3.Connection:
    resolved_db_path = resolve_db_path(project_root, db_path)
    connection = connect(resolved_db_path)
    init_db(connection)
    return connection


def parse_json_input(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    loaded = json.loads(value)
    if not isinstance(loaded, dict):
        raise ValueError("JSON 输入必须是对象")
    return loaded


def print_output(data: Any, *, as_json: bool) -> None:
    if as_json:
        typer.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if isinstance(data, (dict, list)):
        typer.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return

    typer.echo(str(data))


def fail(message: str, exit_code: int = 1) -> None:
    typer.echo(message, err=True)
    raise typer.Exit(code=exit_code)


def require_confirmation(confirmed: bool, message: str) -> None:
    if not confirmed:
        typer.echo(message, err=True)
        raise typer.Exit(code=2)
