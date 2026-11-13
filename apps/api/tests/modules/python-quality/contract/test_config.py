import configparser
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def test_ruff_lints_errors_imports_bugbear_and_upgrades():
    cfg = tomllib.loads((ROOT / "ruff.toml").read_text())
    assert {"E", "F", "I", "B"} <= set(cfg["lint"]["select"])
    assert cfg["line-length"] >= 100


def test_mypy_is_strict_and_checks_the_app():
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "mypy.ini")
    assert cfg["mypy"]["strict"] == "True"
    assert "app" not in cfg["mypy"]["exclude"]


def test_fastapi_parameter_markers_are_allowed_in_defaults():
    cfg = tomllib.loads((ROOT / "ruff.toml").read_text())
    assert "fastapi.Depends" in cfg["lint"]["flake8-bugbear"]["extend-immutable-calls"]


def test_the_scaffold_owned_glue_files_are_exempt_from_import_sorting():
    cfg = tomllib.loads((ROOT / "ruff.toml").read_text())
    assert "I001" in cfg["lint"]["per-file-ignores"]["app/glue/*.py"]
