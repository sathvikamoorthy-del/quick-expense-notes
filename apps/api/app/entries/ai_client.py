"""The Claude API call that reads one plain-words line (REQ-438, WI-066).

Only the typed line, today's date and the category and merchant tables are sent (REQ-438 q6): no user id, name,
email or other entries. Every failure becomes an AiFailure for that line; nothing here raises to the route.

The `anthropic` package is imported only when a line is read, so the API starts and code-form entries work even when
the package is not installed; plain-words lines then get the unavailable message, as they do without an API key.
"""

import logging
import os
from datetime import date
from functools import lru_cache
from typing import TYPE_CHECKING

from pydantic import ValidationError

from app.entries.ai_read import AiAnswer, AiFailure
from app.entries.ai_settings import AiSettings, get_ai_settings
from app.entries.expand import CodeInfo

if TYPE_CHECKING:
    import anthropic

log = logging.getLogger(__name__)

# Environment variables through which the SDK can find credentials besides ANTHROPIC_API_KEY.
_CREDENTIAL_VARIABLES = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_PROFILE",
    "ANTHROPIC_FEDERATION_RULE_ID",
)

_INSTRUCTIONS = """You read one expense that a user typed in plain words and return it as structured data.

Rules:
- Use only codes from the tables below. Never invent a code.
- If the line names a merchant that is in the merchant table, set merchant_code to its code and category_code to null.
- If the line names a merchant that is not in the merchant table, set other_merchant to that name.
- Otherwise set category_code to the category that fits best, and merchant_code to null.
- amount is the amount in rupees exactly as written (for example 450, 799.50 or 1.5k). Never invent an amount.
- date is YYYY-MM-DD. Count words such as "yesterday" or "last friday" from the given today. No date means today.
- note is what the money was for, in a few words from the line, or null.
- Set readable to false when the line is not an expense or has no amount."""


def system_prompt(codes: dict[str, CodeInfo]) -> str:
    """Fixed instructions and the code tables, sorted, so the text is the same for every call."""
    categories = sorted((info.category_code, info.category) for info in codes.values() if info.merchant is None)
    merchants = sorted(
        (code, info.merchant, info.category) for code, info in codes.items() if info.merchant is not None
    )
    lines = [_INSTRUCTIONS, "", "Category table (code: category):"]
    lines += [f"{code}: {name}" for code, name in categories]
    lines += ["", "Merchant table (code: merchant, category):"]
    lines += [f"{code}: {merchant}, {category}" for code, merchant, category in merchants]
    return "\n".join(lines)


def user_message(line: str, today: date) -> str:
    return f"Today: {today.isoformat()}\nLine: {line}"


class ClaudeReader:
    """Reads a line with the Claude API (model from ANTHROPIC_MODEL, default Claude Haiku 5.5)."""

    def __init__(self, settings: AiSettings, client: "anthropic.AsyncAnthropic | None" = None) -> None:
        self._settings = settings
        self._client = client

    def _key(self) -> str | None:
        key = self._settings.anthropic_api_key
        value = key.get_secret_value().strip() if key else ""
        return value or None

    def has_credentials(self) -> bool:
        """A key in the settings (or .env), or one of the SDK's credential variables in the environment."""
        return self._key() is not None or any(os.environ.get(name, "").strip() for name in _CREDENTIAL_VARIABLES)

    def _get_client(self) -> "anthropic.AsyncAnthropic":
        if self._client is None:
            import anthropic  # here, not at the top: a missing package must not stop the API (ImportError is caught)

            self._client = anthropic.AsyncAnthropic(
                api_key=self._key(),
                timeout=self._settings.ai_timeout_seconds,
                max_retries=self._settings.ai_max_retries,
            )
        return self._client

    async def read(self, line: str, today: date, codes: dict[str, CodeInfo]) -> AiAnswer | AiFailure:
        if self._client is None and not self.has_credentials():
            log.warning("AI read skipped (unavailable): no ANTHROPIC_API_KEY or other credentials configured")
            return AiFailure.UNAVAILABLE
        try:
            client = self._get_client()
            import anthropic
        except Exception as error:  # ImportError when the package is missing, or the SDK refused to build a client
            return self._failed(AiFailure.UNAVAILABLE, error)

        try:
            response = await client.messages.parse(
                model=self._settings.anthropic_model,
                max_tokens=1024,
                output_config={"effort": "low"},
                output_format=AiAnswer,
                system=system_prompt(codes),
                messages=[{"role": "user", "content": user_message(line, today)}],
            )
        except anthropic.APIResponseValidationError as error:
            return self._failed(AiFailure.UNREADABLE, error)
        except anthropic.APIStatusError as error:  # 401, 403, 429, 5xx and any other refused request
            return self._failed(AiFailure.UNAVAILABLE, error)
        except anthropic.APIConnectionError as error:  # network errors and timeouts
            return self._failed(AiFailure.UNAVAILABLE, error)
        except anthropic.AnthropicError as error:  # e.g. credentials the SDK cannot use
            return self._failed(AiFailure.UNAVAILABLE, error)
        except (ValidationError, ValueError) as error:  # an answer that does not fit AiAnswer
            return self._failed(AiFailure.UNREADABLE, error)
        except Exception as error:  # anything else the SDK raises (e.g. TypeError for unresolved authentication)
            return self._failed(AiFailure.UNAVAILABLE, error)
        if response.stop_reason in ("refusal", "max_tokens") or response.parsed_output is None:
            log.warning("AI answer not usable: stop_reason=%s", response.stop_reason)
            return AiFailure.UNREADABLE
        return response.parsed_output

    @staticmethod
    def _failed(failure: AiFailure, error: Exception) -> AiFailure:
        # Never log the line or the key: only what went wrong.
        log.warning("AI read failed (%s): %s", failure.value, type(error).__name__)
        return failure


@lru_cache
def get_ai_reader() -> ClaudeReader:
    """FastAPI dependency: one reader per process. Tests override it with a fake reader."""
    return ClaudeReader(get_ai_settings())
