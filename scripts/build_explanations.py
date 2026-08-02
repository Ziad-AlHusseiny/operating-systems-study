import json
import re
from pathlib import Path


ARABIC = re.compile(r"[\u0600-\u06ff]")


def validate_entry(question_id: str, entry: dict) -> list[str]:
    errors = []
    if not isinstance(entry.get("translation"), str) or not ARABIC.search(entry["translation"]):
        errors.append(f"{question_id}: translation must contain Arabic")
    paragraphs = entry.get("explanation")
    if not isinstance(paragraphs, list) or len(paragraphs) not in (2, 3):
        errors.append(f"{question_id}: explanation must have 2 or 3 paragraphs")
    elif not all(isinstance(value, str) and ARABIC.search(value) for value in paragraphs):
        errors.append(f"{question_id}: every explanation paragraph must contain Arabic")
    if not isinstance(entry.get("note"), str) or not ARABIC.search(entry["note"]):
        errors.append(f"{question_id}: note must contain Arabic")
    return errors


def build_payload(question_path: Path, part_paths: list[Path]) -> dict:
    questions = json.loads(question_path.read_text(encoding="utf-8"))["questions"]
    expected_ids = {question["id"] for question in questions}
    merged = {}
    for part_path in part_paths:
        for question_id, entry in json.loads(part_path.read_text(encoding="utf-8")).items():
            if question_id in merged:
                raise ValueError(f"duplicate explanation ID: {question_id}")
            merged[question_id] = entry
    if set(merged) != expected_ids:
        missing = sorted(expected_ids - set(merged))
        unknown = sorted(set(merged) - expected_ids)
        raise ValueError(f"coverage mismatch: missing={missing}, unknown={unknown}")
    errors = [error for question_id, entry in merged.items() for error in validate_entry(question_id, entry)]
    if errors:
        raise ValueError("\n".join(errors))
    return {
        "version": 1,
        "language": "ar",
        "generatedStudyGuidance": True,
        "explanations": dict(sorted(merged.items())),
    }


def main() -> None:
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
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Validated {len(payload['explanations'])} Arabic explanations.")


if __name__ == "__main__":
    main()
