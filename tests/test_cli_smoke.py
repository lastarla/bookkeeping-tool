from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
ENV = {
    **os.environ,
    "PYTHONPATH": str(ROOT / "src"),
}
CLI_ENTRY = [sys.executable, "-m", "bookkeeping_tool.cli.app"]


def run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*CLI_ENTRY, *args],
        cwd=cwd or ROOT,
        env=ENV,
        text=True,
        capture_output=True,
        check=False,
    )


def get_free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class CliSmokeTests(unittest.TestCase):
    def test_importing_cli_module_does_not_preload_heavy_dependencies(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import json, sys; "
                    "import bookkeeping_tool.cli.app; "
                    "print(json.dumps({"
                    "'pandas': 'pandas' in sys.modules, "
                    "'fastapi': 'fastapi' in sys.modules, "
                    "'uvicorn': 'uvicorn' in sys.modules}))"
                ),
            ],
            cwd=ROOT,
            env=ENV,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        loaded = json.loads(result.stdout.strip())
        self.assertEqual(loaded, {"pandas": False, "fastapi": False, "uvicorn": False})

    def test_help_commands_work(self) -> None:
        result = run_cli("--help")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("bookkeeping 本地记账工具 CLI", result.stdout)

        query_help = run_cli("query", "--help")
        self.assertEqual(query_help.returncode, 0, msg=query_help.stderr)
        self.assertIn("--start-date", query_help.stdout)

        summary_help = run_cli("summary", "--help")
        self.assertEqual(summary_help.returncode, 0, msg=summary_help.stderr)
        self.assertIn("overview", summary_help.stdout)

        record_help = run_cli("record", "--help")
        self.assertEqual(record_help.returncode, 0, msg=record_help.stderr)
        self.assertIn("expense", record_help.stdout)

        budget_help = run_cli("budget", "--help")
        self.assertEqual(budget_help.returncode, 0, msg=budget_help.stderr)
        self.assertIn("set", budget_help.stdout)

    def test_import_query_and_summary_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            csv_path = tmp_path / "alice_alipay_2025.csv"
            csv_path.write_text(
                "交易时间,交易分类,收/支,金额\n"
                "2025-03-01 08:30:00,餐饮,支出,12.50\n"
                "2025-03-02 09:00:00,工资,收入,100.00\n",
                encoding="utf-8",
            )

            imported = run_cli("import", str(csv_path), "--project-root", str(tmp_path), "--json")
            self.assertEqual(imported.returncode, 0, msg=imported.stderr)
            imported_payload = json.loads(imported.stdout)
            self.assertEqual(imported_payload["status"], "success")
            self.assertEqual(imported_payload["imported_rows"], 2)

            budget = run_cli(
                "budget",
                "set",
                "--scope",
                "month",
                "--period",
                "2025-03",
                "--amount",
                "20",
                "--owner",
                "alice",
                "--platform",
                "alipay",
                "--project-root",
                str(tmp_path),
                "--json",
            )
            self.assertEqual(budget.returncode, 0, msg=budget.stderr)
            budget_payload = json.loads(budget.stdout)
            self.assertEqual(budget_payload["scope"], "month")

            recorded = run_cli(
                "record",
                "expense",
                "--trade-date",
                "2025-03-03",
                "--amount",
                "8",
                "--owner",
                "alice",
                "--platform",
                "alipay",
                "--category",
                "餐饮",
                "--note",
                "午饭",
                "--project-root",
                str(tmp_path),
                "--json",
            )
            self.assertEqual(recorded.returncode, 0, msg=recorded.stderr)
            recorded_payload = json.loads(recorded.stdout)
            self.assertEqual(recorded_payload["direction"], "expense")
            self.assertEqual(recorded_payload["category"], "餐饮")
            self.assertEqual(len(recorded_payload["budget_checks"]), 3)

            queried = run_cli("query", "--project-root", str(tmp_path), "--limit", "5", "--json")
            self.assertEqual(queried.returncode, 0, msg=queried.stderr)
            queried_payload = json.loads(queried.stdout)
            self.assertEqual(len(queried_payload), 3)

            summary = run_cli(
                "summary",
                "overview",
                "--project-root",
                str(tmp_path),
                "--view",
                "monthly",
                "--month",
                "2025-03",
                "--json",
            )
            self.assertEqual(summary.returncode, 0, msg=summary.stderr)
            summary_payload = json.loads(summary.stdout)
            self.assertIn("total_expense", summary_payload)
            self.assertIn("total_income", summary_payload)

    def test_category_fallback_and_budget_reminders(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            unset_record = run_cli(
                "record",
                "expense",
                "--trade-date",
                "2025-03-10",
                "--amount",
                "20",
                "--owner",
                "alice",
                "--platform",
                "wechat",
                "--category",
                "随便写的分类",
                "--project-root",
                str(tmp_path),
                "--json",
            )
            self.assertEqual(unset_record.returncode, 0, msg=unset_record.stderr)
            unset_payload = json.loads(unset_record.stdout)
            self.assertEqual(unset_payload["category"], "其他支出")
            self.assertEqual(len(unset_payload["reminders"]), 3)
            self.assertEqual({item["status"] for item in unset_payload["reminders"]}, {"unset"})

            budget = run_cli(
                "budget",
                "set",
                "--scope",
                "month",
                "--period",
                "2025-03",
                "--amount",
                "100",
                "--owner",
                "alice",
                "--platform",
                "wechat",
                "--project-root",
                str(tmp_path),
                "--json",
            )
            self.assertEqual(budget.returncode, 0, msg=budget.stderr)
            budget_payload = json.loads(budget.stdout)
            self.assertEqual(budget_payload["scope_label"], "月")
            self.assertIsNone(budget_payload["reminder"])

            warning_record = run_cli(
                "record",
                "expense",
                "--trade-date",
                "2025-03-11",
                "--amount",
                "61",
                "--owner",
                "alice",
                "--platform",
                "wechat",
                "--category",
                "餐饮",
                "--project-root",
                str(tmp_path),
                "--json",
            )
            self.assertEqual(warning_record.returncode, 0, msg=warning_record.stderr)
            warning_payload = json.loads(warning_record.stdout)
            month_warning = next(item for item in warning_payload["reminders"] if item["scope"] == "month")
            self.assertEqual(month_warning["status"], "warning")
            self.assertEqual(month_warning["severity"], "warning")
            self.assertIn("月预算已达到80%", month_warning["channel_text"])

            exceeded_record = run_cli(
                "record",
                "expense",
                "--trade-date",
                "2025-03-12",
                "--amount",
                "30",
                "--owner",
                "alice",
                "--platform",
                "wechat",
                "--category",
                "交通",
                "--project-root",
                str(tmp_path),
                "--json",
            )
            self.assertEqual(exceeded_record.returncode, 0, msg=exceeded_record.stderr)
            exceeded_payload = json.loads(exceeded_record.stdout)
            month_exceeded = next(item for item in exceeded_payload["reminders"] if item["scope"] == "month")
            self.assertEqual(month_exceeded["status"], "exceeded")
            self.assertEqual(month_exceeded["severity"], "critical")
            self.assertIn("月预算已超限", month_exceeded["channel_text"])

            budget_check = run_cli(
                "budget",
                "check",
                "--scope",
                "month",
                "--trade-date",
                "2025-03-12",
                "--owner",
                "alice",
                "--platform",
                "wechat",
                "--project-root",
                str(tmp_path),
                "--json",
            )
            self.assertEqual(budget_check.returncode, 0, msg=budget_check.stderr)
            budget_check_payload = json.loads(budget_check.stdout)
            self.assertEqual(budget_check_payload["status"], "exceeded")
            self.assertEqual(budget_check_payload["severity"], "critical")

    def test_serve_routes_are_reachable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            port = get_free_port()
            process = subprocess.Popen(
                [
                    *CLI_ENTRY,
                    "serve",
                    "--project-root",
                    tmpdir,
                    "--port",
                    str(port),
                ],
                cwd=ROOT,
                env=ENV,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                deadline = time.time() + 20
                last_error: Exception | None = None
                while time.time() < deadline:
                    try:
                        with urlopen(f"http://127.0.0.1:{port}/", timeout=1) as response:
                            self.assertEqual(response.status, 200)
                        with urlopen(f"http://127.0.0.1:{port}/docs", timeout=1) as response:
                            self.assertEqual(response.status, 200)
                        with urlopen(f"http://127.0.0.1:{port}/api/meta/default-period", timeout=1) as response:
                            self.assertEqual(response.status, 200)
                        with urlopen(f"http://127.0.0.1:{port}/api/budget/check?scope=month&trade_date=2025-03-01", timeout=1) as response:
                            self.assertEqual(response.status, 200)
                        break
                    except Exception as exc:  # noqa: BLE001
                        last_error = exc
                        if process.poll() is not None:
                            stdout, stderr = process.communicate(timeout=2)
                            self.fail(f"serve exited early\nstdout:\n{stdout}\nstderr:\n{stderr}")
                        time.sleep(0.5)
                else:
                    stdout, stderr = process.communicate(timeout=2)
                    self.fail(f"serve did not become ready: {last_error}\nstdout:\n{stdout}\nstderr:\n{stderr}")
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
