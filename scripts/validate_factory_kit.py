import argparse
import json
import re
from pathlib import Path, PureWindowsPath

VARIABLE = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
UNFINISHED_MARKERS = (
    "T" + "BD",
    "T" + "ODO",
    "implement" + " later",
    "fill" + " in later",
)

REQUIRED_DOCS = (
    "README.md",
    "00-QUICK-START.md",
    "01-PROJECT-INPUT-TEMPLATE.md",
    "02-PRD-TEMPLATE.md",
    "03-SOURCE-INGESTION-SPEC.md",
    "04-CONTENT-AND-DATA-CONTRACTS.md",
    "05-MATERIAL-LESSONS-SPEC.md",
    "06-QUESTION-GENERATION-SPEC.md",
    "07-UX-AND-SYSTEM-FLOW.md",
    "08-BUILD-WORKFLOW.md",
    "09-QA-GATES.md",
    "10-MASTER-BUILD-PROMPT.md",
    "11-HANDOFF-AND-DEPLOYMENT.md",
)

REQUIRED_EXAMPLES = (
    "examples/project-config.example.json",
    "examples/source-manifest.example.json",
    "examples/lesson.example.json",
    "examples/official-question.example.json",
    "examples/generated-question.example.json",
    "examples/explanation.example.json",
)

REQUIRED_HEADINGS = {
    "README.md": (
        "Purpose",
        "Reading order",
        "Validation",
    ),
    "00-QUICK-START.md": ("Start a new project",),
    "01-PROJECT-INPUT-TEMPLATE.md": (
        "Copy-ready form",
        "Variable dictionary",
    ),
    "02-PRD-TEMPLATE.md": (
        "Project Variables",
        "Fixed Product Requirements",
        "Product Goal",
        "Users and Jobs",
        "Content Modes",
        "Functional Requirements",
        "Material Requirements",
        "Question Requirements",
        "Persistence",
        "Non-Functional Requirements",
        "Acceptance Criteria",
    ),
    "03-SOURCE-INGESTION-SPEC.md": (
        "Purpose",
        "Source Lifecycle",
        "Required Audit Output",
        "Format Rules",
        "Normalization and Acceptance",
        "Answer-Key Boundaries",
    ),
    "04-CONTENT-AND-DATA-CONTRACTS.md": (
        "Project Configuration",
        "Source Manifest and `sourceRef`",
        "Material Sections",
        "Questions",
        "Generated Question Quality and Duplication",
        "Review State and Scoring",
    ),
    "05-MATERIAL-LESSONS-SPEC.md": (
        "Purpose and Inputs",
        "Module Map and Learning Objectives",
        "Lesson Page",
        "Lesson Quality Checks",
    ),
    "06-QUESTION-GENERATION-SPEC.md": (
        "Purpose and Contract",
        "MCQ Rubric",
        "True/False Rubric",
        "Evidence and Ambiguity",
        "Review States and Canonical Mapping",
        "Release Checks",
    ),
    "07-UX-AND-SYSTEM-FLOW.md": (
        "Route map",
        "Core journeys",
        "Navigation and responsiveness",
        "Question interactions and exam safety",
        "Accessibility and language",
    ),
    "08-BUILD-WORKFLOW.md": (
        "Resume contract",
        "Stage 1: Initialize project",
        "Stage 12: Handoff, deploy, and verify public output",
        "Stage invalidation and repair",
    ),
    "09-QA-GATES.md": tuple(
        f"Gate {number}: {name}"
        for number, name in enumerate(
            (
                "Input Completeness",
                "Extraction and Provenance",
                "Canonical Content",
                "Lessons and Guidance",
                "Generated Questions",
                "Application Safety and Logic",
                "Browser QA",
                "Deployment",
            ),
            1,
        )
    ),
    "10-MASTER-BUILD-PROMPT.md": (
        "Master build prompt",
        "Low-token operating mode",
    ),
    "11-HANDOFF-AND-DEPLOYMENT.md": (
        "Maintainer file map",
        "Deployment authorization boundary",
        "Authorized deployment procedure",
        "Public verification",
        "Final handoff summary",
    ),
}

EXAMPLE_REQUIRED_KEYS = {
    "examples/project-config.example.json": {
        "version",
        "project",
        "contentPolicy",
        "questionGeneration",
        "exam",
        "deployment",
    },
    "examples/source-manifest.example.json": {"version", "sources"},
    "examples/official-question.example.json": {
        "id",
        "origin",
        "type",
        "prompt",
        "topic",
        "correctAnswer",
        "sourceRefs",
        "needsReview",
        "reviewNotes",
        "options",
        "duplicateSources",
        "officialExplanation",
    },
    "examples/lesson.example.json": {
        "id",
        "moduleId",
        "title",
        "learningObjectives",
        "summary",
        "explanation",
        "keyTerms",
        "workedExamples",
        "commonMistakes",
        "examTips",
        "recap",
        "sourceRefs",
        "review",
        "objectiveIds",
        "body",
        "needsReview",
        "reviewNotes",
        "linkedQuestionIds",
    },
    "examples/generated-question.example.json": {
        "id",
        "origin",
        "type",
        "prompt",
        "options",
        "correctAnswer",
        "rationale",
        "distractorRationales",
        "difficulty",
        "bloomLevel",
        "learningObjectiveId",
        "sourceRefs",
        "review",
        "evidenceMap",
        "contentVersion",
        "qualityState",
        "reviewState",
        "needsReview",
        "reviewNotes",
        "topic",
        "cognitiveLevel",
        "generationMethod",
        "generatedExplanationId",
        "provenance",
        "duplicateComparison",
        "duplicateDisposition",
    },
    "examples/explanation.example.json": {
        "questionId",
        "language",
        "generatedStudyGuidance",
        "translation",
        "explanation",
        "note",
        "sourceRefs",
        "review",
        "id",
        "body",
        "needsReview",
        "reviewNotes",
    },
}

PROJECT_CONFIG_OBJECT_KEYS = {
    "project": {
        "title",
        "shortTitle",
        "slug",
        "description",
        "brandInitials",
        "sourceLanguage",
        "studyLanguage",
    },
    "contentPolicy": {
        "mode",
        "allowOutsideSources",
        "generatedQuestionsRequireHumanReviewForExam",
    },
    "questionGeneration": {
        "mcqPerLesson",
        "trueFalsePerLesson",
        "difficultyPercent",
        "bloomPercent",
    },
    "exam": {"defaultCount", "defaultMinutes"},
    "deployment": {"provider", "repository", "branch", "publicUrl"},
}
CONTENT_POLICY_MODES = {"source-only", "source-plus-generated", "generated-only"}
DIFFICULTY_PERCENT_KEYS = {"easy", "medium", "hard"}
BLOOM_PERCENT_KEYS = {"remember", "apply", "analyze"}
PROJECT_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LANGUAGE_TAG = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
REPOSITORY_NAME = re.compile(r"^[^/\s]+/[^/\s]+$")
SEMANTIC_VERSION = re.compile(r"^\d+\.\d+(?:\.\d+)?$")
UTC_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")

