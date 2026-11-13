"""Today's date in IST (Asia/Kolkata): REQ-276 reckons "today", "yesterday" and "the future" in IST for every user."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")  # needs the tzdata package on Windows (no system time zone database there)


def today_ist(now: datetime | None = None) -> date:
    """The current date in IST. `now` (timezone-aware) is for tests."""
    return (now or datetime.now(IST)).astimezone(IST).date()
