"""REQ-438 / WI-066: the Claude API call, with a fake AsyncAnthropic (no test calls the real API)."""

import json
import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import anthropic
import httpx2
import pytest

from app.entries.ai_client import ClaudeReader, get_ai_reader, system_prompt, user_message
from app.entries.ai_read import AiAnswer, AiFailure
from app.entries.ai_settings import AiSettings
from tests.entries.test_ai_read import SENTENCE, zomato_answer
from tests.entries.test_expand import CODES, TODAY

REQUEST = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
API_DIR = Path(__file__).resolve().parents[2]
USER = "11111111-1111-1111-1111-111111111111"


class FakeMessages:
    def __init__(self, outcome: object) -> None:
        self.outcome = outcome
        self.kwargs: dict[str, Any] = {}

    async def parse(self, **kwargs: Any) -> object:
        self.kwargs = kwargs
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


def reader_for(outcome: object, **settings: Any) -> tuple[ClaudeReader, FakeMessages]:
    messages = FakeMessages(outcome)
    client = cast(anthropic.AsyncAnthropic, SimpleNamespace(messages=messages))
    return ClaudeReader(AiSettings(**settings), client=client), messages


def parsed(answer: AiAnswer | None, stop_reason: str = "end_turn") -> SimpleNamespace:
    return SimpleNamespace(stop_reason=stop_reason, parsed_output=answer)


def status_error(status: int) -> anthropic.APIStatusError:
    return anthropic.APIStatusError("error", response=httpx2.Response(status, request=REQUEST), body=None)


async def test_a_good_answer_is_returned_as_is():
    reader, _ = reader_for(parsed(zomato_answer()))
    assert await reader.read(SENTENCE, TODAY, CODES) == zomato_answer()


async def test_the_request_carries_only_the_line_today_and_the_code_tables():
    reader, messages = reader_for(parsed(zomato_answer()))
    await reader.read(SENTENCE, TODAY, CODES)
    sent = messages.kwargs
    assert sent["model"] == "claude-haiku-5-5"
    assert sent["output_format"] is AiAnswer
    assert sent["output_config"] == {"effort": "low"}
    assert sent["messages"] == [{"role": "user", "content": f"Today: 2026-11-12\nLine: {SENTENCE}"}]
    assert sent["system"] == system_prompt(CODES)
    assert set(sent) == {"model", "max_tokens", "output_config", "output_format", "system", "messages"}


def test_the_system_prompt_lists_the_code_tables_in_a_fixed_order():
    prompt = system_prompt(CODES)
    assert "F: Food" in prompt and "ZMT: Zomato, Food" in prompt and "BSN: BSNL, Utilities" in prompt
    assert prompt == system_prompt(dict(reversed(list(CODES.items()))))
    assert user_message("x", TODAY) == "Today: 2026-11-12\nLine: x"


def test_the_model_can_be_changed_by_a_setting(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    assert AiSettings().anthropic_model == "claude-sonnet-5-5"


async def test_a_model_set_by_the_setting_is_used():
    reader, messages = reader_for(parsed(zomato_answer()), anthropic_model="claude-sonnet-5-5")
    await reader.read(SENTENCE, TODAY, CODES)
    assert messages.kwargs["model"] == "claude-sonnet-5-5"


@pytest.mark.parametrize(
    "error",
    [
        anthropic.APIConnectionError(request=REQUEST),
        anthropic.APITimeoutError(request=REQUEST),
        status_error(401),
        status_error(403),
        status_error(429),
        status_error(500),
        status_error(529),
        anthropic.AnthropicError("no credentials"),
    ],
)
async def test_the_ai_is_unavailable_when_it_cannot_be_reached(error):
    reader, _ = reader_for(error)
    assert await reader.read(SENTENCE, TODAY, CODES) is AiFailure.UNAVAILABLE


@pytest.mark.parametrize(
    "outcome",
    [
        parsed(None),
        parsed(zomato_answer(), stop_reason="refusal"),
        parsed(zomato_answer(), stop_reason="max_tokens"),
        ValueError("not JSON"),
        anthropic.APIResponseValidationError(response=httpx2.Response(200, request=REQUEST), body=None),
    ],
)
async def test_an_answer_that_cannot_be_used_is_unreadable(outcome):
    reader, _ = reader_for(outcome)
    assert await reader.read(SENTENCE, TODAY, CODES) is AiFailure.UNREADABLE


CREDENTIAL_VARIABLES = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_PROFILE",
    "ANTHROPIC_FEDERATION_RULE_ID",
)


