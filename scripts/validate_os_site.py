"""Independently validate checked-in Operating Systems public artifacts."""

from __future__ import annotations

import json
import sys

try:  # Support both `python scripts/...` and package imports in tests.
    from scripts.build_os_site_data import DATA_PATHS, _counts, validate_payloads
except ModuleNotFoundError:  # pragma: no cover - direct CLI import path
    from build_os_site_data import DATA_PATHS, _counts, validate_payloads


def main() -> int:
    try:
        payloads = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in DATA_PATHS.items()}
    except (OSError, json.JSONDecodeError) as error:
        print(f"could not load public artifacts: {error}", file=sys.stderr)
        return 1
    errors = validate_payloads(payloads)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    counts = _counts(payloads)
    print(f"OS public artifacts valid: sources {counts['sources']}; pages 517; teaching 454; modules {counts['modules']}; lessons {counts['lessons']}; questions {counts['questions']}; explanations {counts['explanations']}; practice {counts['practice']}; mock {counts['mock']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
