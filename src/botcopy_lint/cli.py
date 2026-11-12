"""Command line entry point."""

from __future__ import annotations

import argparse
import json

from .checker import check_messages, load_messages, load_style, summary
from .rules import ERROR


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="botcopy-lint", description=__doc__)
    parser.add_argument("messages", help="YAML file (name: text) or text file (one message per line)")
    parser.add_argument("--style", help="a YAML style guide that changes the defaults")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = parser.parse_args(argv)

    messages = load_messages(args.messages)
    findings = check_messages(messages, load_style(args.style))

    if args.format == "json":
        print(json.dumps([f.__dict__ for f in findings], indent=2))
    else:
        last = None
        for finding in findings:
            if last is not None and finding.message_id != last:
                print()
            last = finding.message_id
            print(finding)
        if findings:
            print()
        print(summary(messages, findings))

    errors = any(f.level == ERROR for f in findings)
    return 1 if errors or (args.strict and findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