SOURCE_REFERENCE_REQUIRED_KEYS = {"sourceId", "locationType", "location"}
SOURCE_REFERENCE_LOCATION_TYPES = {"page", "slide", "section", "row", "image"}
SOURCE_STATUSES = {
    "inventoried",
    "extracted",
    "visually-checked",
    "normalized",
    "accepted",
    "needs-review",
}
SOURCE_FORMATS = {
    "pdf",
    "docx",
    "pptx",
    "text",
    "markdown",
    "csv",
    "json",
    "image",
}
GENERATED_DIFFICULTIES = {"easy", "medium", "hard"}
GENERATED_BLOOM_LEVELS = {"remember", "apply", "analyze"}
CANONICAL_COGNITIVE_LEVELS = {
    "remember",
    "understand",
    "apply",
    "analyze",
    "evaluate",
    "create",
}
QUESTION_TYPES = {
    "mcq",
    "true-false",
    "true-false-group",
    "multi-select",
    "matching",
    "ordering",
}
GENERATED_REVIEW_STATUSES = {
    "draft",
    "validated",
    "human-reviewed",
    "needs-review",
    "rejected",
}
GENERATED_MCQ_EVIDENCE_TARGETS = {
    "prompt",
    "correctAnswer",
    "rationale",
    "options[0]",
    "options[1]",
    "options[2]",
    "options[3]",
    "distractorRationales[0]",
    "distractorRationales[1]",
    "distractorRationales[2]",
    "distractorRationales[3]",
}
GENERATED_REVIEW_TRUTH_TABLE = {
    "draft": ("draft", "unreviewed", True, None),
    "validated": ("validated", "unreviewed", True, None),
    "human-reviewed": ("approved", "approved", False, "approved"),
    "needs-review": ("needs-review", "needs-review", True, "needs-review"),
    "rejected": ("rejected", "rejected", True, "rejected"),
}
REVIEW_APPROVAL_REQUIRED_KEYS = {
    "reviewedRecordId",
    "reviewedContentVersion",
    "status",
    "decision",
    "reviewer",
    "reviewedAt",
    "reason",
    "notes",
}
DUPLICATE_COMPARISON_REQUIRED_KEYS = {
    "algorithmVersion",
    "normalizedPrompt",
    "candidateIds",
    "matchClass",
}
DUPLICATE_MATCH_CLASSES = {"none", "exact", "near", "conflict"}
DUPLICATE_DISPOSITIONS = {"retain", "reject-duplicate", "needs-review"}


def collect_template_variables(text: str) -> set[str]:
    return set(VARIABLE.findall(text))


def read_markdown(path: Path) -> tuple[str | None, list[str]]:
    try:
        return path.read_text(encoding="utf-8"), []
    except (OSError, UnicodeError) as error:
        return None, [f"{path}: cannot read Markdown: {error}"]


def collect_declared_variables(path: Path) -> set[str]:
    text, _ = read_markdown(path)
    return collect_template_variables(text) if text is not None else set()


def validate_json_file(path: Path) -> list[str]:
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [f"{path}: invalid JSON: {error}"]
    return []


def validate_object_keys(
    value: object,
    path: str,
    required: set[str],
    *,
    exact: bool = False,
) -> list[str]:
    if not isinstance(value, dict):
        return [f"{path}: must be an object"]
    errors = []
    missing = sorted(required - value.keys())
    if missing:
        errors.append(f"{path}: missing required keys: {', '.join(missing)}")
    if exact:
        unexpected = sorted(value.keys() - required)
        if unexpected:
            errors.append(f"{path}: unexpected keys: {', '.join(unexpected)}")
    return errors


def validate_non_empty_string(value: object, path: str) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return [f"{path}: must be a non-empty string"]
    return []


def validate_exact_boolean(value: object, path: str) -> list[str]:
    if type(value) is not bool:
        return [f"{path}: must be a boolean"]
    return []


def validate_positive_integer(value: object, path: str) -> list[str]:
    if type(value) is not int or value <= 0:
        return [f"{path}: must be a positive integer"]
    return []


def validate_string_array(
    value: object,
    path: str,
    *,
    require_non_empty: bool = False,
    unique: bool = False,
) -> list[str]:
    if not isinstance(value, list) or (require_non_empty and not value):
        requirement = "a non-empty array" if require_non_empty else "an array"
        return [f"{path}: must be {requirement} of non-empty strings"]
    if not all(isinstance(item, str) and item.strip() for item in value):
        return [f"{path}: must contain only non-empty strings"]
    if unique and len(value) != len(set(value)):
        return [f"{path}: must contain unique values"]
    return []


def validate_percent_distribution(
    value: object, path: str, required: set[str]
) -> list[str]:
    errors = validate_object_keys(value, path, required, exact=True)
    if not isinstance(value, dict):
        return errors
    for key in required:
        percent = value.get(key)
        if type(percent) not in {int, float} or not 0 <= percent <= 100:
            errors.append(f"{path}.{key}: must be a number from 0 to 100")
    if all(type(value.get(key)) in {int, float} for key in required):
        if sum(value[key] for key in required) != 100:
            errors.append(f"{path}: percentages must total 100")
    return errors


