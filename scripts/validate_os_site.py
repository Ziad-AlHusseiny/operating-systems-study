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
    expected_config_keys = {"version", "project", "contentPolicy", "questionGeneration", "exam", "deployment"}
    if set(config) != expected_config_keys or config.get("version") != 1:
        errors.append("project config has an invalid root contract")
    project = config.get("project", {})
    policy = config.get("contentPolicy", {})
    generation = config.get("questionGeneration", {})
    exam = config.get("exam", {})
    deployment = config.get("deployment", {})
    if set(project) != {"title", "shortTitle", "slug", "description", "brandInitials", "sourceLanguage", "studyLanguage"} or not all(isinstance(value, str) and value.strip() for value in project.values()):
        errors.append("project config project metadata is invalid")
    if set(policy) != {"mode", "allowOutsideSources", "generatedQuestionsRequireHumanReviewForExam"} or policy.get("mode") not in {"source-only", "source-plus-generated", "generated-only"} or not isinstance(policy.get("allowOutsideSources"), bool) or not isinstance(policy.get("generatedQuestionsRequireHumanReviewForExam"), bool):
        errors.append("project config policy is invalid")
    if set(generation) != {"mcqPerLesson", "trueFalsePerLesson", "difficultyPercent", "bloomPercent"} or not all(isinstance(generation.get(key), int) and generation[key] >= 0 for key in ("mcqPerLesson", "trueFalsePerLesson")) or sum(generation.get("difficultyPercent", {}).values()) != 100 or sum(generation.get("bloomPercent", {}).values()) != 100:
        errors.append("project config question generation is invalid")
    if set(exam) != {"defaultCount", "defaultMinutes"} or not all(isinstance(value, int) and value > 0 for value in exam.values()):
        errors.append("project config exam is invalid")
    if set(deployment) != {"provider", "repository", "branch", "publicUrl"} or deployment.get("provider") != "github-pages" or not isinstance(deployment.get("publicUrl"), str) or not deployment["publicUrl"].startswith(("http://", "https://")):
        errors.append("project config deployment is invalid")
    if course.get("projectId") != config.get("project", {}).get("slug"):
        errors.append("public course project ID differs from project config")
    if course.get("sources") != manifest.get("sources"):
        errors.append("public course sources differ from source manifest")
    pages = extraction.get("pages", [])
    page_counts = Counter(page.get("classification") for page in pages if isinstance(page, dict))
    if course.get("coverage", {}).get("totalPages") != len(pages) or course.get("coverage", {}).get("classificationCounts") != dict(sorted(page_counts.items())):
        errors.append("public course coverage differs from extraction totals")
    manifest_sources = {source.get("id"): source for source in manifest.get("sources", []) if isinstance(source, dict)}
    extraction_sources = {source.get("id"): source for source in extraction.get("sources", []) if isinstance(source, dict)}
    if set(manifest_sources) != set(extraction_sources) or any(manifest_sources[source_id].get("pages") != extraction_sources[source_id].get("pages") or manifest_sources[source_id].get("fileName") != extraction_sources[source_id].get("file") for source_id in manifest_sources):
        errors.append("manifest and extraction source identity differ")
    if sum(source.get("pages", 0) for source in manifest_sources.values()) != len(pages):
        errors.append("manifest and extraction page totals differ")
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
