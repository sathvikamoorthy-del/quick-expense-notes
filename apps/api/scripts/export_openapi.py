"""Writes openapi.json from the app (the input of a web app's typed client).

Usage: python -m scripts.export_openapi [path]
"""

import json
import sys
from pathlib import Path

from app.http.app import create_app
from app.http.settings import Settings


def export(path: str = "openapi.json") -> Path:
    # development settings so the schema is available whatever ENV the shell has
    app = create_app(settings=Settings(env="development"))
    out = Path(path)
    out.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")
    return out


if __name__ == "__main__":
    print(export(sys.argv[1] if len(sys.argv) > 1 else "openapi.json"))