def validate_project_config_example(payload: dict, name: str) -> list[str]:
    errors = validate_object_keys(
        payload, name, EXAMPLE_REQUIRED_KEYS[name], exact=True
    )
    if type(payload.get("version")) is not int or payload.get("version") != 1:
        errors.append(f"{name}: version: must be integer 1")

    for field, required in PROJECT_CONFIG_OBJECT_KEYS.items():
        errors.extend(
            validate_object_keys(
                payload.get(field), f"{name}: {field}", required, exact=True
            )
        )

    project = payload.get("project")
    if isinstance(project, dict):
        for field in PROJECT_CONFIG_OBJECT_KEYS["project"]:
            errors.extend(
                validate_non_empty_string(
                    project.get(field), f"{name}: project.{field}"
                )
            )
        slug = project.get("slug")
        if isinstance(slug, str) and not PROJECT_SLUG.fullmatch(slug):
            errors.append(
                f"{name}: project.slug: must be a lowercase hyphenated "
                "stable identifier"
            )
        for field in ("sourceLanguage", "studyLanguage"):
            value = project.get(field)
            if isinstance(value, str) and value and not LANGUAGE_TAG.fullmatch(value):
                errors.append(f"{name}: project.{field}: invalid language tag")

    policy = payload.get("contentPolicy")
    if isinstance(policy, dict):
        if policy.get("mode") not in CONTENT_POLICY_MODES:
            errors.append(f"{name}: contentPolicy.mode: invalid value")
        for field in (
            "allowOutsideSources",
            "generatedQuestionsRequireHumanReviewForExam",
        ):
            errors.extend(
                validate_exact_boolean(
                    policy.get(field), f"{name}: contentPolicy.{field}"
                )
            )

    generation = payload.get("questionGeneration")
    if isinstance(generation, dict):
        for field in ("mcqPerLesson", "trueFalsePerLesson"):
            errors.extend(
                validate_positive_integer(
                    generation.get(field), f"{name}: questionGeneration.{field}"
                )
            )
        errors.extend(
            validate_percent_distribution(
                generation.get("difficultyPercent"),
                f"{name}: questionGeneration.difficultyPercent",
                DIFFICULTY_PERCENT_KEYS,
            )
        )
        errors.extend(
            validate_percent_distribution(
                generation.get("bloomPercent"),
                f"{name}: questionGeneration.bloomPercent",
                BLOOM_PERCENT_KEYS,
            )
        )

    exam = payload.get("exam")
    if isinstance(exam, dict):
        for field in ("defaultCount", "defaultMinutes"):
            errors.extend(
                validate_positive_integer(exam.get(field), f"{name}: exam.{field}")
            )

    deployment = payload.get("deployment")
    if isinstance(deployment, dict):
        if deployment.get("provider") != "github-pages":
            errors.append(f"{name}: deployment.provider: must be github-pages")
        for field in ("repository", "branch", "publicUrl"):
            errors.extend(
                validate_non_empty_string(
                    deployment.get(field), f"{name}: deployment.{field}"
                )
            )
        repository = deployment.get("repository")
        if (
            isinstance(repository, str)
            and repository
            and not REPOSITORY_NAME.fullmatch(repository)
        ):
            errors.append(f"{name}: deployment.repository: must use OWNER/REPOSITORY")
        public_url = deployment.get("publicUrl")
        if (
            isinstance(public_url, str)
            and public_url
            and not public_url.startswith(("https://", "http://"))
        ):
            errors.append(f"{name}: deployment.publicUrl: must be an HTTP(S) URL")
    return errors


def validate_source_reference(reference: object, path: str) -> list[str]:
    if not isinstance(reference, dict):
        return [f"{path}: source reference must be an object"]

    missing = sorted(SOURCE_REFERENCE_REQUIRED_KEYS - reference.keys())
    errors = []
    if missing:
        errors.append(f"{path}: missing required keys: {', '.join(missing)}")

    source_id = reference.get("sourceId")
    if source_id is not None and (
        not isinstance(source_id, str)
        or not source_id.startswith("source-")
        or not source_id.removeprefix("source-")
    ):
        errors.append(f"{path}: sourceId must use the source- prefix")

    location_type = reference.get("locationType")
    if (
        location_type is not None
        and location_type not in SOURCE_REFERENCE_LOCATION_TYPES
    ):
        errors.append(f"{path}: invalid locationType: {location_type}")
    location = reference.get("location")
    if location is not None and (
        type(location) not in {int, str}
        or isinstance(location, str)
        and not location.strip()
        or type(location) is int
        and location <= 0
    ):
        errors.append(f"{path}: location must be a positive integer or string")
    confidence = reference.get("confidence")
    if confidence is not None and (
        type(confidence) not in {int, float} or not 0 <= confidence <= 1
    ):
        errors.append(f"{path}: confidence must be a number from 0 to 1")
    return errors


def validate_manifest_location(
    value: object, path: str, source_format: object
) -> list[str]:
    required = {"locationType", "location"}
    errors = validate_object_keys(value, path, required, exact=True)
    if not isinstance(value, dict):
        return errors
    location_type = value.get("locationType")
    if location_type not in SOURCE_REFERENCE_LOCATION_TYPES:
        errors.append(f"{path}: invalid locationType: {location_type}")
    expected = {"pdf": "page", "pptx": "slide"}.get(source_format)
    if expected is not None and location_type != expected:
        errors.append(f"{path}: locationType must be {expected} for {source_format}")
    location = value.get("location")
    if (
        type(location) not in {int, str}
        or isinstance(location, str)
        and not location.strip()
        or type(location) is int
        and location <= 0
    ):
        errors.append(f"{path}: location must be a positive integer or string")
    return errors


def validate_source_manifest_example(payload: dict, name: str) -> list[str]:
    errors = []
    version = payload.get("version")
    if not isinstance(version, str) or not SEMANTIC_VERSION.fullmatch(version):
        errors.append(f"{name}: version: must be a semantic version string")
    sources = payload.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append(f"{name}: sources: must be a non-empty array")
        return errors

    source_ids = []
    common = {"id", "fileName", "format", "checksum", "status", "locations"}
    for index, source in enumerate(sources):
        path = f"{name}: sources[{index}]"
        errors.extend(validate_object_keys(source, path, common))
        if not isinstance(source, dict):
            continue
        source_format = source.get("format")
        required = set(common)
        if source_format == "pdf":
            required.add("pages")
        elif source_format == "pptx":
            required.add("slides")
        allowed = required | {"pages", "slides"}
        errors.extend(validate_object_keys(source, path, required))
        unexpected = sorted(source.keys() - allowed)
        if unexpected:
            errors.append(f"{path}: unexpected keys: {', '.join(unexpected)}")

        source_id = source.get("id")
        if isinstance(source_id, str):
            source_ids.append(source_id)
        if (
            not isinstance(source_id, str)
            or not source_id.startswith("source-")
            or not source_id.removeprefix("source-")
        ):
            errors.append(f"{path}: id must use the source- prefix")
        for field in ("fileName", "checksum"):
            errors.extend(
                validate_non_empty_string(source.get(field), f"{path}: {field}")
            )
        if source_format not in SOURCE_FORMATS:
            errors.append(f"{path}: format: invalid value: {source_format}")
        if source.get("status") not in SOURCE_STATUSES:
            errors.append(f"{path}: status: invalid value: {source.get('status')}")
        for count_field in ("pages", "slides"):
            if count_field in source:
                errors.extend(
                    validate_positive_integer(
                        source[count_field], f"{path}: {count_field}"
                    )
                )
        locations = source.get("locations")
        if not isinstance(locations, list) or not locations:
            errors.append(f"{path}: locations: must be a non-empty array")
        else:
            for location_index, location in enumerate(locations):
                errors.extend(
                    validate_manifest_location(
                        location,
                        f"{path}: locations[{location_index}]",
                        source_format,
                    )
                )
    duplicates = sorted({value for value in source_ids if source_ids.count(value) > 1})
    if duplicates:
        errors.append(f"{name}: sources: duplicate IDs: {', '.join(duplicates)}")
    return errors


