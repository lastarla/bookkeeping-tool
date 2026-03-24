from __future__ import annotations

from pathlib import Path
import argparse

import uvicorn

from server.web.app import create_app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run bookkeeping dashboard server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parent
    app = create_app(project_root)
    base_url = f"http://{args.host}:{args.port}"
    print(f"Server: {base_url}")
    print(f"Docs: {base_url}/docs")
    print("Frontend dev: http://127.0.0.1:5173")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
