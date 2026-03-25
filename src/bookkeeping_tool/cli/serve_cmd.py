from __future__ import annotations

import webbrowser

import typer
import uvicorn

from bookkeeping_tool.cli.common import fail, resolve_project_root
from bookkeeping_tool.web.app import create_app, resolve_frontend_dist


def register(app: typer.Typer) -> None:
    @app.command("serve")
    def serve_command(
        host: str = typer.Option("127.0.0.1", "--host", help="服务监听地址"),
        port: int = typer.Option(8000, "--port", min=1, max=65535, help="服务端口"),
        project_root: str | None = typer.Option(None, "--project-root", help="运行数据根目录，默认使用环境变量或当前目录"),
        open_browser: bool = typer.Option(False, "--open", help="启动后打开浏览器"),
    ) -> None:
        resolved_project_root = resolve_project_root(project_root)
        frontend_dist = resolve_frontend_dist()
        if frontend_dist is None:
            fail("未找到可用的前端静态资源，请先构建前端产物后再执行 bookkeeping serve")

        app_instance = create_app(resolved_project_root, frontend_dist=frontend_dist)
        base_url = f"http://{host}:{port}"
        typer.echo(f"Web UI: {base_url}/")
        typer.echo(f"Docs: {base_url}/docs")
        if open_browser:
            webbrowser.open(base_url)
        uvicorn.run(app_instance, host=host, port=port)
