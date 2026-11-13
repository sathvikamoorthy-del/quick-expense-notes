import configparser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def test_pytest_ini_runs_tests_under_tests_with_the_app_on_the_path():
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "pytest.ini")
    section = cfg["pytest"]
    assert section["testpaths"] == "tests"
    assert section["pythonpath"] == "."
    assert section["asyncio_mode"] == "auto"
    assert "--cov=app" in section["addopts"]


def test_coverage_gate_is_at_least_80_percent_and_excludes_glue():
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / ".coveragerc")
    assert int(cfg["report"]["fail_under"]) >= 80
    assert "app/glue/*" in cfg["run"]["omit"]
