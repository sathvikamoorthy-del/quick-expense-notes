import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))

import export_openapi  # noqa: E402


def test_export_writes_a_valid_openapi_document(tmp_path):
    out = export_openapi.export(str(tmp_path / "openapi.json"))
    doc = json.loads(out.read_text())
    assert doc["openapi"].startswith("3.")
    assert "paths" in doc
