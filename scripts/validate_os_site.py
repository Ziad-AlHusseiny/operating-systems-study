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


def _independent_checks(
    payloads: dict,
    config: dict | None = None,
    manifest: dict | None = None,
    extraction: dict | None = None,
) -> tuple[list[str], Counter, int]:
    """Recompute input compatibility and page totals without builder output."""
    config = _read(ROOT / "input" / "project-config.json") if config is None else config
    manifest = _read(ROOT / "content" / "source-manifest.json") if manifest is None else manifest
    extraction = _read(ROOT / "extraction" / "os-pages.json") if extraction is None else extraction
    course = payloads.get("course") if isinstance(payloads, dict) else None
    course = course if isinstance(course, dict) else {}
    errors: list[str] = []
    if not isinstance(config, dict):
        return ["project config must be an object"], Counter(), 0
    expected_config_keys = {"version", "project", "contentPolicy", "questionGeneration", "exam", "deployment"}
    if set(config) != expected_config_keys or config.get("version") != 1:
        errors.append("project config has an invalid root contract")
    project = config.get("project", {})
    policy = config.get("contentPolicy", {})
    generation = config.get("questionGeneration", {})
    exam = config.get("exam", {})
    deployment = config.get("deployment", {})
    policy_mode = policy.get("mode") if isinstance(policy, dict) else None
    if not isinstance(project, dict) or set(project) != {"title", "shortTitle", "slug", "description", "brandInitials", "sourceLanguage", "studyLanguage"} or not all(isinstance(value, str) and value.strip() for value in project.values()) or project.get("sourceLanguage") != "en" or project.get("studyLanguage") != "ar":
        errors.append("project config project metadata is invalid")
    if not isinstance(policy, dict) or set(policy) != {"mode", "allowOutsideSources", "generatedQuestionsRequireHumanReviewForExam"} or policy.get("mode") not in {"source-only", "source-plus-generated", "generated-only"} or not isinstance(policy.get("allowOutsideSources"), bool) or not isinstance(policy.get("generatedQuestionsRequireHumanReviewForExam"), bool):
        errors.append("project config policy is invalid")
    distributions_ok = (
        isinstance(generation, dict)
        and isinstance(generation.get("difficultyPercent"), dict)
        and isinstance(generation.get("bloomPercent"), dict)
        and set(generation["difficultyPercent"]) == {"easy", "medium", "hard"}
        and set(generation["bloomPercent"]) == {"remember", "apply", "analyze"}
        and all(isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 100 for distribution in (generation["difficultyPercent"], generation["bloomPercent"]) for value in distribution.values())
        and sum(generation["difficultyPercent"].values()) == 100
        and sum(generation["bloomPercent"].values()) == 100
    )
    generation_counts_ok = (
        isinstance(generation, dict)
        and all(isinstance(generation.get(key), int) and not isinstance(generation.get(key), bool) and generation[key] >= 0 for key in ("mcqPerLesson", "trueFalsePerLesson"))
        and (
            (policy_mode == "source-only" and generation.get("mcqPerLesson") == generation.get("trueFalsePerLesson") == 0)
            or (policy_mode in {"source-plus-generated", "generated-only"} and generation.get("mcqPerLesson", 0) + generation.get("trueFalsePerLesson", 0) > 0)
        )
    )
    if not isinstance(generation, dict) or set(generation) != {"mcqPerLesson", "trueFalsePerLesson", "difficultyPercent", "bloomPercent"} or not generation_counts_ok or not distributions_ok:
        errors.append("project config question generation is invalid")
    if not isinstance(exam, dict) or set(exam) != {"defaultCount", "defaultMinutes"} or not all(isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in exam.values()):
        errors.append("project config exam is invalid")
    if not isinstance(deployment, dict) or set(deployment) != {"provider", "repository", "branch", "publicUrl"} or deployment.get("provider") != "github-pages" or not isinstance(deployment.get("repository"), str) or deployment["repository"].count("/") != 1 or not all(part.strip() for part in deployment["repository"].split("/")) or not isinstance(deployment.get("branch"), str) or not deployment["branch"].strip() or not isinstance(deployment.get("publicUrl"), str) or not deployment["publicUrl"].startswith(("http://", "https://")):
        errors.append("project config deployment is invalid")
    if course.get("projectId") != (project.get("slug") if isinstance(project, dict) else None):
        errors.append("public course project ID differs from project config")
    if course.get("project") != project or course.get("contentPolicy") != policy or course.get("questionGeneration") != generation or course.get("exam") != exam:
        errors.append("public course policy/configuration differs from project config")
    if not isinstance(manifest, dict) or set(manifest) != {"version", "sources"} or manifest.get("version") != "1.0" or not isinstance(manifest.get("sources"), list):
        errors.append("source manifest has an invalid root contract")
        manifest_sources_list = []
    else:
        manifest_sources_list = manifest["sources"]
    source_keys = {"id", "fileName", "collection", "label", "format", "checksum", "pages", "status", "locations"}
    for source in manifest_sources_list:
        if not isinstance(source, dict) or set(source) != source_keys or not isinstance(source.get("id"), str) or not source["id"].strip() or not isinstance(source.get("fileName"), str) or not source["fileName"].strip() or not isinstance(source.get("pages"), int) or isinstance(source.get("pages"), bool) or source["pages"] < 1 or not isinstance(source.get("locations"), list):
            errors.append("source manifest has a malformed source record")
            break
    manifest_ids = [source.get("id") for source in manifest_sources_list if isinstance(source, dict) and isinstance(source.get("id"), str)]
    if len(manifest_ids) != len(set(manifest_ids)):
        errors.append("source manifest has duplicate source IDs")
    if course.get("sources") != manifest_sources_list:
        errors.append("public course sources differ from source manifest")
    if not isinstance(extraction, dict) or set(extraction) != {"version", "course", "generatedAtPolicy", "sources", "pages"} or extraction.get("version") != "1.0" or extraction.get("course") != "Operating Systems" or extraction.get("generatedAtPolicy") != "deterministic-no-timestamp" or not isinstance(extraction.get("sources"), list) or not isinstance(extraction.get("pages"), list):
        errors.append("extraction has an invalid root contract")
        extraction_sources_list, pages = [], []
    else:
        extraction_sources_list, pages = extraction["sources"], extraction["pages"]
    extraction_source_keys = {"id", "file", "chapter", "part", "pages", "sha256", "title"}
    for source in extraction_sources_list:
        if not isinstance(source, dict) or set(source) != extraction_source_keys or not isinstance(source.get("id"), str) or not isinstance(source.get("file"), str) or not isinstance(source.get("pages"), int) or isinstance(source.get("pages"), bool) or source["pages"] < 1:
            errors.append("extraction has a malformed source record")
            break
    extraction_ids = [source.get("id") for source in extraction_sources_list if isinstance(source, dict) and isinstance(source.get("id"), str)]
    if len(extraction_ids) != len(set(extraction_ids)):
        errors.append("extraction has duplicate source IDs")
    page_keys = {"sourceId", "page", "text", "characterCount", "classification", "classificationEvidence"}
    valid_classes = {"cover", "divider", "teaching", "closing"}
    page_id_pairs: list[tuple[str, int]] = []
    for page in pages:
        if not isinstance(page, dict) or set(page) != page_keys or not isinstance(page.get("sourceId"), str) or not isinstance(page.get("page"), int) or isinstance(page.get("page"), bool) or not isinstance(page.get("text"), str) or not isinstance(page.get("characterCount"), int) or isinstance(page.get("characterCount"), bool) or page.get("classification") not in valid_classes or not isinstance(page.get("classificationEvidence"), dict):
            errors.append("extraction has a malformed page record")
            continue
        page_id_pairs.append((page["sourceId"], page["page"]))
    if len(page_id_pairs) != len(set(page_id_pairs)):
        errors.append("extraction has duplicate page IDs")
    page_counts = Counter(page.get("classification") for page in pages if isinstance(page, dict) and page.get("classification") in valid_classes)
    if course.get("coverage", {}).get("totalPages") != len(pages) or course.get("coverage", {}).get("classificationCounts") != dict(sorted(page_counts.items())):
        errors.append("public course coverage differs from extraction totals")
    manifest_sources = {
        source.get("id"): source
        for source in manifest_sources_list
        if isinstance(source, dict) and isinstance(source.get("id"), str) and isinstance(source.get("pages"), int) and not isinstance(source.get("pages"), bool)
    }
    extraction_sources = {
        source.get("id"): source
        for source in extraction_sources_list
        if isinstance(source, dict) and isinstance(source.get("id"), str) and isinstance(source.get("pages"), int) and not isinstance(source.get("pages"), bool)
    }
    if set(manifest_sources) != set(extraction_sources) or any(manifest_sources[source_id].get("pages") != extraction_sources[source_id].get("pages") or manifest_sources[source_id].get("fileName") != extraction_sources[source_id].get("file") for source_id in manifest_sources):
        errors.append("manifest and extraction source identity differ")
    if sum(source.get("pages", 0) for source in manifest_sources.values()) != len(pages):
        errors.append("manifest and extraction page totals differ")
    if len(manifest_sources) != 21 or len(pages) != 517 or page_counts != Counter({"cover": 21, "divider": 21, "teaching": 454, "closing": 21}):
        errors.append("source extraction acceptance totals differ")
    expected_pairs = {(source_id, page) for source_id, source in extraction_sources.items() for page in range(1, source.get("pages", 0) + 1)}
    if set(page_id_pairs) != expected_pairs:
        errors.append("extraction page identity or bounds differ")
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
