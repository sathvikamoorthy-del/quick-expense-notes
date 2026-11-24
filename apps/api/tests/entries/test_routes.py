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
    assert body["failed"] == [{"typed": "X 100", "ok": False, "entry": None, "error": 'Unknown code "X".', "ai": False}]
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


EIGHT = "F 250\nSWG 340 yd\nUBR 180 12/11 airport\nR 1.5k\nNFX 649\nAPL 420 td fever tablets\nS 2k td shoes\nAMZ 799.50"


def save_text(client, text: str) -> None:
    body = client.post(
        "/entries/save", json={"text": text, "reviewed": reviewed(client, text)}, headers=bearer()
    ).json()
    assert body["ok"], body


def test_summary_of_the_sample_month(client):
    save_text(client, EIGHT)
    response = client.get("/summary", params={"month": "2026-11"}, headers=bearer())
    assert response.status_code == 200
    body = response.json()
    assert [(c["category"], c["total"]) for c in body["categories"]] == [
        ("Food", "590.00"),
        ("Travel", "180.00"),
        ("Rent", "1500.00"),
        ("Entertainment", "649.00"),
        ("Health", "420.00"),
        ("Shopping", "2799.50"),
    ]
    assert (body["month"], body["current_month"], body["grand_total"], body["grand_total_paise"]) == (
        "2026-11",
        "2026-11",
        "6138.50",
        613850,
    )
    assert body["categories"][0] == {"code": "F", "category": "Food", "total": "590.00", "total_paise": 59000}


def test_summary_defaults_to_the_current_ist_month(client):
    body = client.get("/summary", headers=bearer()).json()
    assert (body["month"], body["current_month"], body["categories"], body["grand_total"]) == (
        "2026-11",
        "2026-11",
        [],
        "0.00",
    )


def test_summary_is_never_cached_and_follows_a_save_at_once(client):
    first = client.get("/summary", params={"month": "2026-11"}, headers=bearer())
    assert first.headers["cache-control"] == "no-store"
    assert first.json()["grand_total"] == "0.00"
    save_text(client, "F 250")
    second = client.get("/summary", params={"month": "2026-11"}, headers=bearer())
    assert second.headers.get("x-cache") is None
    assert second.json()["grand_total"] == "250.00"


@pytest.mark.parametrize("month", ["2026-12", "2027-01", "2026-13", "2026-1", "nov"])
def test_summary_of_a_future_or_bad_month_is_422(client, month):
    response = client.get("/summary", params={"month": month}, headers=bearer())
    assert (response.status_code, response.json()["error"]) == (422, "validation-error")


def test_summary_not_signed_in_is_401(client):
    assert client.get("/summary").status_code == 401


def saved_entries(client, month: str | None = None) -> dict:
    response = client.get("/entries", params={"month": month} if month else {}, headers=bearer())
    assert response.status_code == 200, response.json()
    return response.json()


def test_the_saved_entries_list_shows_the_month_newest_date_first(client):
    save_text(client, "F 250\nSWG 340 yd\nF 99 1/11")
    response = client.get("/entries", headers=bearer())
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert (body["month"], body["current_month"]) == ("2026-11", "2026-11")
    assert [(e["typed"], e["date"]) for e in body["entries"]] == [
        ("F 250", "2026-11-12"),
        ("SWG 340 yd", "2026-11-11"),
        ("F 99 1/11", "2026-11-01"),
    ]
    swg = body["entries"][1]
    assert {k: swg[k] for k in ("code", "merchant", "category", "amount", "amount_paise", "note")} == {
        "code": "SWG",
        "merchant": "Swiggy",
        "category": "Food",
        "amount": "340.00",
        "amount_paise": 34000,
        "note": None,
    }
    assert len(swg["id"]) == 36


def test_editing_an_entry_returns_it_and_the_list_shows_the_new_values_at_once(client):
    save_text(client, "UBR 180 12/11 airport")
    entry = saved_entries(client)["entries"][0]
    response = client.put(f"/entries/{entry['id']}", json={"text": "UBR 220 12/11 airport"}, headers=bearer())
    assert response.status_code == 200
    body = response.json()
    assert (body["ok"], body["error"], body["entry"]["amount"], body["entry"]["id"]) == (
        True,
        None,
        "220.00",
        entry["id"],
    )
    assert saved_entries(client)["entries"][0]["typed"] == "UBR 220 12/11 airport"
    assert client.get("/summary", headers=bearer()).json()["grand_total"] == "220.00"


def test_an_invalid_edit_is_a_normal_answer_and_changes_nothing(client):
    save_text(client, "F 250")
    entry = saved_entries(client)["entries"][0]
    response = client.put(f"/entries/{entry['id']}", json={"text": "X 100"}, headers=bearer())
    assert (response.status_code, response.json()) == (200, {"ok": False, "error": 'Unknown code "X".', "entry": None})
    assert saved_entries(client)["entries"][0] == entry


