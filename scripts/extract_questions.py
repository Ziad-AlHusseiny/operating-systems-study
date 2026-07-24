"""Extract auditable question candidates from both official PDF sources."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pdfplumber
from rapidocr_onnxruntime import RapidOCR


BANK_FILE = "Device_Configuration_and_Management_Eng_Ali_Mohamed.pdf"
PRETEST_FILE = "ITS OD 103 Pre-Test.pdf"


def normalize_text(value: str) -> str:
    """Collapse PDF/OCR whitespace without changing wording."""
    return " ".join(value.replace("\x00", " ").split())


def color_role(color: Any) -> str | None:
    """Classify the answer colors used by the official 105-question bank."""
    if not isinstance(color, (tuple, list)) or len(color) < 3:
        return None
    red, green, blue = (float(color[0]), float(color[1]), float(color[2]))
    if green > 0.28 and green > red * 2 and green > blue * 1.25:
        return "correct"
    if red > 0.38 and red > green * 2 and red > blue * 2:
        return "wrong"
    return None


def source_question_number(text: str, fallback: int) -> int:
    """Read the visible question number while keeping a deterministic fallback."""
    match = re.search(r"(?:New Test Bank\s*[·•-]?\s*)?Question\s+(\d+)", text, re.I)
    return int(match.group(1)) if match else fallback


def extract_bank(pdf_path: Path) -> list[dict[str, Any]]:
    """Return exactly 105 entries from PDF pages 2-106."""
    entries: list[dict[str, Any]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for index, page in enumerate(pdf.pages[1:], start=1):
            extracted_text = page.extract_text() or ""
            raw_lines = [
                normalize_text(line)
                for line in extracted_text.splitlines()
                if normalize_text(line)
            ]
            raw_text = normalize_text(extracted_text)
            colored_words: list[dict[str, Any]] = []
            for word in page.extract_words(extra_attrs=["non_stroking_color"]):
                role = color_role(word.get("non_stroking_color"))
                if role:
                    colored_words.append(
                        {
                            "text": normalize_text(word["text"]),
                            "role": role,
                            "x": round(float(word["x0"]), 2),
                            "y": round(float(word["top"]), 2),
                        }
                    )
            entries.append(
                {
                    "sourceId": "bank-105",
                    "sourceFile": BANK_FILE,
                    "sourcePage": index + 1,
                    "sourceQuestion": source_question_number(raw_text, index),
                    "rawText": raw_text,
                    "rawLines": raw_lines,
                    "answerMarks": colored_words,
                    "sourceImage": "",
                    "extractionMethod": "pdf-text-with-color",
                    "needsReview": not raw_text or not any(
                        mark["role"] == "correct" for mark in colored_words
                    ),
                    "reviewNotes": (
                        "No machine-readable green answer marking detected."
                        if not any(mark["role"] == "correct" for mark in colored_words)
                        else ""
                    ),
                }
            )
    if len(entries) != 105:
        raise ValueError(f"Expected 105 bank questions, extracted {len(entries)}")
    return entries


def locate_pdftoppm() -> Path:
    candidates = [
        Path(
            r"C:\Users\dark0\.cache\codex-runtimes\codex-primary-runtime"
            r"\dependencies\native\poppler\Library\bin\pdftoppm.exe"
        ),
        Path("pdftoppm.exe"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("pdftoppm.exe was not found")


def render_pretest_pages(pdf_path: Path, image_dir: Path) -> list[Path]:
    """Render the 70 pre-test question slides (PDF pages 7-76)."""
    image_dir.mkdir(parents=True, exist_ok=True)
    output_prefix = image_dir / "pretest"
    expected = [image_dir / f"pretest-{page:02d}.jpg" for page in range(7, 77)]
    if not all(path.exists() for path in expected):
        subprocess.run(
            [
                str(locate_pdftoppm()),
                "-f",
                "7",
                "-l",
                "76",
                "-jpeg",
                "-r",
                "180",
                str(pdf_path),
                str(output_prefix),
            ],
            check=True,
        )
    return expected


def ordered_ocr_lines(result: list[Any] | None) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for item in result or []:
        box, text, confidence = item
        value = normalize_text(str(text))
        if not value or value.lower() == "pre test exam":
            continue
        x = min(float(point[0]) for point in box)
        y = min(float(point[1]) for point in box)
        lines.append(
            {
                "text": value,
                "confidence": round(float(confidence), 4),
                "x": round(x, 2),
                "y": round(y, 2),
            }
        )
    return sorted(lines, key=lambda line: (line["y"], line["x"]))


def extract_answer_regions(
    image_path: Path,
    ocr_lines: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Locate red official-answer rectangles and associate page OCR text."""
    image = cv2.imread(str(image_path))
    if image is None:
        return []
    blue, green, red = cv2.split(image)
    mask = (
        (red > 130)
        & (red > green.astype(np.float32) * 1.25)
        & (red > blue.astype(np.float32) * 1.25)
    ).astype("uint8") * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _hierarchy = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    regions: list[dict[str, Any]] = []
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        if width * height <= 250 or width <= 12 or height <= 12:
            continue
        lines = [
            line
            for line in ocr_lines
            if x - 12 <= line["x"] <= x + width + 12
            and y - 12 <= line["y"] <= y + height + 12
        ]
        regions.append(
            {
                "x": int(x),
                "y": int(y),
                "width": int(width),
                "height": int(height),
                "kind": "marker" if width < 100 else "selection",
                "text": normalize_text(" ".join(line["text"] for line in lines)),
                "confidence": round(
                    sum(line["confidence"] for line in lines) / len(lines), 4
                )
                if lines
                else 0,
            }
        )
    return sorted(regions, key=lambda region: (region["y"], region["x"]))


