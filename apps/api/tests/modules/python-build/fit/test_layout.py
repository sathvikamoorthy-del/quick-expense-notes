from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def test_scripts_sit_next_to_the_app():
    assert (ROOT / "scripts" / "tasks.py").is_file()
    assert (ROOT / "app" / "http" / "app.py").is_file()
