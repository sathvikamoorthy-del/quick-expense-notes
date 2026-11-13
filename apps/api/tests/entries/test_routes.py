import time
from datetime import date

import jwt
import pytest

from app.entries.codes import clear_codes_cache
from app.http.app import create_app
from app.http.settings import Settings
from tests.entries.test_codes import build_seeded_db
from tests.helpers import client_for

SECRET = "s" * 40


@pytest.fixture
def client(tmp_path, monkeypatch):
    clear_codes_cache()
    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setenv("DATABASE_URL", f"file:{build_seeded_db(tmp_path)}")
    monkeypatch.setattr("app.entries.routes.today_ist", lambda: date(2026, 11, 12))
    with client_for(create_app(settings=Settings(env="development"))) as test_client:
        yield test_client
    clear_codes_cache()


def bearer(user: str = "user-1") -> dict[str, str]:
    token = jwt.encode({"sub": user, "exp": int(time.time()) + 60}, SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def test_expands_an_entry_for_a_signed_in_user(client):
    response = client.post("/entries/expand", json={"text": "swg 340 yd late dinner"}, headers=bearer())
    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "entry": {
            "code": "SWG",
            "merchant": "Swiggy",
            "category": "Food",
            "amount": "340.00",
            "amount_paise": 34000,
            "date": "2026-11-11",
            "note": "late dinner",
        },
        "error": None,
    }


def test_a_rule_error_is_a_normal_answer_with_the_exact_message(client):
    response = client.post("/entries/expand", json={"text": "X 100"}, headers=bearer())
    assert response.status_code == 200
    assert response.json() == {"ok": False, "entry": None, "error": 'Unknown code "X".'}


def test_a_category_code_has_no_merchant(client):
    entry = client.post("/entries/expand", json={"text": "R 1.5k"}, headers=bearer()).json()["entry"]
    assert (entry["merchant"], entry["category"], entry["amount"], entry["note"]) == (None, "Rent", "1500.00", None)


def test_not_signed_in_is_401(client):
    response = client.post("/entries/expand", json={"text": "F 250"})
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}


@pytest.mark.parametrize("body", [{}, {"text": ""}, {"text": "   "}, {"text": "F " + "1" * 600}])
def test_missing_empty_or_too_long_text_is_422(client, body):
    response = client.post("/entries/expand", json=body, headers=bearer())
    assert response.status_code == 422
    assert response.json()["error"] == "validation-error"
