import argparse
import json
import re
from pathlib import Path


ARABIC = re.compile(r"[\u0600-\u06ff]")
CONFLICT = re.compile(r"تعارض|اختلاف|conflict", re.IGNORECASE)
DIFFERENTIAL = re.compile(
    r"(?<![A-Za-z0-9_])Differential(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
INCREMENTAL = re.compile(
    r"(?<![A-Za-z0-9_])Incremental(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
TOKEN_CHARACTERS = r"A-Za-z0-9_\u0600-\u06ff"
ANSWER_PHRASE = re.compile(
    rf"(?<![{TOKEN_CHARACTERS}])"
    rf"(?:"
    rf"(?:the\s+)?(?:correct\s+)?answer"
    rf"|الإجابة(?:\s+الصحيحة)?"
    rf"|(?:الخيار|الاختيار)\s+الصحيح"
    rf")"
    rf"(?![{TOKEN_CHARACTERS}])",
    re.IGNORECASE,
)
TECHNICAL_LABEL = re.compile(
    rf"(?<![{TOKEN_CHARACTERS}])"
    rf"[\"'“”«»‘’]?\s*"
    rf"(?:(?:الـ|ال)\s*)?"
    rf"[\"'“”«»‘’]?\s*"
    rf"(?:Differential|Incremental)"
    rf"(?![{TOKEN_CHARACTERS}])"
    rf"(?:\s*[\"'“”«»‘’])?",
    re.IGNORECASE,
)
SENTENCE_BOUNDARY = re.compile(r"[.!?؟؛\r\n]+")
MAX_SELECTION_SPAN = 120
REQUIRED_FIELDS = {"translation", "explanation", "note"}
PART_RANGES = {
    "q001-026.json": (1, 26),
    "q027-052.json": (27, 52),
    "q053-078.json": (53, 78),
    "q079-103.json": (79, 103),
}
QUESTION_ID = re.compile(r"q-(\d{3})$")


def is_non_empty_arabic(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and bool(ARABIC.search(value))


def has_answer_selection(value: str) -> bool:
    for sentence in SENTENCE_BOUNDARY.split(value):
        answer_matches = list(ANSWER_PHRASE.finditer(sentence))
        label_matches = list(TECHNICAL_LABEL.finditer(sentence))
        for answer_match in answer_matches:
            for label_match in label_matches:
                gap = max(
                    label_match.start() - answer_match.end(),
                    answer_match.start() - label_match.end(),
                    0,
                )
                if gap <= MAX_SELECTION_SPAN:
                    return True
    return False


def validate_entry(question_id: str, entry: object) -> list[str]:
    if not isinstance(entry, dict):
        return [f"{question_id}: entry must be an object"]

    errors: list[str] = []
    if set(entry) != REQUIRED_FIELDS:
        errors.append(
            f"{question_id}: fields must be exactly translation, explanation, note"
        )
    if not is_non_empty_arabic(entry.get("translation")):
        errors.append(f"{question_id}: translation must be a non-empty Arabic string")
    paragraphs = entry.get("explanation")
    if not isinstance(paragraphs, list) or len(paragraphs) not in (2, 3):
        errors.append(f"{question_id}: explanation must have 2 or 3 paragraphs")
    elif not all(is_non_empty_arabic(value) for value in paragraphs):
        errors.append(
            f"{question_id}: every explanation paragraph must be a non-empty Arabic string"
        )
    if not is_non_empty_arabic(entry.get("note")):
        errors.append(f"{question_id}: note must be a non-empty Arabic string")

    if question_id == "q-103":
        paragraph_values = paragraphs if isinstance(paragraphs, list) else []
        values = [entry.get("translation"), *paragraph_values, entry.get("note")]
        combined = " ".join(value for value in values if isinstance(value, str))
        if not CONFLICT.search(combined):
            errors.append("q-103 must mention the unresolved source conflict")
        if not DIFFERENTIAL.search(combined) or not INCREMENTAL.search(combined):
            errors.append("q-103 must mention both Differential and Incremental")
        if has_answer_selection(combined):
            errors.append("q-103 must not select an answer")
    return errors


def validate_part_id(part_path: Path, question_id: str) -> None:
    assigned_range = PART_RANGES.get(part_path.name)
    if assigned_range is None:
        expected_names = ", ".join(sorted(PART_RANGES))
        raise ValueError(
            f"unknown explanation part filename: {part_path.name}; expected {expected_names}"
        )
    match = QUESTION_ID.fullmatch(question_id)
    lower, upper = assigned_range
    if match is None or not lower <= int(match.group(1)) <= upper:
        raise ValueError(
            f"{question_id}: ID is outside assigned range "
            f"q-{lower:03d}..q-{upper:03d} for {part_path.name}"
        )


def build_payload(question_path: Path, part_paths: list[Path]) -> dict:
    questions = json.loads(question_path.read_text(encoding="utf-8"))["questions"]
    expected_ids = {question["id"] for question in questions}
    merged = {}
    for part_path in sorted(part_paths, key=lambda path: path.name):
        part = json.loads(part_path.read_text(encoding="utf-8"))
        if not isinstance(part, dict):
            raise ValueError(f"{part_path.name}: part payload must be an object")
        for question_id, entry in part.items():
            validate_part_id(part_path, question_id)
            if question_id in merged:
                raise ValueError(f"duplicate explanation ID: {question_id}")
            merged[question_id] = entry
    if set(merged) != expected_ids:
        missing = sorted(expected_ids - set(merged))
        unknown = sorted(set(merged) - expected_ids)
        raise ValueError(f"coverage mismatch: missing={missing}, unknown={unknown}")
    errors = [
        error
        for question_id, entry in sorted(merged.items())
        for error in validate_entry(question_id, entry)
    ]
    if errors:
        raise ValueError("\n".join(errors))
    return {
        "version": 1,
        "language": "ar",
        "generatedStudyGuidance": True,
        "explanations": dict(sorted(merged.items())),
    }


def render_payload(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Arabic study explanations.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare committed output with a fresh build without writing files",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    payload = build_payload(
        root / "study-website" / "data" / "questions.json",
        [
            root / "content" / "explanations-ar" / "q001-026.json",
            root / "content" / "explanations-ar" / "q027-052.json",
            root / "content" / "explanations-ar" / "q053-078.json",
            root / "content" / "explanations-ar" / "q079-103.json",
        ],
    )
    output_path = root / "study-website" / "data" / "explanations-ar.json"
    rendered = render_payload(payload)
    if args.check:
        if output_path.read_text(encoding="utf-8") != rendered:
            raise ValueError(
                "committed Arabic explanation payload is out of date; "
                "run python scripts/build_explanations.py"
            )
        print(
            f"Validated {len(payload['explanations'])} Arabic explanations; "
            "committed payload is current."
        )
        return

    output_path.write_text(rendered, encoding="utf-8")
    print(f"Validated {len(payload['explanations'])} Arabic explanations.")


if __name__ == "__main__":
    main()