def validate_source_reference_list(
    value: object, path: str, *, require_non_empty: bool = False
) -> list[str]:
    if not isinstance(value, list) or (require_non_empty and not value):
        requirement = "a non-empty array" if require_non_empty else "an array"
        return [f"{path}: must be {requirement}"]
    return [
        error
        for index, reference in enumerate(value)
        for error in validate_source_reference(reference, f"{path}[{index}]")
    ]


def validate_source_references(payload: object, path: str) -> list[str]:
    if isinstance(payload, list):
        return [
            error
            for index, item in enumerate(payload)
            for error in validate_source_references(item, f"{path}[{index}]")
        ]
    if not isinstance(payload, dict):
        return []

    errors = []
    for key, value in payload.items():
        key_path = f"{path}: {key}"
        if key == "sourceRefs":
            errors.extend(validate_source_reference_list(value, key_path))
        elif key == "sourceRef":
            errors.extend(validate_source_reference(value, key_path))
        errors.extend(validate_source_references(value, key_path))
    return errors


def is_non_empty_string_list(value: object, minimum: int, maximum: int) -> bool:
    return (
        isinstance(value, list)
        and minimum <= len(value) <= maximum
        and all(isinstance(item, str) and item.strip() for item in value)
    )


def validate_generated_review(payload: dict, name: str) -> list[str]:
    review = payload.get("review")
    errors = validate_object_keys(review, f"{name}: review", {"status"})
    if not isinstance(review, dict):
        return errors
    unexpected = sorted(review.keys() - {"status", "approval"})
    if unexpected:
        errors.append(f"{name}: review: unexpected keys: {', '.join(unexpected)}")
    status = review.get("status")
    if status not in GENERATED_REVIEW_STATUSES:
        errors.append(f"{name}: review.status: invalid value: {status}")
        return errors

    expected_needs_review = status != "human-reviewed"
    needs_review = payload.get("needsReview")
    if type(needs_review) is not bool or needs_review is not expected_needs_review:
        display = str(expected_needs_review).lower()
        errors.append(
            f"{name}: needsReview: must be {display} when review.status is {status}"
        )
    if not isinstance(payload.get("reviewNotes"), str):
        errors.append(f"{name}: reviewNotes: must be a string")

    approval = review.get("approval")
    expected_decision = {
        "human-reviewed": "approved",
        "needs-review": "needs-review",
        "rejected": "rejected",
    }.get(status)
    if expected_decision is None:
        if approval is not None:
            errors.append(
                f"{name}: review.approval: must be absent when review.status "
                f"is {status}"
            )
        return errors
    errors.extend(
        validate_object_keys(
            approval,
            f"{name}: review.approval",
            REVIEW_APPROVAL_REQUIRED_KEYS,
            exact=True,
        )
    )
    if not isinstance(approval, dict):
        return errors
    if approval.get("status") != "completed":
        errors.append(f"{name}: review.approval.status: must be completed")
    if approval.get("decision") != expected_decision:
        errors.append(
            f"{name}: review.approval.decision: must be {expected_decision} "
            f"when review.status is {status}"
        )
    if approval.get("reviewedRecordId") != payload.get("id"):
        errors.append(f"{name}: review.approval.reviewedRecordId: must equal id")
    reviewed_version = approval.get("reviewedContentVersion")
    if not isinstance(reviewed_version, str) or not SEMANTIC_VERSION.fullmatch(
        reviewed_version
    ):
        errors.append(
            f"{name}: review.approval.reviewedContentVersion: must be a "
            "semantic version"
        )
    elif "contentVersion" in payload and reviewed_version != payload.get(
        "contentVersion"
    ):
        errors.append(
            f"{name}: review.approval.reviewedContentVersion: must equal contentVersion"
        )
    errors.extend(
        validate_non_empty_string(
            approval.get("reviewer"), f"{name}: review.approval.reviewer"
        )
    )
    reviewed_at = approval.get("reviewedAt")
    if not isinstance(reviewed_at, str) or not UTC_DATETIME.fullmatch(reviewed_at):
        errors.append(f"{name}: review.approval.reviewedAt: must be ISO 8601 UTC")
    for field in ("reason", "notes"):
        if not isinstance(approval.get(field), str):
            errors.append(f"{name}: review.approval.{field}: must be a string")
    return errors


def validate_prefixed_id(value: object, path: str, prefix: str) -> list[str]:
    if (
        not isinstance(value, str)
        or not value.startswith(prefix)
        or not value.removeprefix(prefix)
    ):
        return [f"{path}: must use the {prefix} prefix"]
    return []


def validate_evidenced_records(
    value: object,
    path: str,
    required: set[str],
    *,
    require_non_empty: bool,
) -> list[str]:
    if not isinstance(value, list) or (require_non_empty and not value):
        requirement = "a non-empty array" if require_non_empty else "an array"
        return [f"{path}: must be {requirement}"]
    errors = []
    for index, record in enumerate(value):
        record_path = f"{path}[{index}]"
        errors.extend(validate_object_keys(record, record_path, required, exact=True))
        if not isinstance(record, dict):
            continue
        for field in required - {"sourceRefs"}:
            errors.extend(
                validate_non_empty_string(record.get(field), f"{record_path}: {field}")
            )
        errors.extend(
            validate_source_reference_list(
                record.get("sourceRefs"),
                f"{record_path}: sourceRefs",
                require_non_empty=True,
            )
        )
    return errors


