import sqlite3
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
USER = "11111111-1111-1111-1111-111111111111"  # a users row: saved expenses reference it


@pytest.fixture
def db_file(tmp_path):
    return build_seeded_db(tmp_path, users=(USER,))


@pytest.fixture
def client(db_file, monkeypatch):
    clear_codes_cache()
    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setenv("DATABASE_URL", f"file:{db_file}")
    monkeypatch.setattr("app.entries.routes.today_ist", lambda: date(2026, 11, 12))
    with client_for(create_app(settings=Settings(env="development"))) as test_client:
        yield test_client
    clear_codes_cache()


def expense_count(db_file) -> int:
    connection = sqlite3.connect(db_file)
    try:
        return connection.execute("SELECT count(*) FROM expenses").fetchone()[0]
    finally:
        connection.close()


def bearer(user: str = USER) -> dict[str, str]:
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


SAMPLE = "F 250; SWG 340 yd\nX 100\nUBR 180 12/11 airport"


def test_expand_all_gives_one_result_per_entry_in_typed_order(client):
    response = client.post("/entries/expand-all", json={"text": SAMPLE}, headers=bearer())
    assert response.status_code == 200
    body = response.json()
    assert (body["ok"], body["error"]) == (True, None)
    assert [(r["typed"], r["ok"], r["error"]) for r in body["results"]] == [
        ("F 250", True, None),
        ("SWG 340 yd", True, None),
        ("X 100", False, 'Unknown code "X".'),
        ("UBR 180 12/11 airport", True, None),
    ]
    assert body["results"][0]["entry"] == {
        "code": "F",
        "merchant": None,
        "category": "Food",
        "amount": "250.00",
        "amount_paise": 25000,
        "date": "2026-11-12",
        "note": None,
    }
    assert body["results"][2]["entry"] is None
    assert body["results"][3]["entry"]["note"] == "airport"


def test_expand_all_rejects_more_than_twenty_entries(client):
    response = client.post("/entries/expand-all", json={"text": "\n".join(["F 1"] * 21)}, headers=bearer())
    assert response.status_code == 200
    assert response.json() == {"ok": False, "error": "Too many entries (max 20).", "results": []}


def test_expand_all_not_signed_in_is_401(client):
    assert client.post("/entries/expand-all", json={"text": "F 250"}).status_code == 401


@pytest.mark.parametrize("body", [{}, {"text": ""}, {"text": "  \n ; ;; "}, {"text": "F 1;" * 3000}])
def test_expand_all_missing_empty_or_too_long_text_is_422(client, body):
    response = client.post("/entries/expand-all", json=body, headers=bearer())
    assert response.status_code == 422
    assert response.json()["error"] == "validation-error"


def reviewed(client, text: str) -> list[dict]:
    return client.post("/entries/expand-all", json={"text": text}, headers=bearer()).json()["results"]


def test_save_stores_the_valid_reviewed_entries_and_returns_the_failed_ones(client, db_file):
    response = client.post(
        "/entries/save", json={"text": SAMPLE, "reviewed": reviewed(client, SAMPLE)}, headers=bearer()
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["ok"], body["error"], body["saved"], len(body["ids"])) == (True, None, 3, 3)
    assert body["failed"] == [{"typed": "X 100", "ok": False, "entry": None, "error": 'Unknown code "X".'}]
    assert expense_count(db_file) == 3


def test_save_refuses_a_review_that_differs_and_saves_nothing(client, db_file):
    results = reviewed(client, SAMPLE)
    results[0]["entry"]["amount_paise"] = 26000
    response = client.post("/entries/save", json={"text": SAMPLE, "reviewed": results}, headers=bearer())
    assert response.status_code == 200
    assert response.json() == {
        "ok": False,
        "error": "The entries changed since the review. Press Expand to review them again.",
        "saved": 0,
        "ids": [],
        "failed": [],
    }
    assert expense_count(db_file) == 0


def test_expanding_saves_nothing(client, db_file):
    reviewed(client, SAMPLE)
    client.post("/entries/expand", json={"text": "F 250"}, headers=bearer())
    assert expense_count(db_file) == 0


def test_save_not_signed_in_is_401(client):
    assert client.post("/entries/save", json={"text": "F 250", "reviewed": []}).status_code == 401


def test_save_for_a_token_with_no_users_row_is_401(client, db_file):
    other = bearer("33333333-3333-3333-3333-333333333333")
    response = client.post(
        "/entries/save", json={"text": "F 250", "reviewed": reviewed(client, "F 250")}, headers=other
    )
    assert (response.status_code, response.json()) == (401, {"error": "unauthorized"})
    assert expense_count(db_file) == 0


@pytest.mark.parametrize(
    "body",
    [
        {"text": "F 250"},
        {"text": "", "reviewed": []},
        {"text": " ; ", "reviewed": []},
        {"text": "F 1;" * 3000, "reviewed": []},
    ],
)
def test_save_missing_empty_or_too_long_is_422(client, body):
    response = client.post("/entries/save", json=body, headers=bearer())
    assert response.status_code == 422
    assert response.json()["error"] == "validation-error"