def no_credentials(monkeypatch) -> AiSettings:
    for name in CREDENTIAL_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    return AiSettings(_env_file=None, anthropic_api_key=None)  # type: ignore[call-arg]


async def test_without_an_api_key_the_ai_is_unavailable_and_the_sdk_is_not_called(monkeypatch):
    reader = ClaudeReader(no_credentials(monkeypatch))
    assert not reader.has_credentials()
    assert await reader.read(SENTENCE, TODAY, CODES) is AiFailure.UNAVAILABLE
    assert reader._client is None


@pytest.mark.parametrize("key", ["", "   "])
async def test_an_empty_api_key_counts_as_none(monkeypatch, key):
    no_credentials(monkeypatch)
    reader = ClaudeReader(AiSettings(_env_file=None, anthropic_api_key=key))  # type: ignore[call-arg]
    assert await reader.read(SENTENCE, TODAY, CODES) is AiFailure.UNAVAILABLE


async def test_an_api_key_in_the_environment_counts_as_credentials(monkeypatch):
    no_credentials(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    assert ClaudeReader(AiSettings(_env_file=None)).has_credentials()  # type: ignore[call-arg]


async def test_without_the_anthropic_package_the_ai_is_unavailable(monkeypatch):
    monkeypatch.setitem(sys.modules, "anthropic", None)  # `import anthropic` now raises ImportError
    reader = ClaudeReader(AiSettings(_env_file=None, anthropic_api_key="test-key"))  # type: ignore[call-arg]
    assert await reader.read(SENTENCE, TODAY, CODES) is AiFailure.UNAVAILABLE


async def test_the_sdk_refusing_to_authenticate_is_unavailable():
    # anthropic 2.x raises a plain TypeError ("Could not resolve authentication method") when building the request
    reader, _ = reader_for(TypeError("Could not resolve authentication method."))
    assert await reader.read(SENTENCE, TODAY, CODES) is AiFailure.UNAVAILABLE


def test_the_api_starts_and_answers_without_the_anthropic_package(tmp_path):
    """The whole scenario in a fresh interpreter where `import anthropic` fails: the API still starts, code-form
    entries expand, and a plain-words line gets the unavailable message (not a 500)."""
    script = textwrap.dedent(
        f"""
        import sys
        sys.modules["anthropic"] = None
        import json, os, time
        from datetime import date
        import jwt
        os.environ["JWT_SECRET"] = "s" * 40
        os.environ["DATABASE_URL"] = "file:{(tmp_path / "app.db").as_posix()}"
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        import app.entries.routes as routes
        routes.today_ist = lambda: date(2026, 11, 12)
        from app.http.app import create_app
        from app.http.settings import Settings
        from tests.entries.test_codes import build_seeded_db
        from tests.helpers import client_for
        build_seeded_db(__import__("pathlib").Path("{tmp_path.as_posix()}"), users=("{USER}",))
        token = jwt.encode({{"sub": "{USER}", "exp": int(time.time()) + 60}}, "s" * 40, algorithm="HS256")
        with client_for(create_app(settings=Settings(env="development"))) as client:
            response = client.post(
                "/entries/expand-all",
                json={{"text": "F 250\\n{SENTENCE}"}},
                headers={{"Authorization": "Bearer " + token}},
            )
        print(json.dumps({{"status": response.status_code, "body": response.json()}}))
        """
    )
    done = subprocess.run(
        [sys.executable, "-c", script], cwd=API_DIR, capture_output=True, text=True, timeout=120, check=False
    )
    assert done.returncode == 0, done.stderr
    answer = json.loads(done.stdout.strip().splitlines()[-1])
    assert answer["status"] == 200
    results = answer["body"]["results"]
    assert [(r["typed"], r["ok"], r["error"]) for r in results] == [
        ("F 250", True, None),
        (SENTENCE, False, "AI help is not available right now. Type the entry in code form or try again."),
    ]


def test_the_api_key_setting_is_passed_to_the_client_and_one_reader_is_kept():
    reader = ClaudeReader(AiSettings(anthropic_api_key="test-key", ai_max_retries=0))
    client = reader._get_client()
    assert client.api_key == "test-key" and client.max_retries == 0
    assert reader._get_client() is client
    assert get_ai_reader() is get_ai_reader()
