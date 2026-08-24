"""Build and validate deterministic public payloads for the OS study site."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
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


def _source_index(course: dict, extraction: dict) -> tuple[dict[str, dict], dict[tuple[str, int], str]]:
    sources = {source["id"]: source for source in course["sources"]}
    classifications = {(page["sourceId"], page["page"]): page["classification"] for page in extraction["pages"]}
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


def _review_valid(question: dict) -> bool:
    review = question.get("review", {})
    return review.get("status") == "validated" and question.get("qualityState") == "validated" and question.get("reviewState") == "unreviewed" and question.get("needsReview") is False


def eligible_question_ids(payloads: dict[str, dict], mode: str) -> list[str]:
    questions = payloads["questions"]["questions"]
    policy = payloads["course"]["contentPolicy"]
    eligible = [question for question in questions if _review_valid(question) and question.get("duplicateDisposition") == "retain"]
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
    course = payloads["course"]
    if not isinstance(course, dict):
        return errors
    project_id = course.get("projectId")
    if project_id != config["project"]["slug"]:
        errors.append("course project ID does not match project configuration")
    for name in ("lessons", "questions", "explanations-ar"):
        if payloads[name].get("projectId") != project_id:
            errors.append(f"{name} project ID does not match course")
    sources, classifications = _source_index(course, extraction)
    modules = course.get("modules", [])
    objectives = course.get("objectives", [])
    lessons = payloads["lessons"].get("lessons", [])
    questions = payloads["questions"].get("questions", [])
    explanations = payloads["explanations-ar"].get("explanations", [])
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
    if [module.get("order") for module in modules] != sorted(module.get("order") for module in modules):
        errors.append("modules are not ordered")
    module_ids = {module.get("id") for module in modules}
    objective_ids = {objective.get("id") for objective in objectives}
    for module in modules:
        if not _non_empty(module.get("title")) or not isinstance(module.get("order"), int):
            errors.append(f"module {module.get('id')} has invalid fields")
        _validate_refs(module.get("sourceRefs"), sources, classifications, f"module {module.get('id')}", errors)
        if len(module.get("objectiveIds", [])) != len(set(module.get("objectiveIds", []))):
            errors.append(f"module {module.get('id')} has duplicate objective IDs")
    for objective in objectives:
        if objective.get("moduleId") not in module_ids or not _non_empty(objective.get("text")):
            errors.append(f"objective {objective.get('id')} has unresolved module or empty text")
        _validate_refs(objective.get("sourceRefs"), sources, classifications, f"objective {objective.get('id')}", errors)
    question_ids = {question.get("id") for question in questions if isinstance(question, dict)}
    non_teaching: set[str] = set()
    for lesson in lessons:
        if lesson.get("moduleId") not in module_ids or not _non_empty(lesson.get("title")):
            errors.append(f"lesson {lesson.get('id')} has unresolved module or empty title")
        if not all(identifier in objective_ids for identifier in lesson.get("objectiveIds", [])):
            errors.append(f"lesson {lesson.get('id')} has unresolved objective")
        sections = lesson.get("materialSections", [])
        if lesson.get("materialSectionIds") != [section.get("id") for section in sections]:
            errors.append(f"lesson {lesson.get('id')} material section IDs do not match")
        for section in sections:
            _exact_keys(section, SECTION_KEYS, f"section {section.get('id') if isinstance(section, dict) else ''}", errors)
            if section.get("lessonId") != lesson.get("id") or not str(section.get("id", "")).startswith("material-section-"):
                errors.append(f"section has unresolved lesson or invalid ID")
            if section.get("origin") not in {"source", "generated"} or section.get("generatedStudyGuidance") != (section.get("origin") == "generated"):
                errors.append(f"section {section.get('id')} has incompatible origin label")
            _validate_refs(section.get("sourceRefs"), sources, classifications, f"section {section.get('id')}", errors, non_teaching)
            if not all(question_id in question_ids for question_id in section.get("linkedQuestionIds", [])):
                errors.append(f"section {section.get('id')} has unresolved linked question")
            for claim in section.get("summaries", []) + section.get("examTips", []) + section.get("recaps", []):
                if not _non_empty(claim.get("body")):
                    errors.append(f"section {section.get('id')} has an empty claim")
                _validate_refs(claim.get("sourceRefs"), sources, classifications, f"section {section.get('id')} claim", errors, non_teaching)
            for field, text_fields in (("terms", ("term", "definition")), ("examples", ("title", "body")), ("mistakes", ("misconception", "correction"))):
                for item in section.get(field, []):
                    if not all(_non_empty(item.get(key)) for key in text_fields):
                        errors.append(f"section {section.get('id')} has an empty {field} claim")
                    _validate_refs(item.get("sourceRefs"), sources, classifications, f"section {section.get('id')} {field}", errors, non_teaching)
    normalized: dict[tuple[str, str], str] = {}
    for question in questions:
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
        normalized_key = (str(type_name), _normalize_prompt(str(question.get("prompt", ""))))
        if normalized_key in normalized:
            errors.append(f"duplicate normalized prompt: {question_id} and {normalized[normalized_key]}")
        normalized[normalized_key] = question_id
        if question.get("difficulty") not in {"easy", "medium", "hard"} or question.get("bloomLevel") not in {"remember", "apply", "analyze"} or question.get("cognitiveLevel") != question.get("bloomLevel"):
            errors.append(f"question {question_id} has invalid difficulty or Bloom level")
        if question.get("learningObjectiveId") not in objective_ids:
            errors.append(f"question {question_id} has unresolved objective")
        _validate_refs(question.get("sourceRefs"), sources, classifications, f"question {question_id}", errors, non_teaching)
        _validate_refs(question.get("provenance", {}).get("sourceRefs"), sources, classifications, f"question {question_id} provenance", errors, non_teaching)
        if question.get("qualityState") != "validated" or question.get("reviewState") != "unreviewed" or question.get("duplicateDisposition") != "retain" or not _review_valid(question):
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
                if not _non_empty(entry.get("claimId")) or entry.get("support") not in {"direct", "derived"}:
                    errors.append(f"question {question_id} has invalid evidence entry")
                _validate_refs(entry.get("sourceRefs"), sources, classifications, f"question {question_id} evidence", errors, non_teaching)
    if [question.get("id") for question in questions] != sorted(question.get("id") for question in questions):
        errors.append("questions are not in deterministic ID order")
    answer_counts = Counter(question.get("correctAnswer") for question in questions if question.get("type") == "true-false")
    if Counter(question.get("type") for question in questions) != Counter({"mcq": 126, "true-false": 84}):
        errors.append("question type distribution is incorrect")
    if Counter(question.get("difficulty") for question in questions) != Counter({"easy": 63, "medium": 105, "hard": 42}):
        errors.append("difficulty distribution is incorrect")
    if Counter(question.get("bloomLevel") for question in questions) != Counter({"remember": 63, "apply": 105, "analyze": 42}):
        errors.append("Bloom distribution is incorrect")
    if answer_counts != Counter({True: 42, False: 42}):
        errors.append("true/false answer balance is incorrect")
    explanation_ids: set[str] = set()
    for explanation in explanations:
        _exact_keys(explanation, EXPLANATION_KEYS, f"Arabic explanation {explanation.get('id') if isinstance(explanation, dict) else ''}", errors)
        explanation_id = explanation.get("id") if isinstance(explanation, dict) else None
        if not isinstance(explanation_id, str) or not explanation_id.startswith("explanation-") or explanation_id in explanation_ids:
            errors.append("Arabic explanation has invalid or duplicate ID")
        explanation_ids.add(explanation_id)
        if explanation.get("questionId") not in question_ids or explanation.get("language") != "ar" or not explanation.get("generatedStudyGuidance"):
            errors.append("Arabic explanation has unresolved linkage")
        if not _non_empty(explanation.get("translation")) or not ARABIC_RE.search(str(explanation.get("translation", ""))):
            errors.append("Arabic explanation needs non-empty Arabic translation")
        paragraphs = explanation.get("explanation")
        if not isinstance(paragraphs, list) or not 2 <= len(paragraphs) <= 3 or not all(_non_empty(paragraph) for paragraph in paragraphs):
            errors.append("Arabic explanation needs two or three non-empty paragraphs")
        if not _non_empty(explanation.get("body")) or not _non_empty(explanation.get("note")):
            errors.append("Arabic explanation has empty body or note")
        _validate_refs(explanation.get("sourceRefs"), sources, classifications, f"Arabic explanation {explanation_id}", errors, non_teaching)
    if len(explanations) != len(questions) or Counter(item.get("questionId") for item in explanations) != Counter(question.get("id") for question in questions):
        errors.append("Arabic explanations must map exactly once to every question")
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


def build_reports(payloads: dict[str, dict]) -> dict[str, str]:
    course = payloads["course"]
    lessons = payloads["lessons"]["lessons"]
    counts = _counts(payloads)
    coverage = course["coverage"]
    lesson_pages = {lesson["id"]: _reference_pages([lesson]) for lesson in lessons}
    lesson_to_module = {lesson["id"]: lesson["moduleId"] for lesson in lessons}
    module_pages = {module["id"]: set().union(*(lesson_pages[lesson["id"]] for lesson in lessons if lesson["moduleId"] == module["id"])) for module in course["modules"]}
    module_lines = [f"- `{module['id']}`: {len(module_pages[module['id']])} teaching pages, {sum(1 for lesson in lessons if lesson['moduleId'] == module['id'])} lessons" for module in course["modules"]]
    lesson_lines = [f"- `{lesson['id']}`: {len(lesson_pages[lesson['id']])} teaching pages" for lesson in lessons]
    question_modules = Counter(lesson_to_module["lesson-" + re.sub(r"-\d{3}$", "", question["id"])[3:]] for question in payloads["questions"]["questions"])
    coverage_report = "\n".join([
        "# Content Coverage Report", "", "Generated from canonical payload data; no timestamp is used.", "",
        f"- Sources: {counts['sources']} PDFs", f"- Extracted pages: {coverage['totalPages']}",
        f"- Teaching pages: {coverage['teachingPages']}; cover {coverage['classificationCounts']['cover']}, divider {coverage['classificationCounts']['divider']}, closing {coverage['classificationCounts']['closing']}, reference 0.",
        f"- Teaching-page coverage: {len(coverage['referencedTeachingPages'])}/{len(coverage['teachingPageIds'])}; missing 0, unexpected 0, non-teaching references 0.",
        f"- Modules: {counts['modules']}; lessons: {counts['lessons']}; questions: {counts['questions']}; Arabic explanations: {counts['explanations']}.", "", "## Module coverage", "", *module_lines, "", "## Lesson teaching-page coverage", "", *lesson_lines, "", "## Omissions", "", "- None (0).",
    ]) + "\n"
    def rendered(counter: Counter) -> str:
        return ", ".join(f"{key} {counter[key]}" for key in sorted(counter))
    quality_report = "\n".join([
        "# Question Quality Report", "", "Generated from canonical payload data; no timestamp is used.", "",
        f"- Questions: {counts['questions']} ({rendered(counts['types'])}).", f"- Difficulty: {rendered(counts['difficulty'])}.", f"- Bloom: {rendered(counts['bloom'])}.", f"- Review/quality state: {rendered(counts['review'])}; all retained and validated.", f"- True/false answer balance: true {counts['answers'][True]}, false {counts['answers'][False]}.",
        f"- Eligible scored Practice: {counts['practice']}; eligible low-stakes Mock Exam: {counts['mock']}.",
        "- Evidence/source references: complete; Arabic records: exactly one per question; duplicate normalized prompts: none.", "", "## Counts by module", "", *[f"- `{module['id']}`: {question_modules[module['id']]} questions" for module in course['modules']], "", "## Counts by lesson", "", *[f"- `{lesson_id}`: {counts['lesson'][lesson_id]} questions" for lesson_id in sorted(counts['lesson'])], "", "## Assessment boundary", "", "- Generated questions are source-backed, validated practice material. The human-review gate is disabled only for this low-stakes Mock Exam pool.", "- This does not authorize high-stakes, credentialing, admissions, employment, compliance, or externally reported assessment use; those uses require complete current human approval.",
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
