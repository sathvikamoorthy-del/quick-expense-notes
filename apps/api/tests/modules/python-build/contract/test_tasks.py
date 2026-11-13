import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))

import tasks  # noqa: E402


def test_the_documented_tasks_exist():
    assert set(tasks.COMMANDS) == {"run", "test", "lint", "openapi"}


def test_an_unknown_task_fails_with_exit_code_2(capsys):
    assert tasks.run("deploy") == 2
    assert "unknown task" in capsys.readouterr().err


def test_a_failing_step_stops_the_task(monkeypatch):
    calls = []

    def fake_call(cmd):
        calls.append(cmd)
        return 3

    monkeypatch.setattr(tasks.subprocess, "call", fake_call)
    assert tasks.run("lint") == 3
    assert len(calls) == 1  # stopped at the first failing step


def test_lint_runs_ruff_check_format_and_mypy(monkeypatch):
    calls = []
    monkeypatch.setattr(tasks.subprocess, "call", lambda cmd: calls.append(cmd) or 0)
    assert tasks.run("lint") == 0
    assert [c[0] if c[0] == "ruff" else c[2] for c in calls] == ["ruff", "ruff", "mypy"]
