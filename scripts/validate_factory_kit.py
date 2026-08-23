import argparse
import json
import re
from pathlib import Path

VARIABLE = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")

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

EXAMPLE_REQUIRED_KEYS = {
    "examples/source-manifest.example.json": {"version", "sources"},
    "examples/official-question.example.json": {
        "id", "origin", "type", "prompt", "topic", "correctAnswer",
        "sourceRefs", "needsReview", "reviewNotes"
    },
    "examples/lesson.example.json": {
        "id", "moduleId", "title", "learningObjectives", "summary",
        "explanation", "keyTerms", "workedExamples", "commonMistakes",
        "examTips", "recap", "sourceRefs", "review", "objectiveIds",
        "body", "needsReview", "reviewNotes"
    },
    "examples/generated-question.example.json": {
        "id", "origin", "type", "prompt", "options", "correctAnswer",
        "rationale", "distractorRationales", "difficulty", "bloomLevel",
        "learningObjectiveId", "sourceRefs", "review", "evidenceMap",
        "contentVersion", "qualityState", "reviewState", "needsReview",
        "reviewNotes"
    },
    "examples/explanation.example.json": {
        "questionId", "language", "generatedStudyGuidance", "translation",
        "explanation", "note", "sourceRefs", "review"
    },
}

SOURCE_REFERENCE_REQUIRED_KEYS = {"sourceId", "locationType", "location"}
SOURCE_REFERENCE_LOCATION_TYPES = {"page", "slide", "section", "row", "image"}
GENERATED_DIFFICULTIES = {"easy", "medium", "hard"}
GENERATED_BLOOM_LEVELS = {"remember", "apply", "analyze"}
GENERATED_REVIEW_STATUSES = {
    "draft", "validated", "human-reviewed", "needs-review", "rejected"
}
GENERATED_MCQ_EVIDENCE_TARGETS = {
    "prompt", "correctAnswer", "rationale",
    "options[0]", "options[1]", "options[2]", "options[3]",
    "distractorRationales[0]", "distractorRationales[1]",
    "distractorRationales[2]", "distractorRationales[3]",
}
GENERATED_REVIEW_TRUTH_TABLE = {
    "draft": ("draft", "unreviewed", True, None),
    "validated": ("validated", "unreviewed", True, None),
    "human-reviewed": ("approved", "approved", False, "approved"),
    "needs-review": ("needs-review", "needs-review", True, "needs-review"),
    "rejected": ("rejected", "rejected", True, "rejected"),
}


def collect_template_variables(text: str) -> set[str]:
    return set(VARIABLE.findall(text))


def validate_json_file(path: Path) -> list[str]:
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [f"{path}: invalid JSON: {error}"]
    return []


def validate_source_reference(reference: object, path: str) -> list[str]:
    if not isinstance(reference, dict):
        return [f"{path}: source reference must be an object"]

    missing = sorted(SOURCE_REFERENCE_REQUIRED_KEYS - reference.keys())
    errors = []
    if missing:
        errors.append(f"{path}: missing required keys: {', '.join(missing)}")

    location_type = reference.get("locationType")
    if (
        location_type is not None
        and location_type not in SOURCE_REFERENCE_LOCATION_TYPES
    ):
        errors.append(f"{path}: invalid locationType: {location_type}")
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
    status = review.get("status") if isinstance(review, dict) else None
    if status not in GENERATED_REVIEW_STATUSES:
        return [f"{name}: review.status: invalid value: {status}"]
    return []


