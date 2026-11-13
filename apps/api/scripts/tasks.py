"""Project tasks: python scripts/tasks.py run | test | lint | openapi"""

import subprocess
import sys

COMMANDS = {
    "run": [sys.executable, "-m", "app.http.server"],
    "test": [sys.executable, "-m", "pytest"],
    "lint": None,  # several steps, see below
    "openapi": [sys.executable, "-m", "scripts.export_openapi"],
}
LINT_STEPS = [
    ["ruff", "check", "."],
    ["ruff", "format", "--check", "."],
    [sys.executable, "-m", "mypy", "app"],
]


def run(task: str) -> int:
    if task not in COMMANDS:
        print(f"unknown task '{task}'. Tasks: {', '.join(COMMANDS)}", file=sys.stderr)
        return 2
    steps = LINT_STEPS if task == "lint" else [COMMANDS[task]]
    for step in steps:
        code = subprocess.call(step)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1]) if len(sys.argv) > 1 else run(""))
