"""Build and validate deterministic public payloads for the OS study site."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
PART_PATHS = (
    ROOT / "content" / "os" / "ch01-ch02.json",
    ROOT / "content" / "os" / "ch03-ch05.json",
    ROOT / "content" / "os" / "ch06-ch08-ch09.json",
)
DATA_PATHS = {
    "course": ROOT / "study-website" / "data" / "course.json",
    "lessons": ROOT / "study-website" / "data" / "lessons.json",
    "questions": ROOT / "study-website" / "data" / "questions.json",
    "explanations-ar": ROOT / "study-website" / "data" / "explanations-ar.json",
}
REPORT_PATHS = {
    "coverage": ROOT / "reports" / "CONTENT_COVERAGE_REPORT.md",
    "quality": ROOT / "reports" / "QUESTION_QUALITY_REPORT.md",
}
ROOT_KEYS = {
    "course": {"schemaVersion", "projectId", "version", "project", "modules", "objectives", "sources", "contentPolicy", "questionGeneration", "exam", "coverage"},
    "lessons": {"schemaVersion", "projectId", "lessons"},
    "questions": {"schemaVersion", "projectId", "questions"},
    "explanations-ar": {"schemaVersion", "projectId", "explanations"},
}
MODULE_KEYS = {"id", "title", "order", "objectiveIds", "sourceRefs"}
OBJECTIVE_KEYS = {"id", "moduleId", "text", "order", "sourceRefs"}
LESSON_KEYS = {"id", "moduleId", "objectiveIds", "title", "contentVersion", "materialSectionIds", "learningObjectives", "materialSections", "needsReview", "reviewNotes", "review"}
SECTION_KEYS = {"id", "lessonId", "order", "title", "origin", "label", "generatedStudyGuidance", "summaries", "terms", "examples", "mistakes", "examTips", "recaps", "sourceRefs", "linkedQuestionIds", "contentVersion", "needsReview", "reviewNotes"}
BASE_QUESTION_KEYS = {"id", "origin", "type", "prompt", "topic", "difficulty", "bloomLevel", "cognitiveLevel", "learningObjectiveId", "sourceRefs", "generationMethod", "generatedExplanationId", "provenance", "contentVersion", "qualityState", "reviewState", "duplicateComparison", "duplicateDisposition", "needsReview", "reviewNotes", "review", "correctAnswer", "rationale", "evidenceMap"}
MCQ_KEYS = BASE_QUESTION_KEYS | {"options", "distractorRationales"}
TF_KEYS = BASE_QUESTION_KEYS | {"correctedStatement"}
EXPLANATION_KEYS = {"id", "questionId", "language", "generatedStudyGuidance", "translation", "explanation", "body", "note", "contentVersion", "sourceRefs", "needsReview", "reviewNotes", "review"}
SOURCE_REF_KEYS = {"sourceId", "locationType", "location", "context", "confidence"}
ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
SEMVER_RE = re.compile(r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
PROHIBITED_GENERATED_CLAIMS = re.compile(r"\b(?:official exam question|official question|from the exam|past[- ]paper question|certified|guaranteed to appear)\b", re.IGNORECASE)
PROVENANCE_KEYS = {"sourceRefs", "modelVersion", "promptVersion"}
DUPLICATE_KEYS = {"algorithmVersion", "normalizedPrompt", "candidateIds", "matchClass"}
EVIDENCE_KEYS = {"claimId", "target", "sourceRefs", "support"}
VALIDATED_REVIEW_KEYS = {"status"}
HUMAN_REVIEW_KEYS = {"status", "approval"}
APPROVAL_KEYS = {"reviewedRecordId", "reviewedContentVersion", "status", "decision", "reviewer", "reviewedAt", "reason", "notes"}


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_content_parts() -> list[dict]:
    """Return the canonical OS authoring parts in their fixed release order."""
    return [_read_json(path) for path in PART_PATHS]


def _inputs() -> tuple[dict, dict, dict]:
    return (
        _read_json(ROOT / "input" / "project-config.json"),
        _read_json(ROOT / "content" / "source-manifest.json"),
        _read_json(ROOT / "extraction" / "os-pages.json"),
    )


def _lesson_sort_key(lesson: dict, module_order: dict[str, int]) -> tuple[int, str]:
    return (module_order[lesson["moduleId"]], lesson["id"])


def _claim(body: str, source_refs: list[dict]) -> dict:
    return {"body": body, "sourceRefs": copy.deepcopy(source_refs)}


def _claims(values: list[Any], source_refs: list[dict]) -> list[dict]:
    claims = []
    for value in values:
        if isinstance(value, str) and value.strip():
            claims.append(_claim(value, source_refs))
        elif isinstance(value, dict) and _non_empty(value.get("body")):
            claims.append(_claim(value["body"], value.get("sourceRefs", source_refs)))
    return claims


def _compile_section(section: dict, lesson: dict) -> dict:
    refs = copy.deepcopy(section["sourceRefs"])
    summaries: list[dict] = []
    if section["summary"].strip():
        summaries.append(_claim(section["summary"], refs))
    summaries.extend(_claim(text, refs) for text in section["explanation"] if text.strip())
    return {
        "id": section["id"],
        "lessonId": lesson["id"],
        "order": section["order"],
        "title": section["title"],
        "origin": section["origin"],
        "label": section["label"],
        "generatedStudyGuidance": section["generatedStudyGuidance"],
        "summaries": summaries,
        "terms": copy.deepcopy(section["keyTerms"]),
        "examples": copy.deepcopy(section["workedExamples"]),
        "mistakes": copy.deepcopy(section["commonMistakes"]),
        "examTips": _claims(section["examTips"], refs),
        "recaps": _claims(section["recap"], refs),
        "sourceRefs": refs,
        "linkedQuestionIds": copy.deepcopy(section["linkedQuestionIds"]),
        "contentVersion": lesson["contentVersion"],
        "needsReview": section["needsReview"],
        "reviewNotes": section["reviewNotes"],
    }


def build_payloads(parts: list[dict]) -> dict[str, dict]:
    """Compile canonical authoring records into deterministic browser JSON."""
    config, manifest, extraction = _inputs()
    modules = [copy.deepcopy(record) for part in parts for record in part["modules"]]
    modules.sort(key=lambda record: (record["order"], record["id"]))
    module_order = {record["id"]: record["order"] for record in modules}
    source_lessons = [record for part in parts for record in part["lessons"]]
    source_lessons.sort(key=lambda record: _lesson_sort_key(record, module_order))
    objectives = [copy.deepcopy(objective) for lesson in source_lessons for objective in lesson["learningObjectives"]]
    objectives.sort(key=lambda record: (module_order[record["moduleId"]], record["order"], record["id"]))
    lessons = []
    for lesson in source_lessons:
        compiled = {key: copy.deepcopy(lesson[key]) for key in LESSON_KEYS - {"materialSections"}}
        compiled["materialSections"] = [_compile_section(section, lesson) for section in sorted(lesson["materialSections"], key=lambda item: item["order"])]
        lessons.append(compiled)
    questions = [copy.deepcopy(question) for part in parts for question in part["questions"]]
    questions.sort(key=lambda record: record["id"])
    explanations = [copy.deepcopy(explanation) for part in parts for explanation in part["explanations"]]
    explanations.sort(key=lambda record: record["id"])
    pages = extraction["pages"]
    teaching_pages = sorted(f"{page['sourceId']}:{page['page']}" for page in pages if page["classification"] == "teaching")
    referenced = sorted(_reference_pages(lessons))
    coverage = {
        "totalPages": len(pages),
        "teachingPages": len(teaching_pages),
        "classificationCounts": dict(sorted(Counter(page["classification"] for page in pages).items())),
        "teachingPageIds": teaching_pages,
        "referencedTeachingPages": referenced,
    }
    course = {
        "schemaVersion": "1",
        "projectId": config["project"]["slug"],
        "version": "1.0.0",
        "project": copy.deepcopy(config["project"]),
        "modules": modules,
        "objectives": objectives,
        "sources": copy.deepcopy(manifest["sources"]),
        "contentPolicy": copy.deepcopy(config["contentPolicy"]),
        "questionGeneration": copy.deepcopy(config["questionGeneration"]),
        "exam": copy.deepcopy(config["exam"]),
        "coverage": coverage,
    }
    return {
        "course": course,
        "lessons": {"schemaVersion": "1", "projectId": course["projectId"], "lessons": lessons},
        "questions": {"schemaVersion": "1", "projectId": course["projectId"], "questions": questions},
        "explanations-ar": {"schemaVersion": "1", "projectId": course["projectId"], "explanations": explanations},
    }


def _normalize_prompt(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    normalized = re.sub(r"\s+", " ", normalized).casefold()
    return "".join(character for character in normalized if not unicodedata.category(character).startswith("P"))


def _exact_keys(record: Any, allowed: set[str], label: str, errors: list[str]) -> None:
    if not isinstance(record, dict):
        errors.append(f"{label} must be an object")
        return
    unexpected = sorted(set(record) - allowed)
    missing = sorted(allowed - set(record))
    if unexpected:
        errors.append(f"{label} has unexpected keys: {', '.join(unexpected)}")
    if missing:
        errors.append(f"{label} is missing keys: {', '.join(missing)}")


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _list(value: Any, label: str, errors: list[str]) -> list:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return []
    return value


def _is_json_safe(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return value == value and value not in {float("inf"), float("-inf")}
    if isinstance(value, list):
        return all(_is_json_safe(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _is_json_safe(item) for key, item in value.items())
    return False


def _check_json_safe(value: Any, label: str, errors: list[str]) -> None:
    if not _is_json_safe(value):
        errors.append(f"{label} contains a non-JSON value")


def _valid_content_version(value: Any) -> bool:
    return _non_empty(value) and bool(SEMVER_RE.fullmatch(value))


def _question_lesson_id(question_id: str) -> str | None:
    match = re.fullmatch(r"gq-(os-ch\d\d-part\d)-\d{3}", question_id)
    return f"lesson-{match.group(1)}" if match else None


def _is_utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None and datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() == timezone.utc.utcoffset(None)
    except ValueError:
        return False


def _review_valid(record: dict) -> bool:
    review = record.get("review")
    status = review.get("status") if isinstance(review, dict) else None
    if status == "validated":
        return set(review) == VALIDATED_REVIEW_KEYS and record.get("needsReview") is False and ("qualityState" not in record or (record.get("qualityState") == "validated" and record.get("reviewState") == "unreviewed"))
    if status != "human-reviewed" or set(review) != HUMAN_REVIEW_KEYS or record.get("needsReview") is not False or ("qualityState" in record and (record.get("qualityState") != "approved" or record.get("reviewState") != "approved")):
        return False
    approval = review.get("approval")
    return isinstance(approval, dict) and set(approval) == APPROVAL_KEYS and approval.get("reviewedRecordId") == record.get("id") and approval.get("reviewedContentVersion") == record.get("contentVersion") and approval.get("status") == "completed" and approval.get("decision") == "approved" and _non_empty(approval.get("reviewer")) and _is_utc_timestamp(approval.get("reviewedAt")) and _non_empty(approval.get("reason")) and _non_empty(approval.get("notes"))


def _answer_and_evidence_valid(question: dict) -> bool:
    if not _non_empty(question.get("rationale")) or not isinstance(question.get("sourceRefs"), list) or not question["sourceRefs"]:
        return False
    if question.get("type") == "mcq":
        options, answer, rationales = question.get("options"), question.get("correctAnswer"), question.get("distractorRationales")
        if not isinstance(options, list) or len(options) != 4 or len(set(options)) != 4 or not all(_non_empty(item) for item in options) or isinstance(answer, bool) or not isinstance(answer, int) or not 0 <= answer < 4 or not isinstance(rationales, list) or len(rationales) != 4 or not all(_non_empty(item) for item in rationales):
            return False
    elif question.get("type") == "true-false":
        if not isinstance(question.get("correctAnswer"), bool) or (question["correctAnswer"] is False and not _non_empty(question.get("correctedStatement"))) or (question["correctAnswer"] is True and question.get("correctedStatement") is not None):
            return False
    else:
        return False
    evidence = question.get("evidenceMap")
    return isinstance(evidence, list) and bool(evidence) and all(isinstance(entry, dict) and set(entry) == EVIDENCE_KEYS and _non_empty(entry.get("claimId")) and entry.get("support") in {"direct", "derived"} and isinstance(entry.get("sourceRefs"), list) and bool(entry["sourceRefs"]) for entry in evidence)


def _source_index(course: dict, extraction: dict) -> tuple[dict[str, dict], dict[tuple[str, int], str]]:
    sources = {source["id"]: source for source in course.get("sources", []) if isinstance(source, dict) and isinstance(source.get("id"), str)}
    classifications = {(page["sourceId"], page["page"]): page["classification"] for page in extraction.get("pages", []) if isinstance(page, dict) and isinstance(page.get("sourceId"), str) and isinstance(page.get("page"), int) and isinstance(page.get("classification"), str)}
    return sources, classifications


def _validate_refs(refs: Any, sources: dict[str, dict], classifications: dict[tuple[str, int], str], label: str, errors: list[str], non_teaching: set[str] | None = None) -> None:
    if not isinstance(refs, list) or not refs:
        errors.append(f"{label} needs non-empty source references")
        return
    for index, ref in enumerate(refs):
        if not isinstance(ref, dict):
            errors.append(f"{label} sourceRef {index} must be an object")
        elif set(ref) - SOURCE_REF_KEYS:
            errors.append(f"{label} sourceRef {index} has unexpected keys: {', '.join(sorted(set(ref) - SOURCE_REF_KEYS))}")
        elif not {"sourceId", "locationType", "location"}.issubset(ref):
            errors.append(f"{label} sourceRef {index} is missing a required key")
        if not isinstance(ref, dict):
            continue
        source = sources.get(ref.get("sourceId"))
        if source is None:
            errors.append(f"{label} has unknown source {ref.get('sourceId')}")
            continue
        if ref.get("locationType") != "page" or not isinstance(ref.get("location"), int):
            errors.append(f"{label} has incompatible source location")
            continue
        page = ref["location"]
        if page < 1 or page > source.get("pages", 0):
            errors.append(f"{label} has page bounds error")
            continue
        classification = classifications.get((ref["sourceId"], page))
        if classification is None:
            errors.append(f"{label} points to an unextracted page")
        elif non_teaching is not None and classification != "teaching":
            non_teaching.add(f"{ref['sourceId']}:{page}")


def _reference_pages(lessons: Iterable[dict]) -> set[str]:
    pages: set[str] = set()
    for lesson in lessons:
        for section in lesson["materialSections"]:
            for ref in section["sourceRefs"]:
                if ref.get("locationType") == "page" and isinstance(ref.get("location"), int):
                    pages.add(f"{ref['sourceId']}:{ref['location']}")
    return pages


def eligible_question_ids(payloads: dict[str, dict], mode: str) -> list[str]:
    questions = payloads["questions"]["questions"]
    policy = payloads["course"]["contentPolicy"]
    eligible = [question for question in questions if isinstance(question, dict) and _review_valid(question) and _answer_and_evidence_valid(question) and question.get("duplicateDisposition") == "retain"]
    if mode == "practice":
        return [question["id"] for question in eligible]
    if mode == "mock-exam":
        if policy["generatedQuestionsRequireHumanReviewForExam"]:
            return [question["id"] for question in eligible if question.get("review", {}).get("status") == "human-reviewed"]
        return [question["id"] for question in eligible]
    raise ValueError(f"unknown eligibility mode: {mode}")


def validate_payloads(payloads: dict[str, dict]) -> list[str]:
    """Return every contract error without modifying public payload data."""
    errors: list[str] = []
    config, _, extraction = _inputs()
    if set(payloads) != set(ROOT_KEYS):
        return ["payload set must contain course, lessons, questions, and explanations-ar"]
    for name, allowed in ROOT_KEYS.items():
        _exact_keys(payloads[name], allowed, name, errors)
        _check_json_safe(payloads[name], name, errors)
    course = payloads["course"]
    if not isinstance(course, dict):
        return errors
    if course.get("project") != config.get("project"):
        errors.append("course project metadata is incompatible with project configuration")
    for key in ("contentPolicy", "questionGeneration", "exam"):
        if course.get(key) != config.get(key):
            errors.append(f"course {key} is incompatible with project configuration")
    if course.get("sources") != _inputs()[1].get("sources"):
        errors.append("course sources are incompatible with source manifest")
    project_id = course.get("projectId")
    if project_id != config["project"]["slug"]:
        errors.append("course project ID does not match project configuration")
    for name in ("lessons", "questions", "explanations-ar"):
        if payloads[name].get("projectId") != project_id:
            errors.append(f"{name} project ID does not match course")
    sources, classifications = _source_index(course, extraction)
    public_sources = _list(course.get("sources"), "sources", errors)
    if len(sources) != len(public_sources):
        errors.append("duplicate source ID")
    modules = _list(course.get("modules"), "modules", errors)
    objectives = _list(course.get("objectives"), "objectives", errors)
    lessons = _list(payloads["lessons"].get("lessons"), "lessons", errors)
    questions = _list(payloads["questions"].get("questions"), "questions", errors)
    explanations = _list(payloads["explanations-ar"].get("explanations"), "Arabic explanations", errors)
    if len(modules) != 7:
        errors.append("module total must be exactly 7")
    if len(lessons) != 21:
        errors.append("lesson total must be exactly 21")
    if len(questions) != 210:
        errors.append("question total must be exactly 210")
    if len(explanations) != 210:
        errors.append("Arabic explanation total must be exactly 210")
    ids: set[str] = set()
    for label, records, keys, prefix in (("module", modules, MODULE_KEYS, "module-"), ("objective", objectives, OBJECTIVE_KEYS, "objective-"), ("lesson", lessons, LESSON_KEYS, "lesson-")):
        if not isinstance(records, list):
            errors.append(f"{label}s must be an array")
            continue
        for record in records:
            _exact_keys(record, keys, label, errors)
            record_id = record.get("id") if isinstance(record, dict) else None
            if not isinstance(record_id, str) or not record_id.startswith(prefix):
                errors.append(f"invalid {label} id")
            elif record_id in ids:
                errors.append(f"duplicate id {record_id}")
            else:
                ids.add(record_id)
    if all(isinstance(module, dict) and isinstance(module.get("order"), int) for module in modules) and [module.get("order") for module in modules] != sorted(module.get("order") for module in modules):
        errors.append("modules are not ordered")
    module_ids = {module.get("id") for module in modules if isinstance(module, dict)}
    objective_ids = {objective.get("id") for objective in objectives if isinstance(objective, dict)}
    objectives_by_module = Counter(objective.get("moduleId") for objective in objectives if isinstance(objective, dict))
    for module in modules:
        if not isinstance(module, dict):
            continue
        if not _non_empty(module.get("title")) or not isinstance(module.get("order"), int):
            errors.append(f"module {module.get('id')} has invalid fields")
        _validate_refs(module.get("sourceRefs"), sources, classifications, f"module {module.get('id')}", errors)
        module_objectives = module.get("objectiveIds")
        if not isinstance(module_objectives, list):
            errors.append(f"module {module.get('id')} objective IDs must be an array")
        elif len(module_objectives) != len(set(module_objectives)):
            errors.append(f"module {module.get('id')} has duplicate objective IDs")
        elif any(objective_id not in objective_ids for objective_id in module_objectives) or any(next((objective for objective in objectives if isinstance(objective, dict) and objective.get("id") == objective_id), {}).get("moduleId") != module.get("id") for objective_id in module_objectives):
            errors.append(f"module objective linkage is unresolved for {module.get('id')}")
        elif len(module_objectives) != objectives_by_module[module.get("id")]:
            errors.append(f"module objective linkage is incomplete for {module.get('id')}")
    for objective in objectives:
        if not isinstance(objective, dict):
            continue
        if objective.get("moduleId") not in module_ids or not _non_empty(objective.get("text")):
            errors.append(f"objective {objective.get('id')} has unresolved module or empty text")
        _validate_refs(objective.get("sourceRefs"), sources, classifications, f"objective {objective.get('id')}", errors)
    lesson_order = {lesson.get("id"): (next((module.get("order") for module in modules if isinstance(module, dict) and module.get("id") == lesson.get("moduleId")), 999), lesson.get("id")) for lesson in lessons if isinstance(lesson, dict)}
    if all(isinstance(lesson, dict) for lesson in lessons) and [lesson.get("id") for lesson in lessons] != sorted(lesson_order, key=lesson_order.get):
        errors.append("lessons are not ordered")
    question_ids = {question.get("id") for question in questions if isinstance(question, dict)}
    non_teaching: set[str] = set()
    section_ids: set[str] = set()
    for lesson in lessons:
        if not isinstance(lesson, dict):
            continue
        if lesson.get("moduleId") not in module_ids or not _non_empty(lesson.get("title")):
            errors.append(f"lesson {lesson.get('id')} has unresolved module or empty title")
        if not _valid_content_version(lesson.get("contentVersion")):
            errors.append(f"lesson {lesson.get('id')} has invalid content version")
        lesson_review = lesson.get("review")
        _exact_keys(lesson_review, VALIDATED_REVIEW_KEYS if isinstance(lesson_review, dict) and lesson_review.get("status") == "validated" else HUMAN_REVIEW_KEYS if isinstance(lesson_review, dict) and lesson_review.get("status") == "human-reviewed" else set(), f"lesson {lesson.get('id')} review", errors)
        if isinstance(lesson_review, dict) and lesson_review.get("status") == "human-reviewed":
            _exact_keys(lesson_review.get("approval"), APPROVAL_KEYS, f"lesson {lesson.get('id')} approval", errors)
        if not _review_valid(lesson):
            errors.append(f"lesson review binding is invalid for {lesson.get('id')}")
        if not all(identifier in objective_ids for identifier in lesson.get("objectiveIds", [])):
            errors.append(f"lesson {lesson.get('id')} has unresolved objective")
        sections = _list(lesson.get("materialSections"), f"lesson {lesson.get('id')} material sections", errors)
        if lesson.get("materialSectionIds") != [section.get("id") for section in sections]:
            errors.append(f"lesson {lesson.get('id')} material section IDs do not match")
        section_orders = [section.get("order") for section in sections if isinstance(section, dict)]
        if len(section_orders) != len(sections) or any(not isinstance(order, int) or order < 1 for order in section_orders) or section_orders != sorted(section_orders) or len(set(section_orders)) != len(section_orders):
            errors.append(f"section order is invalid for lesson {lesson.get('id')}")
        for section in sections:
            if not isinstance(section, dict):
                errors.append("section must be an object")
                continue
            _exact_keys(section, SECTION_KEYS, f"section {section.get('id') if isinstance(section, dict) else ''}", errors)
            if section.get("id") in section_ids:
                errors.append(f"duplicate section ID {section.get('id')}")
            section_ids.add(section.get("id"))
            if section.get("lessonId") != lesson.get("id") or not str(section.get("id", "")).startswith("material-section-"):
                errors.append(f"section has unresolved lesson or invalid ID")
            if section.get("origin") not in {"source", "generated"} or section.get("generatedStudyGuidance") != (section.get("origin") == "generated"):
                errors.append(f"section {section.get('id')} has incompatible origin label")
            if not isinstance(section.get("generatedStudyGuidance"), bool):
                errors.append(f"section {section.get('id')} has non-Boolean guidance flag")
            if section.get("contentVersion") != lesson.get("contentVersion") or not _valid_content_version(section.get("contentVersion")):
                errors.append(f"section {section.get('id')} has incompatible content version")
            _validate_refs(section.get("sourceRefs"), sources, classifications, f"section {section.get('id')}", errors, non_teaching)
            if not all(question_id in question_ids for question_id in section.get("linkedQuestionIds", [])):
                errors.append(f"section {section.get('id')} has unresolved linked question")
            for claim in section.get("summaries", []) + section.get("examTips", []) + section.get("recaps", []):
                _exact_keys(claim, {"body", "sourceRefs"}, f"section {section.get('id')} claim", errors)
                if not isinstance(claim, dict):
                    continue
                if not _non_empty(claim.get("body")):
                    errors.append(f"section {section.get('id')} has an empty claim")
                _validate_refs(claim.get("sourceRefs"), sources, classifications, f"section {section.get('id')} claim", errors, non_teaching)
            for field, text_fields in (("terms", ("term", "definition")), ("examples", ("title", "body")), ("mistakes", ("misconception", "correction"))):
                for item in section.get(field, []):
                    _exact_keys(item, set(text_fields) | {"sourceRefs"}, f"section {section.get('id')} {field}", errors)
                    if not isinstance(item, dict):
                        continue
                    if not all(_non_empty(item.get(key)) for key in text_fields):
                        errors.append(f"section {section.get('id')} has an empty {field} claim")
                    _validate_refs(item.get("sourceRefs"), sources, classifications, f"section {section.get('id')} {field}", errors, non_teaching)
    normalized: dict[tuple[str, str], str] = {}
    for question in questions:
        if not isinstance(question, dict):
            errors.append("question must be an object")
            continue
        type_name = question.get("type") if isinstance(question, dict) else None
        _exact_keys(question, MCQ_KEYS if type_name == "mcq" else TF_KEYS, f"question {question.get('id') if isinstance(question, dict) else ''}", errors)
        question_id = question.get("id") if isinstance(question, dict) else None
        if not isinstance(question_id, str) or not question_id.startswith("gq-"):
            errors.append("invalid question id")
            continue
        if question_id in ids:
            errors.append(f"duplicate id {question_id}")
        ids.add(question_id)
        if type_name not in {"mcq", "true-false"}:
            errors.append(f"question {question_id} has invalid type")
        if not _non_empty(question.get("prompt")) or not _non_empty(question.get("topic")):
            errors.append(f"question {question_id} has an empty prompt or topic")
        if PROHIBITED_GENERATED_CLAIMS.search(" ".join(str(value) for value in (question.get("prompt"), question.get("rationale"), *question.get("options", [])))):
            errors.append(f"question {question_id} contains prohibited official/exam wording")
        normalized_key = (str(type_name), _normalize_prompt(str(question.get("prompt", ""))))
        if normalized_key in normalized:
            errors.append(f"duplicate normalized prompt: {question_id} and {normalized[normalized_key]}")
        normalized[normalized_key] = question_id
        if question.get("difficulty") not in {"easy", "medium", "hard"} or question.get("bloomLevel") not in {"remember", "apply", "analyze"} or question.get("cognitiveLevel") != question.get("bloomLevel"):
            errors.append(f"question {question_id} has invalid difficulty or Bloom level")
        if question.get("learningObjectiveId") not in objective_ids:
            errors.append(f"question {question_id} has unresolved objective")
        owning_lesson = _question_lesson_id(question_id)
        if owning_lesson not in lesson_order or question.get("learningObjectiveId") not in next((lesson.get("objectiveIds", []) for lesson in lessons if isinstance(lesson, dict) and lesson.get("id") == owning_lesson), []):
            errors.append(f"question {question_id} objective does not belong to its owning lesson")
        if not _valid_content_version(question.get("contentVersion")):
            errors.append(f"question {question_id} has invalid content version")
        _exact_keys(question.get("provenance"), PROVENANCE_KEYS, f"question {question_id} provenance", errors)
        if isinstance(question.get("provenance"), dict) and (not _non_empty(question["provenance"].get("modelVersion")) or not _non_empty(question["provenance"].get("promptVersion"))):
            errors.append(f"question {question_id} has invalid provenance values")
        _exact_keys(question.get("duplicateComparison"), DUPLICATE_KEYS, f"question {question_id} duplicate comparison", errors)
        if isinstance(question.get("duplicateComparison"), dict) and question["duplicateComparison"].get("matchClass") not in {"none", "exact", "near", "conflict"}:
            errors.append(f"question {question_id} has invalid duplicate comparison")
        _validate_refs(question.get("sourceRefs"), sources, classifications, f"question {question_id}", errors, non_teaching)
        _validate_refs(question.get("provenance", {}).get("sourceRefs") if isinstance(question.get("provenance"), dict) else None, sources, classifications, f"question {question_id} provenance", errors, non_teaching)
        review = question.get("review")
        _exact_keys(review, VALIDATED_REVIEW_KEYS if isinstance(review, dict) and review.get("status") == "validated" else HUMAN_REVIEW_KEYS if isinstance(review, dict) and review.get("status") == "human-reviewed" else set(), f"question {question_id} review", errors)
        if isinstance(review, dict) and review.get("status") == "human-reviewed":
            _exact_keys(review.get("approval"), APPROVAL_KEYS, f"question {question_id} approval", errors)
        if question.get("duplicateDisposition") != "retain" or not _review_valid(question):
            errors.append(f"question {question_id} has incompatible review state")
        if type_name == "mcq":
            options = question.get("options")
            answer = question.get("correctAnswer")
            if not isinstance(options, list) or len(options) != 4 or len(set(options)) != 4 or not all(_non_empty(option) for option in options):
                errors.append(f"question {question_id} needs four unique MCQ options")
            if isinstance(answer, bool) or not isinstance(answer, int) or not isinstance(options, list) or not 0 <= answer < len(options):
                errors.append(f"question {question_id} has invalid answer index")
            rationales = question.get("distractorRationales")
            if not isinstance(rationales, list) or len(rationales) != 4 or not all(_non_empty(item) and len(item.strip()) >= 12 for item in rationales):
                errors.append(f"question {question_id} needs four substantive distractor rationales")
            expected_targets = {"prompt", "correctAnswer", "rationale", *(f"options[{index}]" for index in range(4)), *(f"distractorRationales[{index}]" for index in range(4))}
        else:
            if not isinstance(question.get("correctAnswer"), bool):
                errors.append(f"question {question_id} has invalid true/false answer")
            correction = question.get("correctedStatement")
            if (question.get("correctAnswer") is True and correction is not None) or (question.get("correctAnswer") is False and not _non_empty(correction)):
                errors.append(f"question {question_id} has invalid corrected statement")
            expected_targets = {"prompt", "correctAnswer", "rationale", "correctedStatement"} if question.get("correctAnswer") is False else {"prompt", "correctAnswer", "rationale"}
        if not _non_empty(question.get("rationale")):
            errors.append(f"question {question_id} has empty rationale")
        evidence = question.get("evidenceMap")
        if not isinstance(evidence, list) or {entry.get("target") for entry in evidence if isinstance(entry, dict)} != expected_targets:
            errors.append(f"question {question_id} has incomplete evidence map")
        else:
            for entry in evidence:
                _exact_keys(entry, EVIDENCE_KEYS, f"question {question_id} evidence", errors)
                if not isinstance(entry, dict):
                    continue
                if not _non_empty(entry.get("claimId")) or entry.get("support") not in {"direct", "derived"}:
                    errors.append(f"question {question_id} has invalid evidence entry")
                _validate_refs(entry.get("sourceRefs"), sources, classifications, f"question {question_id} evidence", errors, non_teaching)
    if [question.get("id") for question in questions] != sorted(question.get("id") for question in questions):
        errors.append("questions are not in deterministic ID order")
    answer_counts = Counter(question.get("correctAnswer") for question in questions if isinstance(question, dict) and question.get("type") == "true-false")
    if Counter(question.get("type") for question in questions if isinstance(question, dict)) != Counter({"mcq": 126, "true-false": 84}):
        errors.append("question type distribution is incorrect")
    if Counter(question.get("difficulty") for question in questions if isinstance(question, dict)) != Counter({"easy": 63, "medium": 105, "hard": 42}):
        errors.append("difficulty distribution is incorrect")
    if Counter(question.get("bloomLevel") for question in questions if isinstance(question, dict)) != Counter({"remember": 63, "apply": 105, "analyze": 42}):
        errors.append("Bloom distribution is incorrect")
    if answer_counts != Counter({True: 42, False: 42}):
        errors.append("true/false answer balance is incorrect")
    explanation_ids: set[str] = set()
    for explanation in explanations:
        if not isinstance(explanation, dict):
            errors.append("Arabic explanation must be an object")
            continue
        _exact_keys(explanation, EXPLANATION_KEYS, f"Arabic explanation {explanation.get('id') if isinstance(explanation, dict) else ''}", errors)
        explanation_id = explanation.get("id") if isinstance(explanation, dict) else None
        if not isinstance(explanation_id, str) or not explanation_id.startswith("explanation-") or explanation_id in explanation_ids:
            errors.append("Arabic explanation has invalid or duplicate ID")
        explanation_ids.add(explanation_id)
        if explanation.get("questionId") not in question_ids or explanation.get("language") != "ar" or explanation.get("generatedStudyGuidance") is not True:
            errors.append("Arabic explanation has unresolved linkage")
        if not isinstance(explanation.get("generatedStudyGuidance"), bool):
            errors.append("Arabic explanation has non-Boolean guidance flag")
        if not _valid_content_version(explanation.get("contentVersion")):
            errors.append("Arabic explanation has invalid content version")
        explanation_review = explanation.get("review")
        _exact_keys(explanation_review, VALIDATED_REVIEW_KEYS if isinstance(explanation_review, dict) and explanation_review.get("status") == "validated" else HUMAN_REVIEW_KEYS if isinstance(explanation_review, dict) and explanation_review.get("status") == "human-reviewed" else set(), f"Arabic explanation {explanation_id} review", errors)
        if isinstance(explanation_review, dict) and explanation_review.get("status") == "human-reviewed":
            _exact_keys(explanation_review.get("approval"), APPROVAL_KEYS, f"Arabic explanation {explanation_id} approval", errors)
        if not _review_valid(explanation):
            errors.append(f"Arabic explanation review binding is invalid for {explanation_id}")
        question = next((item for item in questions if isinstance(item, dict) and item.get("id") == explanation.get("questionId")), None)
        if question is not None and (explanation.get("id") != f"explanation-{question['id']}-ar" or explanation.get("contentVersion") != question.get("contentVersion") or explanation.get("sourceRefs") != question.get("sourceRefs")):
            errors.append("Arabic explanation is incompatible with its linked question")
        if PROHIBITED_GENERATED_CLAIMS.search(" ".join(str(value) for value in (explanation.get("translation"), explanation.get("body"), explanation.get("note")))):
            errors.append("Arabic explanation contains prohibited official/exam wording")
        if not _non_empty(explanation.get("translation")) or not ARABIC_RE.search(str(explanation.get("translation", ""))):
            errors.append("Arabic explanation needs non-empty Arabic translation")
        paragraphs = explanation.get("explanation")
        if not isinstance(paragraphs, list) or not 2 <= len(paragraphs) <= 3 or not all(_non_empty(paragraph) for paragraph in paragraphs):
            errors.append("Arabic explanation needs two or three non-empty paragraphs")
        if not _non_empty(explanation.get("body")) or not _non_empty(explanation.get("note")):
            errors.append("Arabic explanation has empty body or note")
        _validate_refs(explanation.get("sourceRefs"), sources, classifications, f"Arabic explanation {explanation_id}", errors, non_teaching)
    if len(explanations) != len(questions) or Counter(item.get("questionId") for item in explanations if isinstance(item, dict)) != Counter(question.get("id") for question in questions if isinstance(question, dict)):
        errors.append("Arabic explanations must map exactly once to every question")
    explanations_by_id = {item.get("id"): item for item in explanations if isinstance(item, dict)}
    for question in questions:
        if isinstance(question, dict) and (question.get("generatedExplanationId") not in explanations_by_id or explanations_by_id[question.get("generatedExplanationId")].get("questionId") != question.get("id")):
            errors.append(f"question {question.get('id')} has unresolved generatedExplanationId")
    if all(isinstance(explanation, dict) and isinstance(explanation.get("id"), str) for explanation in explanations) and [explanation["id"] for explanation in explanations] != sorted(explanation["id"] for explanation in explanations):
        errors.append("Arabic explanations are not ordered")
    if non_teaching:
        errors.append(f"non-teaching referenced pages: {', '.join(sorted(non_teaching))}")
    coverage = course.get("coverage", {})
    all_teaching = sorted(f"{source}:{page}" for (source, page), value in classifications.items() if value == "teaching")
    seen = sorted(_reference_pages(lessons))
    if coverage.get("teachingPageIds") != all_teaching or coverage.get("referencedTeachingPages") != seen or seen != all_teaching:
        errors.append("teaching-page coverage is incomplete or inconsistent")
    counts = coverage.get("classificationCounts", {})
    if counts != {"closing": 21, "cover": 21, "divider": 21, "teaching": 454} or coverage.get("totalPages") != 517 or coverage.get("teachingPages") != 454:
        errors.append("source page classification totals are incorrect")
    if not course.get("contentPolicy", {}).get("generatedQuestionsRequireHumanReviewForExam") and len(eligible_question_ids(payloads, "mock-exam")) != 210:
        errors.append("all validated questions must be eligible for the low-stakes Mock Exam")
    return errors


def payload_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _counts(payloads: dict[str, dict]) -> dict[str, Any]:
    course, lessons, questions, explanations = (payloads["course"], payloads["lessons"]["lessons"], payloads["questions"]["questions"], payloads["explanations-ar"]["explanations"])
    return {
        "sources": len(course["sources"]), "modules": len(course["modules"]), "lessons": len(lessons), "questions": len(questions), "explanations": len(explanations),
        "types": Counter(item["type"] for item in questions), "difficulty": Counter(item["difficulty"] for item in questions), "bloom": Counter(item["bloomLevel"] for item in questions),
        "module": Counter(item["moduleId"] for item in lessons), "lesson": Counter("lesson-" + re.sub(r"-\d{3}$", "", item["id"])[3:] for item in questions),
        "review": Counter(item["review"]["status"] for item in questions), "answers": Counter(item["correctAnswer"] for item in questions if item["type"] == "true-false"),
        "practice": len(eligible_question_ids(payloads, "practice")), "mock": len(eligible_question_ids(payloads, "mock-exam")),
    }


def measure_payloads(payloads: dict[str, dict]) -> dict[str, Any]:
    """Measure report values from payload records and source extraction data."""
    _, _, extraction = _inputs()
    course = payloads["course"]
    lessons = payloads["lessons"]["lessons"]
    classifications = {(page["sourceId"], page["page"]): page["classification"] for page in extraction["pages"]}
    expected = {f"{source}:{page}" for (source, page), classification in classifications.items() if classification == "teaching"}
    reported = set(course.get("coverage", {}).get("referencedTeachingPages", []))
    actual = _reference_pages(lessons)
    non_teaching = {page_id for page_id in actual if tuple([page_id.rsplit(":", 1)[0], int(page_id.rsplit(":", 1)[1])]) in classifications and classifications[tuple([page_id.rsplit(":", 1)[0], int(page_id.rsplit(":", 1)[1])])] != "teaching"}
    canonical_parts = load_content_parts()
    expected_lessons = {lesson["id"] for part in canonical_parts for lesson in part["lessons"]}
    actual_lessons = {lesson.get("id") for lesson in lessons if isinstance(lesson, dict)}
    expected_objectives = {objective["id"] for part in canonical_parts for lesson in part["lessons"] for objective in lesson["learningObjectives"]}
    actual_objectives = {objective_id for lesson in lessons if isinstance(lesson, dict) for objective_id in lesson.get("objectiveIds", [])}
    expected_sections = {section["id"] for part in canonical_parts for lesson in part["lessons"] for section in lesson["materialSections"]}
    actual_sections = {section.get("id") for lesson in lessons if isinstance(lesson, dict) for section in lesson.get("materialSections", []) if isinstance(section, dict)}
    questions = payloads["questions"].get("questions", [])
    explanations = payloads["explanations-ar"].get("explanations", [])
    normalized = [(question.get("type"), _normalize_prompt(question.get("prompt", ""))) for question in questions if isinstance(question, dict)]
    return {
        "classificationCounts": Counter(page["classification"] for page in extraction["pages"]),
        "totalPages": len(extraction["pages"]),
        "expectedTeaching": expected,
        "reportedTeaching": reported,
        "actualTeaching": actual,
        "missing": expected - reported,
        "unexpected": reported - expected,
        "nonTeaching": non_teaching,
        "omittedLessons": expected_lessons - actual_lessons,
        "omittedObjectives": expected_objectives - actual_objectives,
        "omittedSections": expected_sections - actual_sections,
        "evidenceOk": len(questions) == 210 and all(_answer_and_evidence_valid(question) for question in questions if isinstance(question, dict)),
        "arabicOk": len(explanations) == len(questions) and all(isinstance(explanation, dict) and explanation.get("language") == "ar" and explanation.get("generatedStudyGuidance") is True and _non_empty(explanation.get("translation")) and isinstance(explanation.get("explanation"), list) and 2 <= len(explanation["explanation"]) <= 3 for explanation in explanations),
        "duplicatesOk": len(normalized) == len(set(normalized)),
    }


def build_reports(payloads: dict[str, dict]) -> dict[str, str]:
    course = payloads["course"]
    lessons = payloads["lessons"]["lessons"]
    counts = _counts(payloads)
    coverage = course["coverage"]
    measured = measure_payloads(payloads)
    lesson_pages = {lesson["id"]: _reference_pages([lesson]) for lesson in lessons}
    lesson_to_module = {lesson["id"]: lesson["moduleId"] for lesson in lessons}
    module_pages = {module["id"]: set().union(*(lesson_pages[lesson["id"]] for lesson in lessons if lesson["moduleId"] == module["id"])) for module in course["modules"]}
    module_lines = [f"- `{module['id']}`: {len(module_pages[module['id']])} teaching pages, {sum(1 for lesson in lessons if lesson['moduleId'] == module['id'])} lessons" for module in course["modules"]]
    lesson_lines = [f"- `{lesson['id']}`: {len(lesson_pages[lesson['id']])} teaching pages" for lesson in lessons]
    question_modules = Counter(lesson_to_module.get("lesson-" + re.sub(r"-\d{3}$", "", question["id"])[3:], "unmapped") for question in payloads["questions"]["questions"] if isinstance(question, dict))
    coverage_report = "\n".join([
        "# Content Coverage Report", "", "Generated from canonical payload data; no timestamp is used.", "",
        f"- Sources: {counts['sources']} PDFs", f"- Extracted pages: {coverage['totalPages']}",
        f"- Teaching pages: {measured['classificationCounts']['teaching']}; cover {measured['classificationCounts']['cover']}, divider {measured['classificationCounts']['divider']}, closing {measured['classificationCounts']['closing']}, reference {measured['classificationCounts']['reference']}.",
        f"- Teaching-page coverage: {len(measured['reportedTeaching'])}/{len(measured['expectedTeaching'])}; missing {len(measured['missing'])}, unexpected {len(measured['unexpected'])}, non-teaching references {len(measured['nonTeaching'])}.",
        f"- Modules: {counts['modules']}; lessons: {counts['lessons']}; questions: {counts['questions']}; Arabic explanations: {counts['explanations']}.", "", "## Module coverage", "", *module_lines, "", "## Lesson teaching-page coverage", "", *lesson_lines, "", "## Omissions", "", f"- Omitted lessons {len(measured['omittedLessons'])}; omitted objectives {len(measured['omittedObjectives'])}; omitted sections {len(measured['omittedSections'])}.",
    ]) + "\n"
    def rendered(counter: Counter) -> str:
        return ", ".join(f"{key} {counter[key]}" for key in sorted(counter))
    quality_report = "\n".join([
        "# Question Quality Report", "", "Generated from canonical payload data; no timestamp is used.", "",
        f"- Questions: {counts['questions']} ({rendered(counts['types'])}).", f"- Difficulty: {rendered(counts['difficulty'])}.", f"- Bloom: {rendered(counts['bloom'])}.", f"- Review/quality state: {rendered(counts['review'])}; all retained and validated.", f"- True/false answer balance: true {counts['answers'][True]}, false {counts['answers'][False]}.",
        f"- Eligible scored Practice: {counts['practice']}; eligible low-stakes Mock Exam: {counts['mock']}.",
        f"- Evidence/source references: {'complete' if measured['evidenceOk'] else 'failed'}; Arabic records: {'complete' if measured['arabicOk'] else 'failed'}; duplicate normalized prompts: {'none' if measured['duplicatesOk'] else 'failed'}.", "", "## Counts by module", "", *[f"- `{module['id']}`: {question_modules[module['id']]} questions" for module in course['modules']], "", "## Counts by lesson", "", *[f"- `{lesson_id}`: {counts['lesson'][lesson_id]} questions" for lesson_id in sorted(counts['lesson'])], "", "## Assessment boundary", "", "- Generated questions are source-backed, validated practice material. The human-review gate is disabled only for this low-stakes Mock Exam pool.", "- This does not authorize high-stakes, credentialing, admissions, employment, compliance, or externally reported assessment use; those uses require complete current human approval.",
    ]) + "\n"
    return {"coverage": coverage_report, "quality": quality_report}


def write_artifacts(payloads: dict[str, dict]) -> None:
    errors = validate_payloads(payloads)
    if errors:
        raise ValueError("cannot write invalid payloads:\n" + "\n".join(errors))
    for name, path in DATA_PATHS.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload_bytes(payloads[name]))
    for name, path in REPORT_PATHS.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(build_reports(payloads)[name], encoding="utf-8", newline="\n")


def _expected_artifacts(payloads: dict[str, dict]) -> dict[Path, bytes]:
    artifacts = {DATA_PATHS[name]: payload_bytes(payload) for name, payload in payloads.items()}
    artifacts.update({REPORT_PATHS[name]: text.encode("utf-8") for name, text in build_reports(payloads).items()})
    return artifacts


def check_artifacts(payloads: dict[str, dict]) -> list[str]:
    errors = validate_payloads(payloads)
    for path, expected in _expected_artifacts(payloads).items():
        if not path.exists():
            errors.append(f"missing generated artifact: {path.relative_to(ROOT)}")
        elif path.read_bytes() != expected:
            errors.append(f"generated artifact drift: {path.relative_to(ROOT)}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate and compare artifacts without writing")
    args = parser.parse_args(argv)
    payloads = build_payloads(load_content_parts())
    errors = check_artifacts(payloads) if args.check else validate_payloads(payloads)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    if not args.check:
        write_artifacts(payloads)
    print(f"OS payloads OK: {len(payloads['course']['modules'])} modules, {len(payloads['lessons']['lessons'])} lessons, {len(payloads['questions']['questions'])} questions, {len(payloads['explanations-ar']['explanations'])} Arabic explanations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