def validate_lesson_example(payload: dict, name: str) -> list[str]:
    errors = []
    if not is_non_empty_string_list(payload.get("explanation"), 2, 5):
        errors.append(
            f"{name}: explanation: must contain two to five non-empty paragraphs"
        )
    if not is_non_empty_string_list(payload.get("recap"), 3, 7):
        errors.append(
            f"{name}: recap: must contain three to seven non-empty strings"
        )
    objectives = payload.get("learningObjectives")
    objective_ids = payload.get("objectiveIds")
    authoring_objective_ids = [
        objective.get("id") for objective in objectives
    ] if isinstance(objectives, list) and all(
        isinstance(objective, dict) for objective in objectives
    ) else None
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
            f"{name}: learningObjectives: IDs must equal objectiveIds in the "
            "same order"
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
        target = evidence.get("target")
        if isinstance(target, str):
            targets.append(target)
        if (
            not isinstance(target, str)
            or target not in GENERATED_MCQ_EVIDENCE_TARGETS
        ):
            errors.append(f"{path}: invalid claim target: {target}")
        if not isinstance(evidence.get("claimId"), str) or not evidence["claimId"].strip():
            errors.append(f"{path}: claimId must be a non-empty string")
        errors.extend(validate_source_reference_list(
            evidence.get("sourceRefs"),
            f"{path}: sourceRefs",
            require_non_empty=True,
        ))
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
            f"{name}: evidenceMap: duplicate claim targets: "
            f"{', '.join(duplicates)}"
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

    quality_state, canonical_review, needs_review, decision = expected
    errors = []
    fields = (
        ("qualityState", quality_state),
        ("reviewState", canonical_review),
        ("needsReview", needs_review),
    )
    for field, expected_value in fields:
        actual_value = payload.get(field)
        mismatch = (
            type(actual_value) is not bool or actual_value is not expected_value
        ) if field == "needsReview" else actual_value != expected_value
        if mismatch:
            display = str(expected_value).lower() if isinstance(
                expected_value, bool
            ) else expected_value
            errors.append(
                f"{name}: {field}: must be {display} when review.status is "
                f"{review_status}"
            )

    approval = review.get("approval")
    if decision is None:
        if approval is not None:
            errors.append(
                f"{name}: review.approval: must be absent when review.status "
                f"is {review_status}"
            )
        return errors
    if not isinstance(approval, dict):
        errors.append(
            f"{name}: review.approval: must be an object when review.status "
            f"is {review_status}"
        )
        return errors

    if approval.get("status") != "completed":
        errors.append(f"{name}: review.approval.status: must be completed")
    if approval.get("decision") != decision:
        errors.append(
            f"{name}: review.approval.decision: must be {decision} when "
            f"review.status is {review_status}"
        )
    if approval.get("reviewedRecordId") != payload.get("id"):
        errors.append(
            f"{name}: review.approval.reviewedRecordId: must equal id"
        )
    if approval.get("reviewedContentVersion") != payload.get("contentVersion"):
        errors.append(
            f"{name}: review.approval.reviewedContentVersion: must equal "
            "contentVersion"
        )
    return errors


def validate_generated_question_example(payload: dict, name: str) -> list[str]:
    errors = []
    if payload.get("origin") != "generated":
        errors.append(f"{name}: origin: must be generated")

    options = payload.get("options")
    if not is_non_empty_string_list(options, 4, 4):
        errors.append(
            f"{name}: options: must contain exactly four non-empty strings"
        )
    rationales = payload.get("distractorRationales")
    if not is_non_empty_string_list(rationales, 4, 4):
        errors.append(
            f"{name}: distractorRationales: must contain exactly four "
            "non-empty strings"
        )

    answer = payload.get("correctAnswer")
    if type(answer) is not int or not isinstance(options, list) or not (
        0 <= answer < len(options)
    ):
        errors.append(
            f"{name}: correctAnswer: must be a valid zero-based option index"
        )

    difficulty = payload.get("difficulty")
    if difficulty not in GENERATED_DIFFICULTIES:
        errors.append(f"{name}: difficulty: invalid value: {difficulty}")
    bloom_level = payload.get("bloomLevel")
    if bloom_level not in GENERATED_BLOOM_LEVELS:
        errors.append(f"{name}: bloomLevel: invalid value: {bloom_level}")
    if not payload.get("sourceRefs"):
        errors.append(
            f"{name}: sourceRefs: must contain at least one source reference"
        )
    errors.extend(validate_generated_evidence_map(payload, name))
    errors.extend(validate_generated_review(payload, name))
    errors.extend(validate_generated_review_truth(payload, name))
    return errors


def validate_explanation_example(payload: dict, name: str) -> list[str]:
    errors = []
    if payload.get("generatedStudyGuidance") is not True:
        errors.append(
            f"{name}: generatedStudyGuidance: must be exactly true"
        )
    if not is_non_empty_string_list(payload.get("explanation"), 2, 3):
        errors.append(
            f"{name}: explanation: must contain two or three non-empty "
            "paragraphs"
        )
    errors.extend(validate_generated_review(payload, name))
    return errors


def validate_example_payload(name: str, payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return [f"{name}: example JSON must be an object"]

    missing = sorted(EXAMPLE_REQUIRED_KEYS.get(name, set()) - payload.keys())
    errors = []
    if missing:
        errors.append(
            f"{name}: missing required top-level keys: {', '.join(missing)}"
        )
    generated_validators = {
        "examples/lesson.example.json": validate_lesson_example,
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
    try:
        headings = {
            line.lstrip("#").strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("#")
        }
    except OSError as error:
        return [f"{path}: cannot read Markdown: {error}"]
    return [f"{path}: missing heading: {heading}" for heading in required if heading not in headings]


def validate_kit(root: Path) -> list[str]:
    errors = validate_required_files(root, REQUIRED_DOCS + REQUIRED_EXAMPLES)
    for name in REQUIRED_EXAMPLES:
        path = root / name
        if path.is_file():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                errors.append(f"{path}: invalid JSON: {error}")
                continue
            errors.extend(validate_example_payload(name, payload))
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
