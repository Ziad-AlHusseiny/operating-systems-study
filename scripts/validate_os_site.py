"""Independently validate checked-in Operating Systems public artifacts."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

try:  # Support both `python scripts/...` and package imports in tests.
    from scripts.build_os_site_data import DATA_PATHS, ROOT, _counts, validate_payloads
except ModuleNotFoundError:  # pragma: no cover - direct CLI import path
    from build_os_site_data import DATA_PATHS, ROOT, _counts, validate_payloads


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _independent_checks(payloads: dict) -> tuple[list[str], Counter, int]:
    """Recompute input compatibility and page totals without builder output."""
    config = _read(ROOT / "input" / "project-config.json")
    manifest = _read(ROOT / "content" / "source-manifest.json")
    extraction = _read(ROOT / "extraction" / "os-pages.json")
    course = payloads["course"]
    errors = []
    if course.get("projectId") != config.get("project", {}).get("slug"):
        errors.append("public course project ID differs from project config")
    if course.get("sources") != manifest.get("sources"):
        errors.append("public course sources differ from source manifest")
    pages = extraction.get("pages", [])
    page_counts = Counter(page.get("classification") for page in pages if isinstance(page, dict))
    if course.get("coverage", {}).get("totalPages") != len(pages) or course.get("coverage", {}).get("classificationCounts") != dict(sorted(page_counts.items())):
        errors.append("public course coverage differs from extraction totals")
    return errors, page_counts, len(pages)


def main() -> int:
    try:
        payloads = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in DATA_PATHS.items()}
    except (OSError, json.JSONDecodeError) as error:
        print(f"could not load public artifacts: {error}", file=sys.stderr)
        return 1
    errors, page_counts, total_pages = _independent_checks(payloads)
    errors.extend(validate_payloads(payloads))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    counts = _counts(payloads)
    print(f"OS public artifacts valid: sources {counts['sources']}; pages {total_pages}; teaching {page_counts['teaching']}; modules {counts['modules']}; lessons {counts['lessons']}; questions {counts['questions']}; explanations {counts['explanations']}; practice {counts['practice']}; mock {counts['mock']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
