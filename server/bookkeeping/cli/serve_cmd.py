from __future__ import annotations

import webbrowser

import typer
import uvicorn

from server.bookkeeping.cli.common import resolve_project_root
from server.web.app import create_app


def register(app: typer.Typer) -> None:
    @app.command("serve")
    def serve_command(
        host: str = typer.Option("127.0.0.1", "--host", help="服务监听地址"),
        port: int = typer.Option(8000, "--port", min=1, max=65535, help="服务端口"),
        project_root: str | None = typer.Option(None, "--project-root", help="项目根目录，默认自动推导"),
        open_browser: bool = typer.Option(False, "--open", help="启动后打开浏览器"),
    ) -> None:
        resolved_project_root = resolve_project_root(project_root)
        app_instance = create_app(resolved_project_root)
        base_url = f"http://{host}:{port}"
        typer.echo(f"Server: {base_url}")
        typer.echo(f"Docs: {base_url}/docs")
        typer.echo("Frontend dev: http://127.0.0.1:5173")
        if open_browser:
            webbrowser.open(base_url)
        uvicorn.run(app_instance, host=host, port=port)
