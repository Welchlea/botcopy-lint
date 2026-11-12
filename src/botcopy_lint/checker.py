"""Load messages and a style guide, then check every message."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import yaml

from .rules import ERROR, Finding, check_message


def default_style() -> dict:
    text = resources.files("botcopy_lint").joinpath("default_style.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(text)


def load_style(path: str | Path | None = None) -> dict:
    """Start from the default style. Anything in the custom file replaces it."""
    style = default_style()
    if path:
        with open(path, encoding="utf-8") as handle:
            custom = yaml.safe_load(handle) or {}
        for key, value in custom.items():
            if isinstance(value, dict) and isinstance(style.get(key), dict):
                style[key] = {**style[key], **value}
            else:
                style[key] = value
    return style


def load_messages(path: str | Path) -> dict[str, str]:
    """Read messages from YAML (name: text) or a text file (one per line)."""
    path = Path(path)
    if path.suffix in {".yaml", ".yml"}:
        with open(path, encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        data = data.get("messages", data)
        return {str(k): " ".join(str(v).split()) for k, v in data.items()}
    lines = path.read_text(encoding="utf-8").splitlines()
    return {f"line {n}": line.strip() for n, line in enumerate(lines, start=1) if line.strip()}


def check_messages(messages: dict[str, str], style: dict | None = None) -> list[Finding]:
    style = style or default_style()
    findings: list[Finding] = []
    for message_id, text in messages.items():
        findings.extend(check_message(message_id, text, style))
    return findings


def summary(messages: dict[str, str], findings: list[Finding]) -> str:
    errors = sum(1 for f in findings if f.level == ERROR)
    warnings = len(findings) - errors
    flagged = len({f.message_id for f in findings})
    return f"{len(messages)} messages checked. {flagged} need work: {errors} errors, {warnings} warnings"
