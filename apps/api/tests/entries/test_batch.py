"""REQ-277 / WI-047: several entries in one text box, with today = 12 Nov 2026 (IST)."""

import pytest

from app.entries.batch import MAX_ENTRIES, TOO_MANY_ENTRIES, EntryResult, TooMany, expand_all, split_entries
from app.entries.expand import EntryError, Expanded
from tests.entries.test_expand import CODES, TODAY, YESTERDAY


def results(text: str) -> list[EntryResult]:
    outcome = expand_all(text, TODAY, CODES)
    assert isinstance(outcome, list), outcome
    return outcome


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
    outcome = expand_all("\n".join(["F 1"] * (MAX_ENTRIES + 1)), TODAY, CODES)
    assert outcome == TooMany()
    assert outcome.message == TOO_MANY_ENTRIES == "Too many entries (max 20)."


def test_empty_parts_do_not_count_toward_the_maximum():
    assert len(results(";;\n".join(["F 1"] * MAX_ENTRIES) + ";;;\n\n")) == MAX_ENTRIES


def test_a_text_box_with_no_entries_gives_no_results():
    assert results(" ;\n; ") == []
