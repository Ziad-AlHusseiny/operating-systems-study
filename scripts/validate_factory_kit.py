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
        "examTips", "recap", "sourceRefs", "review"
    },
    "examples/generated-question.example.json": {
        "id", "origin", "type", "prompt", "options", "correctAnswer",
        "rationale", "distractorRationales", "difficulty", "bloomLevel",
        "learningObjectiveId", "sourceRefs", "review"
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
            if not isinstance(value, list):
                errors.append(f"{key_path}: must be an array")
            else:
                for index, reference in enumerate(value):
                    errors.extend(
                        validate_source_reference(reference, f"{key_path}[{index}]")
                    )
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
    errors.extend(validate_generated_review(payload, name))
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
    errors.extend(validate_generated_review(payload, name))
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
    errors.extend(validate_source_references(payload, name))
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