def validate_lesson_example(payload: dict, name: str) -> list[str]:
    errors = []
    errors.extend(validate_prefixed_id(payload.get("id"), f"{name}: id", "lesson-"))
    errors.extend(
        validate_prefixed_id(payload.get("moduleId"), f"{name}: moduleId", "module-")
    )
    for field in ("title", "summary", "body"):
        errors.extend(validate_non_empty_string(payload.get(field), f"{name}: {field}"))
    errors.extend(
        validate_source_reference_list(
            payload.get("sourceRefs"), f"{name}: sourceRefs", require_non_empty=True
        )
    )
    errors.extend(
        validate_string_array(
            payload.get("objectiveIds"),
            f"{name}: objectiveIds",
            require_non_empty=True,
            unique=True,
        )
    )
    if isinstance(payload.get("objectiveIds"), list):
        for index, objective_id in enumerate(payload["objectiveIds"]):
            errors.extend(
                validate_prefixed_id(
                    objective_id,
                    f"{name}: objectiveIds[{index}]",
                    "objective-",
                )
            )
    errors.extend(
        validate_evidenced_records(
            payload.get("learningObjectives"),
            f"{name}: learningObjectives",
            {"id", "text", "sourceRefs"},
            require_non_empty=True,
        )
    )
    errors.extend(
        validate_evidenced_records(
            payload.get("keyTerms"),
            f"{name}: keyTerms",
            {"term", "definition", "sourceRefs"},
            require_non_empty=True,
        )
    )
    errors.extend(
        validate_evidenced_records(
            payload.get("workedExamples"),
            f"{name}: workedExamples",
            {"title", "body", "sourceRefs"},
            require_non_empty=False,
        )
    )
    errors.extend(
        validate_evidenced_records(
            payload.get("commonMistakes"),
            f"{name}: commonMistakes",
            {"misconception", "correction", "sourceRefs"},
            require_non_empty=False,
        )
    )
    errors.extend(
        validate_evidenced_records(
            payload.get("examTips"),
            f"{name}: examTips",
            {"body", "sourceRefs"},
            require_non_empty=False,
        )
    )
    errors.extend(
        validate_string_array(
            payload.get("linkedQuestionIds"),
            f"{name}: linkedQuestionIds",
            unique=True,
        )
    )
    if isinstance(payload.get("linkedQuestionIds"), list):
        for index, question_id in enumerate(payload["linkedQuestionIds"]):
            if not (
                isinstance(question_id, str) and question_id.startswith(("q-", "gq-"))
            ):
                errors.append(f"{name}: linkedQuestionIds[{index}]: must use q- or gq-")
    if type(payload.get("needsReview")) is not bool:
        errors.append(f"{name}: needsReview: must be a boolean")
    if not isinstance(payload.get("reviewNotes"), str):
        errors.append(f"{name}: reviewNotes: must be a string")
    if not is_non_empty_string_list(payload.get("explanation"), 2, 5):
        errors.append(
            f"{name}: explanation: must contain two to five non-empty paragraphs"
        )
    if not is_non_empty_string_list(payload.get("recap"), 3, 7):
        errors.append(f"{name}: recap: must contain three to seven non-empty strings")
    objectives = payload.get("learningObjectives")
    objective_ids = payload.get("objectiveIds")
    authoring_objective_ids = (
        [objective.get("id") for objective in objectives]
        if isinstance(objectives, list)
        and all(isinstance(objective, dict) for objective in objectives)
        else None
    )
    valid_objective_ids = (
        isinstance(objective_ids, list)
        and bool(objective_ids)
        and all(isinstance(value, str) and value.strip() for value in objective_ids)
        and isinstance(authoring_objective_ids, list)
        and all(
            isinstance(value, str) and value.strip()
            for value in authoring_objective_ids
        )
    )
    if not valid_objective_ids:
        errors.append(
            f"{name}: learningObjectives: IDs must equal non-empty "
            "objectiveIds in the same order"
        )
    elif authoring_objective_ids != objective_ids:
        errors.append(
            f"{name}: learningObjectives: IDs must equal objectiveIds in the same order"
        )
    explanation = payload.get("explanation")
    if is_non_empty_string_list(explanation, 2, 5):
        expected_body = "\n\n".join(explanation)
        if payload.get("body") != expected_body:
            errors.append(
                f"{name}: body: must equal explanation paragraphs joined "
                "with two newlines"
            )
    errors.extend(validate_generated_review(payload, name))
    return errors


def validate_generated_evidence_map(payload: dict, name: str) -> list[str]:
    evidence_map = payload.get("evidenceMap")
    if not isinstance(evidence_map, list) or not evidence_map:
        return [f"{name}: evidenceMap: must be a non-empty array"]

    errors = []
    targets = []
    for index, evidence in enumerate(evidence_map):
        path = f"{name}: evidenceMap[{index}]"
        if not isinstance(evidence, dict):
            errors.append(f"{path}: must be an object")
            continue
        errors.extend(
            validate_object_keys(
                evidence,
                path,
                {"claimId", "target", "sourceRefs", "support"},
                exact=True,
            )
        )
        target = evidence.get("target")
        if isinstance(target, str):
            targets.append(target)
        if not isinstance(target, str) or target not in GENERATED_MCQ_EVIDENCE_TARGETS:
            errors.append(f"{path}: invalid claim target: {target}")
        if (
            not isinstance(evidence.get("claimId"), str)
            or not evidence["claimId"].strip()
        ):
            errors.append(f"{path}: claimId must be a non-empty string")
        errors.extend(
            validate_source_reference_list(
                evidence.get("sourceRefs"),
                f"{path}: sourceRefs",
                require_non_empty=True,
            )
        )
        if evidence.get("support") not in {"direct", "derived"}:
            errors.append(f"{path}: support must be direct or derived")

    missing = sorted(GENERATED_MCQ_EVIDENCE_TARGETS - set(targets))
    if missing:
        errors.append(
            f"{name}: evidenceMap: missing claim targets: {', '.join(missing)}"
        )
    duplicates = sorted({target for target in targets if targets.count(target) > 1})
    if duplicates:
        errors.append(
            f"{name}: evidenceMap: duplicate claim targets: {', '.join(duplicates)}"
        )
    return errors


def validate_generated_review_truth(payload: dict, name: str) -> list[str]:
    review = payload.get("review")
    if not isinstance(review, dict):
        return []
    review_status = review.get("status")
    expected = GENERATED_REVIEW_TRUTH_TABLE.get(review_status)
    if expected is None:
        return []

    quality_state, canonical_review, _, _ = expected
    errors = []
    fields = (
        ("qualityState", quality_state),
        ("reviewState", canonical_review),
    )
    for field, expected_value in fields:
        actual_value = payload.get(field)
        if actual_value != expected_value:
            errors.append(
                f"{name}: {field}: must be {expected_value} when review.status is "
                f"{review_status}"
            )
    return errors


def validate_id_text_items(value: object, path: str) -> tuple[list[str], list[str]]:
    if not isinstance(value, list) or not value:
        return [f"{path}: must be a non-empty array"], []
    errors = []
    ids = []
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        errors.extend(validate_object_keys(item, item_path, {"id", "text"}, exact=True))
        if not isinstance(item, dict):
            continue
        for field in ("id", "text"):
            errors.extend(
                validate_non_empty_string(item.get(field), f"{item_path}: {field}")
            )
        if isinstance(item.get("id"), str):
            ids.append(item["id"])
    if len(ids) != len(set(ids)):
        errors.append(f"{path}: IDs must be unique")
    return errors, ids


