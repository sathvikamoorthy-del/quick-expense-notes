"""REQ-277 / WI-047: several entries in one text box, with today = 12 Nov 2026 (IST)."""

import pytest

from app.entries.ai_read import AI_UNAVAILABLE, AI_UNREADABLE, TOO_MANY_PLAIN, AiFailure
from app.entries.batch import (
    MAX_ENTRIES,
    TOO_MANY_ENTRIES,
    AiLine,
    EntryResult,
    TooMany,
    expand_all,
    plan_all,
    split_entries,
)
from app.entries.expand import EntryError, Expanded
from tests.entries.test_ai_read import SENTENCE, FakeReader, zomato_answer
from tests.entries.test_expand import CODES, TODAY, YESTERDAY


def results(text: str) -> list[EntryResult]:
    """Code-form text boxes only: every entry is expanded by the rules."""
    outcome = plan_all(text, TODAY, CODES)
    assert isinstance(outcome, list), outcome
    assert all(isinstance(item, EntryResult) for item in outcome)
    return [item for item in outcome if isinstance(item, EntryResult)]


def test_the_sample_text_box_gives_three_entries_and_one_error():
    # 03-sample-entries.md "Several entries in one text box"
    out = results("F 250; SWG 340 yd\nX 100\nUBR 180 12/11 airport")
    assert [r.typed for r in out] == ["F 250", "SWG 340 yd", "X 100", "UBR 180 12/11 airport"]
    f, swg, x, ubr = (r.result for r in out)
    assert isinstance(f, Expanded) and (f.merchant, f.category, f.amount, f.date) == (None, "Food", "250.00", TODAY)
    assert isinstance(swg, Expanded) and (swg.merchant, swg.amount, swg.date) == ("Swiggy", "340.00", YESTERDAY)
    assert x == EntryError('Unknown code "X".')
    assert isinstance(ubr, Expanded) and (ubr.merchant, ubr.category, ubr.note) == ("Uber", "Travel", "airport")


@pytest.mark.parametrize(
    "text",
    ["F 250\nR 1.5k\nNFX 649", "F 250;R 1.5k;NFX 649", "F 250; R 1.5k\nNFX 649", "F 250\r\nR 1.5k\r\nNFX 649"],
)
def test_new_lines_and_semicolons_both_separate_entries(text):
    assert split_entries(text) == ["F 250", "R 1.5k", "NFX 649"]


@pytest.mark.parametrize("text", ["F 250;;", ";F 250", "\n\nF 250\n\n", "  ;  F 250  ;  \n  "])
def test_empty_parts_are_skipped_with_no_result(text):
    assert [r.typed for r in results(text)] == ["F 250"]


def test_inner_spaces_of_an_entry_are_kept_as_typed():
    assert results("  APL 420 td  fever tablets ; ")[0].typed == "APL 420 td  fever tablets"


def test_an_error_does_not_stop_the_other_entries():
    out = results("X 1\nF 250\nF\nSWG 340\nF 100 20/11")
    assert [r.result.message if isinstance(r.result, EntryError) else r.result.amount for r in out] == [
        'Unknown code "X".',
        "250.00",
        "Amount is missing.",
        "340.00",
        "Date cannot be in the future.",
    ]


def test_twenty_entries_are_accepted():
    assert len(results(";".join(["F 1"] * MAX_ENTRIES))) == MAX_ENTRIES


def test_more_than_twenty_entries_reject_the_whole_text_box():
    outcome = plan_all("\n".join(["F 1"] * (MAX_ENTRIES + 1)), TODAY, CODES)
    assert outcome == TooMany()
    assert outcome.message == TOO_MANY_ENTRIES == "Too many entries (max 20)."


def test_empty_parts_do_not_count_toward_the_maximum():
    assert len(results(";;\n".join(["F 1"] * MAX_ENTRIES) + ";;;\n\n")) == MAX_ENTRIES


def test_a_text_box_with_no_entries_gives_no_results():
    assert results(" ;\n; ") == []


# REQ-438 / WI-066: plain-words lines read with AI help (a fake reader; no test calls the Claude API)


def test_code_form_lines_are_planned_for_the_rules_and_others_for_ai():
    planned = plan_all(f"X 100\n{SENTENCE}\nF\nUber 180", TODAY, CODES)
    assert planned == [
        EntryResult(typed="X 100", result=EntryError('Unknown code "X".')),
        AiLine(typed=SENTENCE),
        EntryResult(typed="F", result=EntryError("Amount is missing.")),
        AiLine(typed="Uber 180"),
    ]


async def test_plain_words_lines_are_read_by_ai_and_marked():
    reader = FakeReader({SENTENCE: zomato_answer()})
    out = await expand_all(f"F 250\n{SENTENCE}", TODAY, CODES, reader)
    assert isinstance(out, list)
    assert [(r.typed, r.ai) for r in out] == [("F 250", False), (SENTENCE, True)]
    entry = out[1].result
    assert isinstance(entry, Expanded)
    assert (entry.code, entry.merchant, entry.category, entry.amount, entry.date, entry.note) == (
        "ZMT",
        "Zomato",
        "Food",
        "450.00",
        YESTERDAY,
        "dinner",
    )
    assert reader.calls == [SENTENCE]


async def test_a_code_form_line_is_never_sent_to_ai():
    reader = FakeReader({})
    out = await expand_all("X 100\nF -50\nswg 340", TODAY, CODES, reader)
    assert isinstance(out, list) and reader.calls == []
    assert [r.ai for r in out] == [False, False, False]


async def test_at_most_five_plain_words_lines_are_read():
    lines = [f"paid {n} for tea" for n in range(1, 7)]
    reader = FakeReader({})
    out = await expand_all("\n".join(lines), TODAY, CODES, reader)
    assert isinstance(out, list)
    assert reader.calls == lines[:5]
    assert out[5] == EntryResult(typed=lines[5], result=EntryError(TOO_MANY_PLAIN), ai=True)
    assert TOO_MANY_PLAIN == "Too many plain-words lines (max 5)."


async def test_plain_words_lines_still_count_toward_twenty_entries():
    text = "\n".join(["F 1"] * 18 + ["paid 1 for tea"] * 3)
    assert await expand_all(text, TODAY, CODES, FakeReader({})) == TooMany()


@pytest.mark.parametrize(
    ("failure", "message"), [(AiFailure.UNAVAILABLE, AI_UNAVAILABLE), (AiFailure.UNREADABLE, AI_UNREADABLE)]
)
async def test_an_ai_failure_stops_only_that_line(failure, message):
    out = await expand_all(f"F 250\n{SENTENCE}\nSWG 340 yd", TODAY, CODES, FakeReader({SENTENCE: failure}))
    assert isinstance(out, list)
    assert out[1] == EntryResult(typed=SENTENCE, result=EntryError(message), ai=True)
    assert isinstance(out[0].result, Expanded) and isinstance(out[2].result, Expanded)


async def test_a_reader_that_raises_stops_only_that_line_with_the_unavailable_message():
    class Broken:
        async def read(self, line, today, codes):
            raise RuntimeError("boom")

    out = await expand_all(f"F 250\n{SENTENCE}", TODAY, CODES, Broken())
    assert isinstance(out, list) and isinstance(out[0].result, Expanded)
    assert out[1] == EntryResult(typed=SENTENCE, result=EntryError(AI_UNAVAILABLE), ai=True)
