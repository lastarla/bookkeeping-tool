from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import typer

from server.bookkeeping.db import connect, get_default_db_path, init_db


def resolve_project_root(project_root: str | None = None) -> Path:
    if project_root:
        return Path(project_root).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def resolve_db_path(project_root: Path, db_path: str | None = None) -> Path:
    if db_path:
        return Path(db_path).expanduser().resolve()
    return get_default_db_path(project_root)


def open_connection(project_root: Path, db_path: str | None = None) -> sqlite3.Connection:
    resolved_db_path = resolve_db_path(project_root, db_path)
    connection = connect(resolved_db_path)
    init_db(connection)
    return connection


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