def extract_pretest(pdf_path: Path, image_dir: Path) -> list[dict[str, Any]]:
    """Return exactly 70 OCR-backed entries from PDF pages 7-76."""
    engine = RapidOCR()
    entries: list[dict[str, Any]] = []
    for question_number, image_path in enumerate(
        render_pretest_pages(pdf_path, image_dir), start=1
    ):
        result, _elapsed = engine(str(image_path))
        lines = ordered_ocr_lines(result)
        text = normalize_text(" ".join(line["text"] for line in lines))
        average_confidence = (
            sum(line["confidence"] for line in lines) / len(lines) if lines else 0
        )
        notes: list[str] = []
        if average_confidence < 0.82:
            notes.append(f"Low average OCR confidence ({average_confidence:.2f}).")
        if len(text) < 25:
            notes.append("Too little question text was detected.")
        notes.append("Answer marking is graphical and must be cross-checked visually.")
        entries.append(
            {
                "sourceId": "pretest-70",
                "sourceFile": PRETEST_FILE,
                "sourcePage": question_number + 6,
                "sourceQuestion": question_number,
                "rawText": text,
                "ocrLines": lines,
                "answerMarks": [],
                "answerRegions": extract_answer_regions(image_path, lines),
                "sourceImage": str(
                    image_path.relative_to(image_dir.parent.parent).as_posix()
                ),
                "extractionMethod": "render-and-rapidocr",
                "needsReview": average_confidence < 0.82 or len(text) < 25,
                "reviewNotes": " ".join(notes),
            }
        )
    if len(entries) != 70:
        raise ValueError(f"Expected 70 pre-test questions, extracted {len(entries)}")
    return entries


def write_raw(entries: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def find_source(source_root: Path, filename: str) -> Path:
    candidates = [
        source_root / filename,
        source_root.parent.parent / filename,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"Could not find {filename}")


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=repo_root)
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "extraction" / "raw-questions.json",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=repo_root / "extraction" / "source-pages",
    )
    parser.add_argument(
        "--reuse-pretest",
        action="store_true",
        help="Reuse pre-test OCR entries already present in the output file.",
    )
    args = parser.parse_args()

    bank_path = find_source(args.source_root.resolve(), BANK_FILE)
    pretest_path = find_source(args.source_root.resolve(), PRETEST_FILE)
    pretest_entries: list[dict[str, Any]]
    if args.reuse_pretest and args.output.exists():
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        pretest_entries = [
            item for item in existing if item.get("sourceId") == "pretest-70"
        ]
        if len(pretest_entries) != 70:
            raise ValueError("Existing output does not contain 70 pre-test entries")
        for entry in pretest_entries:
            source_image = Path(entry["sourceImage"])
            if source_image.is_absolute():
                try:
                    entry["sourceImage"] = str(
                        source_image.relative_to(repo_root).as_posix()
                    )
                except ValueError:
                    entry["sourceImage"] = str(
                        (Path("extraction") / "source-pages" / source_image.name).as_posix()
                    )
                source_image = repo_root / entry["sourceImage"]
            else:
                source_image = repo_root / source_image
            if not entry.get("answerRegions"):
                entry["answerRegions"] = extract_answer_regions(
                    source_image, entry.get("ocrLines", [])
                )
    else:
        pretest_entries = extract_pretest(pretest_path, args.image_dir)
    entries = extract_bank(bank_path) + pretest_entries
    write_raw(entries, args.output)
    print(f"Wrote {len(entries)} raw entries to {args.output}")


if __name__ == "__main__":
    main()
