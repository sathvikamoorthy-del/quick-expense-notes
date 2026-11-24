"""REQ-438 / WI-066: the Claude API call, with a fake AsyncAnthropic (no test calls the real API)."""

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


async def test_without_any_credentials_the_ai_is_unavailable(monkeypatch):
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE", "ANTHROPIC_FEDERATION_RULE_ID"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ANTHROPIC_CONFIG_DIR", "Z:/no-such-dir")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:9")  # never the real API, even if credentials exist
    reader = ClaudeReader(AiSettings(ai_max_retries=0, ai_timeout_seconds=2))
    assert await reader.read(SENTENCE, TODAY, CODES) is AiFailure.UNAVAILABLE


def test_the_api_key_setting_is_passed_to_the_client_and_one_reader_is_kept():
    reader = ClaudeReader(AiSettings(anthropic_api_key="test-key", ai_max_retries=0))
    client = reader._get_client()
    assert client.api_key == "test-key" and client.max_retries == 0
    assert reader._get_client() is client
    assert get_ai_reader() is get_ai_reader()
