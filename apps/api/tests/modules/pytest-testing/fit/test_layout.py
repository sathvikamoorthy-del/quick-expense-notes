from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def test_the_app_layout_matches_the_test_config():
    assert (ROOT / "app").is_dir()
    assert (ROOT / "tests").is_dir()
    assert (ROOT / "requirements.in").is_file()
