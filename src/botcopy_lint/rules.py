"""The style rules. Each rule looks at one message and returns its findings."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .readability import reading_grade, split_sentences, split_words

ERROR, WARNING = "error", "warning"


@dataclass(frozen=True)
class Finding:
    message_id: str
    rule: str
    level: str
    detail: str

    def __str__(self) -> str:
        return f"{self.message_id}: {self.level} [{self.rule}] {self.detail}"


def _has_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"(?<![A-Za-z]){re.escape(phrase)}(?![A-Za-z])", text, flags=re.IGNORECASE) is not None


def rule_reading_grade(text: str, style: dict):
    cfg = style.get("reading_grade") or {}
    if len(split_words(text)) < int(cfg.get("min_words", 12)):
        return
    grade = reading_grade(text)
    limit = float(cfg.get("max", 9))
    if grade > limit:
        yield "reading-grade", ERROR, f"Reading grade {grade}. The limit is {limit:g}. Use shorter sentences and words"


def rule_long_sentence(text: str, style: dict):
    limit = int((style.get("sentence_words") or {}).get("max", 25))
    for sentence in split_sentences(text):
        count = len(split_words(sentence))
        if count > limit:
            start = " ".join(sentence.split()[:6])
            yield "long-sentence", ERROR, f'{count} words in one sentence, limit {limit}: "{start}..."'


def rule_long_message(text: str, style: dict):
    limit = int((style.get("message_words") or {}).get("max", 60))
    count = len(split_words(text))
    if count > limit:
        yield "long-message", WARNING, f"{count} words. Aim for {limit} or fewer, or split into two messages"


def rule_one_question(text: str, style: dict):
    limit = int((style.get("questions") or {}).get("max", 1))
    count = text.count("?")
    if count > limit:
        yield "one-question", ERROR, f"{count} questions in one message. Ask one thing at a time"


def rule_avoid_words(text: str, style: dict):
    for word, plain in (style.get("avoid_words") or {}).items():
        if _has_phrase(text, str(word)):
            if not plain:
                advice = "rewrite without it"
            elif str(plain).startswith("tip:"):
                advice = str(plain)[4:].strip()
            else:
                advice = f'use "{plain}"'
            yield "plain-words", ERROR, f'"{word}": {advice}'


def rule_blame(text: str, style: dict):
    for phrase in style.get("blame_phrases") or []:
        if _has_phrase(text, str(phrase)):
            yield "no-blame", ERROR, f'"{phrase}" blames the user. Say what to do next instead'


def rule_cold(text: str, style: dict):
    for phrase in style.get("cold_phrases") or []:
        if _has_phrase(text, str(phrase)):
            yield "cold-wording", WARNING, f'"{phrase}" can read as cold or dismissive'


def rule_vague_link(text: str, style: dict):
    # Markdown links: [link text](address)
    vague = {str(v).lower() for v in style.get("vague_links") or []}
    for label in re.findall(r"\[([^\]]+)\]\([^)]+\)", text):
        if label.strip().lower() in vague:
            yield "link-text", ERROR, f'Link text "{label}" does not say where the link goes'


def rule_shouting(text: str, style: dict):
    allowed = {str(a).upper() for a in style.get("allowed_capitals") or []}
    shouted = []
    for word in re.findall(r"\b[A-Z]{3,}\b", text):
        if word not in allowed and word not in shouted:
            shouted.append(word)
    if shouted:
        yield "no-capitals", ERROR, f"Words in capitals are harder to read and feel like shouting: {', '.join(shouted)}"


def rule_exclamation(text: str, style: dict):
    limit = int((style.get("exclamation_marks") or {}).get("max", 0))
    count = text.count("!")
    if count > limit:
        yield "exclamation-marks", WARNING, f"{count} exclamation marks, limit {limit}"


def rule_double_apology(text: str, style: dict):
    count = len(re.findall(r"\b(?:sorry|apologi[sz]e|apologies)\b", text, flags=re.IGNORECASE))
    if count > 1:
        yield "one-apology", WARNING, f"{count} apologies in one message. One is enough"


RULES = [
    rule_reading_grade,
    rule_long_sentence,
    rule_long_message,
    rule_one_question,
    rule_avoid_words,
    rule_blame,
    rule_cold,
    rule_vague_link,
    rule_shouting,
    rule_exclamation,
    rule_double_apology,
]


def check_message(message_id: str, text: str, style: dict) -> list[Finding]:
    disabled = set(style.get("disabled") or [])
    findings = []
    for rule in RULES:
        for name, level, detail in rule(text, style):
            if name not in disabled:
                findings.append(Finding(message_id, name, level, detail))
    return findings