def validate_question_type_shape(payload: dict, name: str) -> list[str]:
    question_type = payload.get("type")
    if question_type not in QUESTION_TYPES:
        return [f"{name}: type: invalid value: {question_type}"]
    answer = payload.get("correctAnswer")
    errors = []
    if question_type in {"mcq", "true-false", "multi-select"}:
        options = payload.get("options")
        if question_type == "mcq":
            valid_options = is_non_empty_string_list(options, 4, 4)
            if not valid_options:
                errors.append(
                    f"{name}: options: must contain exactly four non-empty strings"
                )
            if (
                type(answer) is not int
                or not isinstance(options, list)
                or not 0 <= answer < len(options)
            ):
                errors.append(
                    f"{name}: correctAnswer: must be a valid zero-based option index"
                )
        elif question_type == "true-false":
            if options != ["True", "False"]:
                errors.append(f'{name}: options: must equal ["True", "False"]')
            if type(answer) is not int or answer not in {0, 1}:
                errors.append(f"{name}: correctAnswer: must be 0 or 1")
        else:
            if not is_non_empty_string_list(options, 2, 10_000):
                errors.append(
                    f"{name}: options: must contain at least two non-empty strings"
                )
            if (
                not isinstance(answer, list)
                or not answer
                or any(type(index) is not int for index in answer)
                or len(answer) != len(set(answer))
                or not isinstance(options, list)
                or any(index < 0 or index >= len(options) for index in answer)
            ):
                errors.append(
                    f"{name}: correctAnswer: must contain unique valid option indices"
                )
    elif question_type == "true-false-group":
        item_errors, statement_ids = validate_id_text_items(
            payload.get("statements"), f"{name}: statements"
        )
        errors.extend(item_errors)
        if (
            not isinstance(answer, dict)
            or set(answer) != set(statement_ids)
            or any(type(value) is not bool for value in answer.values())
        ):
            errors.append(
                f"{name}: correctAnswer: must map every statement ID to a boolean"
            )
    elif question_type == "matching":
        left_errors, left_ids = validate_id_text_items(
            payload.get("leftItems"), f"{name}: leftItems"
        )
        right_errors, right_ids = validate_id_text_items(
            payload.get("rightItems"), f"{name}: rightItems"
        )
        errors.extend(left_errors + right_errors)
        allow_many = payload.get("allowManyToOne", False)
        if type(allow_many) is not bool:
            errors.append(f"{name}: allowManyToOne: must be a boolean")
        values = list(answer.values()) if isinstance(answer, dict) else []
        if (
            not isinstance(answer, dict)
            or set(answer) != set(left_ids)
            or any(value not in right_ids for value in values)
            or not allow_many
            and len(values) != len(set(values))
        ):
            errors.append(
                f"{name}: correctAnswer: must map every left ID to valid right IDs"
            )
    elif question_type == "ordering":
        item_errors, item_ids = validate_id_text_items(
            payload.get("items"), f"{name}: items"
        )
        errors.extend(item_errors)
        if (
            not isinstance(answer, list)
            or len(answer) != len(item_ids)
            or set(answer) != set(item_ids)
        ):
            errors.append(
                f"{name}: correctAnswer: must order every item ID exactly once"
            )
    return errors


def validate_question_base(payload: dict, name: str, expected_origin: str) -> list[str]:
    errors = []
    prefix = "q-" if expected_origin == "official" else "gq-"
    errors.extend(validate_prefixed_id(payload.get("id"), f"{name}: id", prefix))
    if payload.get("origin") != expected_origin:
        errors.append(f"{name}: origin: must be {expected_origin}")
    for field in ("prompt", "topic"):
        errors.extend(validate_non_empty_string(payload.get(field), f"{name}: {field}"))
    errors.extend(
        validate_source_reference_list(
            payload.get("sourceRefs"), f"{name}: sourceRefs", require_non_empty=True
        )
    )
    if type(payload.get("needsReview")) is not bool:
        errors.append(f"{name}: needsReview: must be a boolean")
    if not isinstance(payload.get("reviewNotes"), str):
        errors.append(f"{name}: reviewNotes: must be a string")
    errors.extend(validate_question_type_shape(payload, name))
    return errors


def validate_official_question_example(payload: dict, name: str) -> list[str]:
    errors = validate_question_base(payload, name, "official")
    duplicate_sources = payload.get("duplicateSources")
    errors.extend(
        validate_source_reference_list(duplicate_sources, f"{name}: duplicateSources")
    )
    if not isinstance(payload.get("officialExplanation"), str):
        errors.append(f"{name}: officialExplanation: must be a string")
    return errors


