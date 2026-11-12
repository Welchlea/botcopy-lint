from pathlib import Path

import pytest

from botcopy_lint.checker import check_messages, default_style, load_messages, load_style, summary
from botcopy_lint.cli import main
from botcopy_lint.rules import check_message

EXAMPLES = Path(__file__).parent.parent / "examples"
STYLE = default_style()


def rules_for(text, style=STYLE):
    return [f.rule for f in check_message("m", text, style)]


def test_clean_message_has_no_findings():
    assert rules_for("Hello. I can help you with your pension.") == []


def test_plain_words_suggests_a_replacement():
    findings = check_message("m", "I can assist you.", STYLE)
    assert findings[0].rule == "plain-words"
    assert 'use "help"' in findings[0].detail


def test_plain_words_only_matches_whole_words():
    # "assistant" contains "assist" but is a different word.
    assert rules_for("I am your assistant.") == []


def test_tip_is_shown_in_place_of_a_plain_word():
    detail = check_message("m", "It will arrive in due course.", STYLE)[0].detail
    assert "give a date" in detail


def test_long_sentence():
    text = "word " * 30 + "end."
    assert "long-sentence" in rules_for(text)


def test_short_messages_are_not_scored_for_reading_grade():
    assert "reading-grade" not in rules_for("Documentation verification unsuccessful.")


def test_dense_message_fails_reading_grade():
    text = (
        "Verification of identity necessitates submission of documentation "
        "demonstrating residential eligibility requirements accordingly."
    )
    assert "reading-grade" in rules_for(text)


def test_one_question_at_a_time():
    assert "one-question" in rules_for("What do you need? Is it your balance?")
    assert "one-question" not in rules_for("What do you need?")


def test_blame_wording():
    assert "no-blame" in rules_for("Invalid date.")


def test_cold_wording_is_a_warning():
    findings = check_message("m", "Unfortunately it is late.", STYLE)
    assert [(f.rule, f.level) for f in findings] == [("cold-wording", "warning")]


@pytest.mark.parametrize("label,expected", [("click here", True), ("guide to tax", False)])
def test_link_text(label, expected):
    text = f"Read our [{label}](https://example.com)."
    assert ("link-text" in rules_for(text)) is expected


def test_capitals_allow_known_acronyms():
    assert "no-capitals" in rules_for("Do NOT share it.")
    assert "no-capitals" not in rules_for("You can find this on GOV.UK or in the FAQ.")


def test_two_apologies():
    assert "one-apology" in rules_for("Sorry about that. Apologies.")


def test_rules_can_be_switched_off():
    style = {**STYLE, "disabled": ["cold-wording"]}
    assert rules_for("Unfortunately it is late.", style) == []


def test_custom_style_changes_defaults_and_keeps_the_rest():
    style = load_style(EXAMPLES / "house_style.yaml")
    assert style["reading_grade"]["max"] == 8
    assert style["reading_grade"]["min_words"] == 12
    assert style["avoid_words"]["member"] == "customer"
    assert style["avoid_words"]["utilise"] == "use"


def test_examples_before_fails_and_after_passes():
    before = load_messages(EXAMPLES / "messages_before.yaml")
    after = load_messages(EXAMPLES / "messages_after.yaml")
    assert len({f.message_id for f in check_messages(before)}) == 7
    assert check_messages(after) == []
    assert summary(after, []) == "7 messages checked. 0 need work: 0 errors, 0 warnings"


def test_text_file_uses_line_numbers(tmp_path):
    path = tmp_path / "copy.txt"
    path.write_text("Hello.\n\nInvalid date.\n", encoding="utf-8")
    findings = check_messages(load_messages(path))
    assert findings[0].message_id == "line 3"


def test_cli_exit_codes(capsys):
    assert main([str(EXAMPLES / "messages_after.yaml")]) == 0
    assert main([str(EXAMPLES / "messages_before.yaml")]) == 1
    capsys.readouterr()