def test_editing_an_unknown_or_another_users_entry_is_404(client, db_file):
    save_text(client, "F 250")
    entry = saved_entries(client)["entries"][0]
    connection = sqlite3.connect(db_file)
    try:
        connection.execute(
            "INSERT INTO users (id, email, password_hash, display_name) VALUES (?, 'b@example.com', 'x', 'B')",
            ("22222222-2222-2222-2222-222222222222",),
        )
        connection.commit()
    finally:
        connection.close()
    other = bearer("22222222-2222-2222-2222-222222222222")
    response = client.put(f"/entries/{entry['id']}", json={"text": "F 1"}, headers=other)
    assert (response.status_code, response.json()["error"]) == (404, "not-found")
    assert client.get("/entries", headers=other).json()["entries"] == []
    unknown = client.put("/entries/00000000-0000-0000-0000-000000000000", json={"text": "F 1"}, headers=bearer())
    assert unknown.status_code == 404
    assert saved_entries(client)["entries"][0] == entry


@pytest.mark.parametrize("body", [{}, {"text": ""}, {"text": "   "}])
def test_an_edit_with_no_text_is_422(client, body):
    save_text(client, "F 250")
    entry = saved_entries(client)["entries"][0]
    response = client.put(f"/entries/{entry['id']}", json=body, headers=bearer())
    assert (response.status_code, response.json()["error"]) == (422, "validation-error")


@pytest.mark.parametrize("month", ["2026-12", "2026-13", "nov"])
def test_the_list_of_a_future_or_bad_month_is_422(client, month):
    response = client.get("/entries", params={"month": month}, headers=bearer())
    assert (response.status_code, response.json()["error"]) == (422, "validation-error")


def test_the_list_and_edit_need_sign_in(client):
    assert client.get("/entries").status_code == 401
    assert client.put("/entries/x", json={"text": "F 1"}).status_code == 401


def test_deleting_an_entry_removes_it_from_the_list_and_the_summary_at_once(client):
    save_text(client, "F 250\nNFX 649")
    entries = saved_entries(client)["entries"]
    netflix = next(e for e in entries if e["code"] == "NFX")
    assert [c["category"] for c in client.get("/summary", headers=bearer()).json()["categories"]] == [
        "Food",
        "Entertainment",
    ]
    response = client.delete(f"/entries/{netflix['id']}", headers=bearer())
    assert (response.status_code, response.content) == (204, b"")
    assert [e["typed"] for e in saved_entries(client)["entries"]] == ["F 250"]
    summary = client.get("/summary", headers=bearer()).json()
    assert ([c["category"] for c in summary["categories"]], summary["grand_total"]) == (["Food"], "250.00")
    again = client.delete(f"/entries/{netflix['id']}", headers=bearer())
    assert (again.status_code, again.json()["error"]) == (404, "not-found")


def test_deleting_another_users_or_an_unknown_entry_is_404_and_deletes_nothing(client, db_file):
    save_text(client, "F 250")
    entry = saved_entries(client)["entries"][0]
    connection = sqlite3.connect(db_file)
    try:
        connection.execute(
            "INSERT INTO users (id, email, password_hash, display_name) VALUES (?, 'c@example.com', 'x', 'C')",
            ("33333333-3333-3333-3333-333333333333",),
        )
        connection.commit()
    finally:
        connection.close()
    other = bearer("33333333-3333-3333-3333-333333333333")
    assert client.delete(f"/entries/{entry['id']}", headers=other).status_code == 404
    assert client.delete("/entries/00000000-0000-0000-0000-000000000000", headers=bearer()).status_code == 404
    assert saved_entries(client)["entries"] == [entry]


def test_deleting_needs_sign_in(client):
    assert client.delete("/entries/x").status_code == 401


# REQ-438 / WI-066: plain-words lines read with AI help (a fake reader; no test calls the Claude API)
@pytest.fixture
def fake_reader():
    from tests.entries.test_ai_read import SENTENCE, FakeReader, zomato_answer

    return FakeReader({SENTENCE: zomato_answer()})


@pytest.fixture
def ai_client(db_file, monkeypatch, fake_reader):
    from app.entries.ai_client import get_ai_reader

    clear_codes_cache()
    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setenv("DATABASE_URL", f"file:{db_file}")
    monkeypatch.setattr("app.entries.routes.today_ist", lambda: date(2026, 11, 12))
    app = create_app(settings=Settings(env="development"))
    app.dependency_overrides[get_ai_reader] = lambda: fake_reader
    with client_for(app) as test_client:
        yield test_client
    clear_codes_cache()


AI_SENTENCE = "paid 450 to zomato yesterday for dinner"