def validate_generated_question_example(payload: dict, name: str) -> list[str]:
    errors = validate_question_base(payload, name, "generated")
    if not payload.get("sourceRefs"):
        errors.append(f"{name}: sourceRefs: must contain at least one source reference")
    rationales = payload.get("distractorRationales")
    if not is_non_empty_string_list(rationales, 4, 4):
        errors.append(
            f"{name}: distractorRationales: must contain exactly four non-empty strings"
        )

    errors.extend(
        validate_non_empty_string(payload.get("rationale"), f"{name}: rationale")
    )

    difficulty = payload.get("difficulty")
    if difficulty not in GENERATED_DIFFICULTIES:
        errors.append(f"{name}: difficulty: invalid value: {difficulty}")
    bloom_level = payload.get("bloomLevel")
    if bloom_level not in GENERATED_BLOOM_LEVELS:
        errors.append(f"{name}: bloomLevel: invalid value: {bloom_level}")
    cognitive_level = payload.get("cognitiveLevel")
    if cognitive_level not in CANONICAL_COGNITIVE_LEVELS:
        errors.append(f"{name}: cognitiveLevel: invalid value: {cognitive_level}")
    if bloom_level != cognitive_level:
        errors.append(f"{name}: bloomLevel: must equal cognitiveLevel")
    errors.extend(
        validate_prefixed_id(
            payload.get("learningObjectiveId"),
            f"{name}: learningObjectiveId",
            "objective-",
        )
    )
    for field in (
        "generationMethod",
        "generatedExplanationId",
        "contentVersion",
    ):
        errors.extend(validate_non_empty_string(payload.get(field), f"{name}: {field}"))
    explanation_id = payload.get("generatedExplanationId")
    if isinstance(explanation_id, str) and not explanation_id.startswith(
        "explanation-"
    ):
        errors.append(f"{name}: generatedExplanationId: must use explanation- prefix")
    content_version = payload.get("contentVersion")
    if (
        isinstance(content_version, str)
        and content_version
        and not SEMANTIC_VERSION.fullmatch(content_version)
    ):
        errors.append(f"{name}: contentVersion: must be a semantic version")

    provenance = payload.get("provenance")
    provenance_keys = {"sourceRefs", "modelVersion", "promptVersion"}
    errors.extend(
        validate_object_keys(
            provenance, f"{name}: provenance", provenance_keys, exact=True
        )
    )
    if isinstance(provenance, dict):
        errors.extend(
            validate_source_reference_list(
                provenance.get("sourceRefs"),
                f"{name}: provenance.sourceRefs",
                require_non_empty=True,
            )
        )
        for field in ("modelVersion", "promptVersion"):
            errors.extend(
                validate_non_empty_string(
                    provenance.get(field), f"{name}: provenance.{field}"
                )
            )

    duplicate = payload.get("duplicateComparison")
    errors.extend(
        validate_object_keys(
            duplicate,
            f"{name}: duplicateComparison",
            DUPLICATE_COMPARISON_REQUIRED_KEYS,
            exact=True,
        )
    )
    if isinstance(duplicate, dict):
        for field in ("algorithmVersion", "normalizedPrompt"):
            errors.extend(
                validate_non_empty_string(
                    duplicate.get(field), f"{name}: duplicateComparison.{field}"
                )
            )
        errors.extend(
            validate_string_array(
                duplicate.get("candidateIds"),
                f"{name}: duplicateComparison.candidateIds",
                unique=True,
            )
        )
        if duplicate.get("matchClass") not in DUPLICATE_MATCH_CLASSES:
            errors.append(f"{name}: duplicateComparison.matchClass: invalid value")
        candidates = duplicate.get("candidateIds")
        if isinstance(candidates, list):
            if candidates != sorted(candidates):
                errors.append(
                    f"{name}: duplicateComparison.candidateIds: must use "
                    "lexicographic order"
                )
            if payload.get("id") in candidates:
                errors.append(
                    f"{name}: duplicateComparison.candidateIds: cannot include id"
                )
            for candidate in candidates:
                if not isinstance(candidate, str) or not candidate.startswith(
                    ("q-", "gq-")
                ):
                    errors.append(
                        f"{name}: duplicateComparison.candidateIds: invalid ID"
                    )
                    break
    disposition = payload.get("duplicateDisposition")
    if disposition not in DUPLICATE_DISPOSITIONS:
        errors.append(f"{name}: duplicateDisposition: invalid value: {disposition}")
    if isinstance(duplicate, dict):
        expected_disposition = {
            "none": "retain",
            "near": "needs-review",
            "conflict": "needs-review",
        }.get(duplicate.get("matchClass"))
        if expected_disposition and disposition != expected_disposition:
            errors.append(
                f"{name}: duplicateDisposition: must be {expected_disposition} "
                f"when matchClass is {duplicate.get('matchClass')}"
            )
    errors.extend(validate_generated_evidence_map(payload, name))
    errors.extend(validate_generated_review(payload, name))
    errors.extend(validate_generated_review_truth(payload, name))
    return errors


def validate_explanation_example(payload: dict, name: str) -> list[str]:
    errors = []
    errors.extend(
        validate_prefixed_id(payload.get("id"), f"{name}: id", "explanation-")
    )
    question_id = payload.get("questionId")
    if not (isinstance(question_id, str) and question_id.startswith(("q-", "gq-"))):
        errors.append(f"{name}: questionId: must use q- or gq- prefix")
    language = payload.get("language")
    if not isinstance(language, str) or not LANGUAGE_TAG.fullmatch(language):
        errors.append(f"{name}: language: invalid language tag")
    if payload.get("generatedStudyGuidance") is not True:
        errors.append(f"{name}: generatedStudyGuidance: must be exactly true")
    if not is_non_empty_string_list(payload.get("explanation"), 2, 3):
        errors.append(
            f"{name}: explanation: must contain two or three non-empty paragraphs"
        )
    for field in ("translation", "body", "note"):
        errors.extend(validate_non_empty_string(payload.get(field), f"{name}: {field}"))
    errors.extend(
        validate_source_reference_list(
            payload.get("sourceRefs"), f"{name}: sourceRefs", require_non_empty=True
        )
    )
    if type(payload.get("needsReview")) is not bool:
        errors.append(f"{name}: needsReview: must be a boolean")
    if not isinstance(payload.get("reviewNotes"), str):
        errors.append(f"{name}: reviewNotes: must be a string")
    errors.extend(validate_generated_review(payload, name))
    return errors


