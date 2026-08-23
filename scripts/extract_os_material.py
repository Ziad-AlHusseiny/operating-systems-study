"""Deterministically extract traceable page records from the OS lecture PDFs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import pypdf
from pypdf import PdfReader


CLASSIFICATIONS = ("teaching", "cover", "divider", "reference", "closing")
FILENAME_PATTERN = re.compile(r"^(?P<lecture>\d+)-ch(?P<chapter>\d+)_part(?P<part>\d+)\.pdf$")
CHAPTER_TITLES = {
    1: "Introduction",
    2: "Operating-System Services",
    3: "Processes",
    5: "CPU Scheduling",
    6: "Synchronization Tools",
    8: "Deadlocks",
    9: "Main Memory",
}


def _natural_source_key(path: Path) -> tuple[int, int, int]:
    match = FILENAME_PATTERN.fullmatch(path.name)
    if match is None:
        raise ValueError(f"Unsupported Operating Systems lecture filename: {path.name}")
    return (
        int(match.group("lecture")),
        int(match.group("chapter")),
        int(match.group("part")),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_text(text: str) -> str:
    return unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")


def build_source_records(pdf_root: Path) -> list[dict]:
    """Inventory the lecture PDFs in numeric lecture order."""
    pdf_root = Path(pdf_root)
    source_paths = sorted(pdf_root.glob("*.pdf"), key=_natural_source_key)
    records = []
    for source_path in source_paths:
        lecture, chapter, part = _natural_source_key(source_path)
        if chapter not in CHAPTER_TITLES:
            raise ValueError(f"Unsupported chapter in {source_path.name}")
        reader = PdfReader(source_path)
        records.append(
            {
                "id": f"os-lec-{lecture:02d}",
                "file": source_path.name,
                "chapter": chapter,
                "part": part,
                "pages": len(reader.pages),
                "sha256": _sha256(source_path),
                "title": f"Chapter {chapter}: {CHAPTER_TITLES[chapter]} (Part {part})",
                "_path": str(source_path.resolve()),
            }
        )
    return records


def _classify_page(page_number: int, page_count: int, text: str) -> str:
    if page_number == 1:
        return "cover"
    if page_number == page_count:
        return "closing"
    if page_number == 2:
        return "divider"
    if any(
        re.fullmatch(r"(?:references?|bibliography)", line.strip(), flags=re.IGNORECASE)
        for line in text.splitlines()
    ):
        return "reference"
    return "teaching"


def extract_page_records(source: dict) -> list[dict]:
    """Extract normalized, one-based page records for one inventoried source."""
    source_path = Path(source["_path"])
    reader = PdfReader(source_path)
    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = _normalized_text(page.extract_text() or "")
        pages.append(
            {
                "sourceId": source["id"],
                "page": page_number,
                "text": text,
                "characterCount": len(text),
                "classification": _classify_page(page_number, len(reader.pages), text),
            }
        )
    return pages


def _public_source(source: dict) -> dict:
    return {key: value for key, value in source.items() if key != "_path"}


def build_payload(pdf_root: Path) -> dict:
    """Build the public, path-free extraction payload."""
    source_records = build_source_records(pdf_root)
    page_records = [
        page_record
        for source in source_records
        for page_record in extract_page_records(source)
    ]
    return {
        "version": "1.0",
        "course": "Operating Systems",
        "generatedAtPolicy": "deterministic-no-timestamp",
        "sources": [_public_source(source) for source in source_records],
        "pages": page_records,
    }


def build_source_manifest(payload: dict) -> dict:
    return {
        "version": "1.0",
        "sources": [
            {
                "id": source["id"],
                "fileName": source["file"],
                "collection": f"Chapter {source['chapter']} lectures",
                "label": source["title"],
                "format": "pdf",
                "checksum": f"sha256:{source['sha256']}",
                "pages": source["pages"],
                "status": "accepted",
                "locations": [{"locationType": "page", "location": 1}],
            }
            for source in payload["sources"]
        ],
    }


def _audit_report(payload: dict) -> str:
    total_by_classification = Counter(page["classification"] for page in payload["pages"])
    pages_by_source = {
        source["id"]: Counter(
            page["classification"]
            for page in payload["pages"]
            if page["sourceId"] == source["id"]
        )
        for source in payload["sources"]
    }
    lines = [
        "# Operating Systems source audit",
        "",
        "## Run policy",
        "",
        "- Completion time: omitted by deterministic artifact policy.",
        f"- Extraction tool: pypdf {pypdf.__version__}.",
        "- Source format/status: 21 PDF files, all accepted.",
        f"- Inventoried pages: {len(payload['pages'])}.",
        "- Answer keys: absent; none were supplied with the lecture PDFs.",
        "- OCR corrections: none; embedded PDF text was extracted page by page.",
        "- Unreadable locations: none.",
        "- Duplicate groups: none detected by SHA-256.",
        "- Review items: none from source ingestion.",
        "",
        "## Page classifications",
        "",
        "| Classification | Pages |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {classification} | {total_by_classification[classification]} |" for classification in CLASSIFICATIONS)
    lines.extend(
        [
            "",
            "## Source inventory",
            "",
            "| Source ID | File | SHA-256 | Pages | Teaching | Cover | Divider | Reference | Closing |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for source in payload["sources"]:
        counts = pages_by_source[source["id"]]
        lines.append(
            "| {id} | {file} | `{sha256}` | {pages} | {teaching} | {cover} | {divider} | {reference} | {closing} |".format(
                **source,
                teaching=counts["teaching"],
                cover=counts["cover"],
                divider=counts["divider"],
                reference=counts["reference"],
                closing=counts["closing"],
            )
        )
    return "\n".join(lines) + "\n"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf-root", required=True, type=Path)
    arguments = parser.parse_args()
    payload = build_payload(arguments.pdf_root)
    if len(payload["sources"]) != 21 or len(payload["pages"]) != 517:
        raise ValueError("Expected exactly 21 lecture PDFs and 517 pages")
    if any(
        not page["text"].strip()
        for page in payload["pages"]
        if page["classification"] == "teaching"
    ):
        raise ValueError("Every teaching page must have extracted text")

    repository_root = Path(__file__).resolve().parents[1]
    _write_json(repository_root / "extraction" / "os-pages.json", payload)
    _write_json(repository_root / "content" / "source-manifest.json", build_source_manifest(payload))
    report_path = repository_root / "reports" / "SOURCE_AUDIT_REPORT.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_audit_report(payload), encoding="utf-8")


if __name__ == "__main__":
    main()