def test_expand_all_reads_a_plain_words_line_with_ai_and_marks_it(ai_client, fake_reader):
    text = f"F 250\n{AI_SENTENCE}\nX 100"
    results = ai_client.post("/entries/expand-all", json={"text": text}, headers=bearer()).json()["results"]
    assert [(r["typed"], r["ok"], r["ai"]) for r in results] == [
        ("F 250", True, False),
        (AI_SENTENCE, True, True),
        ("X 100", False, False),
    ]
    assert results[1]["entry"] == {
        "code": "ZMT",
        "merchant": "Zomato",
        "category": "Food",
        "amount": "450.00",
        "amount_paise": 45000,
        "date": "2026-11-11",
        "note": "dinner",
    }
    assert results[2]["error"] == 'Unknown code "X".'
    assert fake_reader.calls == [AI_SENTENCE]


def test_an_ai_failure_shows_on_that_line_only(ai_client):
    text = "F 250\nspent 99 on something odd"  # the fake reader cannot read it
    results = ai_client.post("/entries/expand-all", json={"text": text}, headers=bearer()).json()["results"]
    assert (results[0]["ok"], results[1]["ok"], results[1]["ai"]) == (True, False, True)
    assert results[1]["error"] == "The AI could not read this line. Type it in code form."


def test_save_stores_the_reviewed_ai_line_without_asking_the_ai_again(ai_client, fake_reader, db_file):
    text = f"F 250\n{AI_SENTENCE}"
    results = ai_client.post("/entries/expand-all", json={"text": text}, headers=bearer()).json()["results"]
    fake_reader.calls.clear()
    body = ai_client.post("/entries/save", json={"text": text, "reviewed": results}, headers=bearer()).json()
    assert (body["ok"], body["saved"]) == (True, 2)
    assert fake_reader.calls == []
    assert expense_count(db_file) == 2


def test_save_refuses_an_ai_flag_on_a_code_form_line(ai_client, db_file):
    results = ai_client.post("/entries/expand-all", json={"text": "F 250"}, headers=bearer()).json()["results"]
    results[0]["ai"] = True
    body = ai_client.post("/entries/save", json={"text": "F 250", "reviewed": results}, headers=bearer()).json()
    assert (body["ok"], body["error"]) == (
        False,
        "The entries changed since the review. Press Expand to review them again.",
    )
    assert expense_count(db_file) == 0


def test_the_list_gives_the_edit_text_and_an_edit_with_it_keeps_the_values(ai_client):
    text = f"SWG 340 yd\n{AI_SENTENCE}"
    results = ai_client.post("/entries/expand-all", json={"text": text}, headers=bearer()).json()["results"]
    assert ai_client.post("/entries/save", json={"text": text, "reviewed": results}, headers=bearer()).json()["ok"]
    entries = {e["typed"]: e for e in saved_entries(ai_client)["entries"]}
    assert entries["SWG 340 yd"]["edit_text"] == "SWG 340 yd"
    ai_entry = entries[AI_SENTENCE]
    assert ai_entry["edit_text"] == "ZMT 450 11/11 dinner"
    response = ai_client.put(f"/entries/{ai_entry['id']}", json={"text": ai_entry["edit_text"]}, headers=bearer())
    edited = response.json()
    assert edited["ok"], edited
    assert {k: edited["entry"][k] for k in ("code", "amount", "date", "note")} == {
        "code": "ZMT",
        "amount": "450.00",
        "date": "2026-11-11",
        "note": "dinner",
    }


def test_a_plain_words_line_without_an_api_key_gets_the_unavailable_message(db_file, monkeypatch):
    """The real ClaudeReader with no key anywhere: 200 with the message on that line, never a 500."""
    from app.entries.ai_client import ClaudeReader, get_ai_reader
    from app.entries.ai_settings import AiSettings

    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE", "ANTHROPIC_FEDERATION_RULE_ID"):
        monkeypatch.delenv(name, raising=False)
    clear_codes_cache()
    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setenv("DATABASE_URL", f"file:{db_file}")
    monkeypatch.setattr("app.entries.routes.today_ist", lambda: date(2026, 11, 12))
    app = create_app(settings=Settings(env="development"))
    reader = ClaudeReader(AiSettings(_env_file=None, anthropic_api_key=None))  # type: ignore[call-arg]
    app.dependency_overrides[get_ai_reader] = lambda: reader
    with client_for(app) as test_client:
        response = test_client.post("/entries/expand-all", json={"text": f"F 250\n{AI_SENTENCE}"}, headers=bearer())
    clear_codes_cache()
    assert response.status_code == 200
    assert [(r["typed"], r["ok"], r["error"], r["ai"]) for r in response.json()["results"]] == [
        ("F 250", True, None, False),
        (AI_SENTENCE, False, "AI help is not available right now. Type the entry in code form or try again.", True),
    ]