def validate_example_payload(name: str, payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return [f"{name}: example JSON must be an object"]

    missing = sorted(EXAMPLE_REQUIRED_KEYS.get(name, set()) - payload.keys())
    errors = []
    if missing:
        errors.append(f"{name}: missing required top-level keys: {', '.join(missing)}")
    unexpected = sorted(payload.keys() - EXAMPLE_REQUIRED_KEYS.get(name, set()))
    if unexpected:
        errors.append(f"{name}: unexpected top-level keys: {', '.join(unexpected)}")
    generated_validators = {
        "examples/project-config.example.json": validate_project_config_example,
        "examples/source-manifest.example.json": validate_source_manifest_example,
        "examples/lesson.example.json": validate_lesson_example,
        "examples/official-question.example.json": (validate_official_question_example),
        "examples/generated-question.example.json": (
            validate_generated_question_example
        ),
        "examples/explanation.example.json": validate_explanation_example,
    }
    if name in generated_validators:
        errors.extend(generated_validators[name](payload, name))
    source_payload = payload
    if name == "examples/generated-question.example.json":
        source_payload = {
            key: value for key, value in payload.items() if key != "evidenceMap"
        }
    errors.extend(validate_source_references(source_payload, name))
    return errors


def validate_required_files(root: Path, required: tuple[str, ...]) -> list[str]:
    return [
        f"missing required file: {name}"
        for name in required
        if not (root / name).is_file()
    ]


def validate_markdown_headings(path: Path, required: tuple[str, ...]) -> list[str]:
    text, errors = read_markdown(path)
    if text is None:
        return errors
    return validate_markdown_heading_text(path, text, required)


def validate_markdown_heading_text(
    path: Path, text: str, required: tuple[str, ...]
) -> list[str]:
    headings = {
        line.lstrip("#").strip() for line in text.splitlines() if line.startswith("#")
    }
    return [
        f"{path}: missing heading: {heading}"
        for heading in required
        if heading not in headings
    ]


def validate_internal_link_text(root: Path, path: Path, text: str) -> list[str]:
    errors = []
    resolved_root = root.resolve()
    for target in MARKDOWN_LINK.findall(text):
        if target.startswith(("http://", "https://", "#")):
            continue
        clean_target = target.split("#", 1)[0]
        if not clean_target:
            continue
        windows_target = PureWindowsPath(clean_target)
        native_target = Path(clean_target)
        if (
            native_target.is_absolute()
            or windows_target.is_absolute()
            or bool(windows_target.drive)
            or clean_target.startswith(("\\\\", "//"))
        ):
            errors.append(f"{path}: unsafe link target: {target}")
            continue
        resolved_target = (path.parent / clean_target).resolve()
        try:
            resolved_target.relative_to(resolved_root)
        except ValueError:
            errors.append(f"{path}: unsafe link target: {target}")
            continue
        if not resolved_target.exists():
            errors.append(f"{path}: broken relative link: {target}")
    return errors


def validate_internal_links(root: Path, markdown_paths: list[Path]) -> list[str]:
    errors = []
    for path in markdown_paths:
        text, read_errors = read_markdown(path)
        errors.extend(read_errors)
        if text is not None:
            errors.extend(validate_internal_link_text(root, path, text))
    return errors


def validate_unfinished_marker_text(path: Path, text: str) -> list[str]:
    folded_text = text.casefold()
    return [
        f"{path}: unfinished marker: {marker}"
        for marker in UNFINISHED_MARKERS
        if marker.casefold() in folded_text
    ]


def validate_unfinished_markers(markdown_paths: list[Path]) -> list[str]:
    errors = []
    for path in markdown_paths:
        text, read_errors = read_markdown(path)
        errors.extend(read_errors)
        if text is not None:
            errors.extend(validate_unfinished_marker_text(path, text))
    return errors


def iter_source_references(value: object, path: str) -> list[tuple[str, dict]]:
    if isinstance(value, list):
        return [
            item
            for index, child in enumerate(value)
            for item in iter_source_references(child, f"{path}[{index}]")
        ]
    if not isinstance(value, dict):
        return []
    references = []
    for key, child in value.items():
        child_path = f"{path}: {key}"
        if key == "sourceRefs" and isinstance(child, list):
            references.extend(
                (f"{child_path}[{index}]", reference)
                for index, reference in enumerate(child)
                if isinstance(reference, dict)
            )
            continue
        if key == "sourceRef" and isinstance(child, dict):
            references.append((child_path, child))
            continue
        references.extend(iter_source_references(child, child_path))
    return references


def validate_example_links(payloads: dict[str, dict]) -> list[str]:
    errors = []
    manifest = payloads.get("examples/source-manifest.example.json", {})
    sources = manifest.get("sources") if isinstance(manifest, dict) else None
    source_map = {
        source.get("id"): source
        for source in sources or []
        if isinstance(source, dict) and isinstance(source.get("id"), str)
    }
    for name, payload in payloads.items():
        if name == "examples/source-manifest.example.json":
            continue
        for path, reference in iter_source_references(payload, name):
            source = source_map.get(reference.get("sourceId"))
            if source is None:
                errors.append(f"{path}: sourceId does not resolve")
                continue
            locations = source.get("locations")
            available = {
                (location.get("locationType"), location.get("location"))
                for location in locations or []
                if isinstance(location, dict)
            }
            requested = (reference.get("locationType"), reference.get("location"))
            if requested not in available:
                errors.append(f"{path}: source location does not resolve")

    official = payloads.get("examples/official-question.example.json", {})
    generated = payloads.get("examples/generated-question.example.json", {})
    explanation = payloads.get("examples/explanation.example.json", {})
    lesson = payloads.get("examples/lesson.example.json", {})
    question_ids = {
        payload.get("id")
        for payload in (official, generated)
        if isinstance(payload, dict) and isinstance(payload.get("id"), str)
    }
    explanation_ids = (
        {explanation.get("id")}
        if isinstance(explanation, dict) and isinstance(explanation.get("id"), str)
        else set()
    )

    if (
        isinstance(generated, dict)
        and generated.get("generatedExplanationId") not in explanation_ids
    ):
        errors.append(
            "examples/generated-question.example.json: "
            "generatedExplanationId does not resolve"
        )
    if (
        isinstance(explanation, dict)
        and explanation.get("questionId") not in question_ids
    ):
        errors.append("examples/explanation.example.json: questionId does not resolve")
    if (
        isinstance(generated, dict)
        and isinstance(explanation, dict)
        and generated.get("generatedExplanationId") == explanation.get("id")
        and explanation.get("questionId") != generated.get("id")
    ):
        errors.append(
            "examples/explanation.example.json: explanation does not "
            "describe generated question"
        )
    if isinstance(lesson, dict):
        for index, question_id in enumerate(lesson.get("linkedQuestionIds") or []):
            if question_id not in question_ids:
                errors.append(
                    "examples/lesson.example.json: "
                    f"linkedQuestionIds[{index}] does not resolve"
                )
    return errors


def validate_kit(root: Path) -> list[str]:
    errors = validate_required_files(root, REQUIRED_DOCS + REQUIRED_EXAMPLES)
    markdown_paths = sorted(path for path in root.glob("*.md") if path.is_file())
    markdown_texts = {}
    for path in markdown_paths:
        text, read_errors = read_markdown(path)
        errors.extend(read_errors)
        if text is not None:
            markdown_texts[path] = text

    for name, headings in REQUIRED_HEADINGS.items():
        path = root / name
        if path in markdown_texts:
            errors.extend(
                validate_markdown_heading_text(path, markdown_texts[path], headings)
            )

    payloads = {}
    for name in REQUIRED_EXAMPLES:
        path = root / name
        if path.is_file():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                errors.append(f"{path}: invalid JSON: {error}")
                continue
            if isinstance(payload, dict):
                payloads[name] = payload
            errors.extend(validate_example_payload(name, payload))
    errors.extend(validate_example_links(payloads))

    declaration_path = root / "01-PROJECT-INPUT-TEMPLATE.md"
    if declaration_path in markdown_texts:
        declared = collect_template_variables(markdown_texts[declaration_path])
        used = set().union(
            *(collect_template_variables(text) for text in markdown_texts.values())
        )
        errors.extend(
            f"undeclared template variable: {name}" for name in sorted(used - declared)
        )

    for path, text in markdown_texts.items():
        errors.extend(validate_internal_link_text(root, path, text))
        errors.extend(validate_unfinished_marker_text(path, text))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a study-site factory kit.")
    parser.add_argument("--root", type=Path, default=Path("docs/study-site-factory"))
    args = parser.parse_args()

    errors = validate_kit(args.root)
    if errors:
        print("\n".join(errors))
        return 1

    print("Validated study-site factory kit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
