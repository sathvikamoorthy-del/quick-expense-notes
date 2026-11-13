from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def test_app_folder_exists_for_the_checkers():
    assert (ROOT / "app").is_dir()
    assert (ROOT / "ruff.toml").is_file() and (ROOT / "mypy.ini").is_file()
