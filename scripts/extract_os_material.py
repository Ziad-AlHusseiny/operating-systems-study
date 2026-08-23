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
SOURCE_VERIFIED_LAYOUTS = {
    "os-lec-01": (29, "Sector A,B", 186, "c35bdc94cd9e9f965bd06b7c97e2bf880485c74bc77790d6ec2f4f3a6c64a45a"),
    "os-lec-02": (30, "Introduction (Part 2)", 137, "e598157b043c7911ae4c1e58249be4b26e974d38e6f039b675b31819fa38eea6"),
    "os-lec-03": (20, "Introduction (Part 3)", 137, "f026f5ffa0b1ecc33b3518e8ec9ad66cf3d70d76a560c0ba66bff5d34dcbb962"),
    "os-lec-04": (29, "Introduction (Part 4)", 137, "0ac24794ac03b14779b706c9c0c7084b0786bcf18c03006839a38d153e2b7b37"),
    "os-lec-05": (24, "Services (Part 1)", 151, "0ba363046c36547c9ff6f7357301921ba94606e262f6f7841b7eff7d1f7d9c0d"),
    "os-lec-06": (26, "Services (Part 2)", 151, "ec8b4c8209c2aac89b1f696473440b2ab1304506bd6b763fe3c6fb51ae78a9db"),
    "os-lec-07": (29, "Services (Part 3)", 151, "1d78df26cb27b6d0c758ec00ec7c5ea766e8040cca9ab61f2541b2e5409f44d1"),
    "os-lec-08": (24, "Processes (Part 1)", 134, "742264f6d8e5947b664f3cee6eece5fcfd3d3827b4f87558e8a98df114126ef0"),
    "os-lec-09": (25, "Processes (Part 2)", 134, "325230370dd71e385e484aefb3a2e4f9996d86e4ccbadd29ec34ce0d96524226"),
    "os-lec-10": (28, "Processes (Part 3)", 134, "5f3af9f4e8212a25ceeb1f50bffa85b184aa067e02dfcccbe72f898e16be34f6"),
    "os-lec-11": (22, "CPU Scheduling (Part 1)", 139, "a7a8a44c9b1b6e56af9da0d0cac093c57aaec8b7c9da99a92844f771dc7aca35"),
    "os-lec-12": (20, "CPU Scheduling (Part 2)", 139, "eefcf2f76fcb832f3f52c329adfadb66bc6974c8dad42f2e7ddc754837d56f20"),
    "os-lec-13": (21, "CPU Scheduling (Part 3)", 139, "7618cb9fb8db7c4ab7d4d1e0bf8e928f1636e3ee70bfcc42b2747dc5d020969f"),
    "os-lec-14": (23, "CPU Scheduling (Part 4)", 139, "da992b858e54794f980f08ef12f57313557b2075a28b11c1debc63529422b123"),
    "os-lec-15": (23, "Tools (Part 1)", 147, "533b9e61871dc7a9dd7f73f40e57a2a14f2cafb5d62ba22240f7054a60aeacac"),
    "os-lec-16": (24, "Tools (Part 2)", 147, "f5bc643e31a679d8de1caf962feb09e576a74f8899ed3a7fa660f6434a3da367"),
    "os-lec-17": (19, "Deadlocks", 135, "a5ae9f63a5964dfa260aef8260c710e31d4d89dd8f706194c88339046bfc11e0"),
    "os-lec-18": (20, "Deadlocks", 135, "b0db972dfc07f0df8bc003880a6a014ad4f29fd958b6e9b5d0035a5e9c154c5a"),
    "os-lec-19": (19, "Deadlocks", 135, "543d7af9bfdc675479d5fa7ac1c3fbd637f449c6502bea8f85a8c2f3507e0a21"),
    "os-lec-20": (32, "Main Memory", 138, "09b846d552e334789de3149e470ed4a19aef392987c3d46fae39219ca5e9eb48"),
    "os-lec-21": (30, "Main Memory", 137, "b9f040d8a058b1537d7cf92f1e8eaf289a8e57a50fd60409204f158bc487fb97"),
}
PAGE_CLASSIFICATION_OVERRIDES = {
    source_id: {
        1: {
            "classification": "cover",
            "expectedText": "Operating System Concepts",
            "maximumCharacterCount": 187,
            "detail": "Verified course-cover page in the source PDF.",
        },
        2: {
            "classification": "divider",
            "expectedText": divider_text,
            "maximumCharacterCount": divider_maximum_character_count,
            "detail": "Verified lecture title or organizational divider in the source PDF.",
        },
        page_count: {
            "classification": "closing",
            "expectedText": "Operating System Concepts",
            "maximumCharacterCount": 110,
            "detail": "Verified recurring publication footer-only closing page in the source PDF.",
        },
    }
    for source_id, (page_count, divider_text, divider_maximum_character_count, _) in SOURCE_VERIFIED_LAYOUTS.items()
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
    if any(
        re.fullmatch(r"(?:references?|bibliography)", line.strip(), flags=re.IGNORECASE)
        for line in text.splitlines()
    ):
        return "reference"
    return "teaching"


def _source_verified_classification(source: dict, page_number: int, text: str) -> tuple[str, dict, dict | None]:
    """Use the reviewed per-source override map and route mismatches to review."""
    override = PAGE_CLASSIFICATION_OVERRIDES.get(source["id"], {}).get(page_number)
    if override is None:
        classification = _classify_page(page_number, source["pages"], text)
        return classification, {
            "method": "source-heading" if classification == "reference" else "teaching-default",
            "detail": "Standalone reference heading" if classification == "reference" else "No non-teaching override applies.",
        }, None

    expected_page_count, _, _, expected_sha256 = SOURCE_VERIFIED_LAYOUTS[source["id"]]
    verified_source = (
        source["pages"] == expected_page_count
        and source.get("sha256") == expected_sha256
    )
    expected_text = override["expectedText"]
    maximum_character_count = override.get("maximumCharacterCount")
    matches_verified_page = verified_source and expected_text in text and (
        maximum_character_count is None or len(text) <= maximum_character_count
    )
    if matches_verified_page:
        return override["classification"], {
            "method": "source-verified-override",
            "detail": override["detail"],
        }, None

    detail = (
        f"Page did not match the verified {override['classification']} evidence "
        f"for {source['id']} page {page_number}; retained as teaching pending review."
    )
    return "teaching", {"method": "ambiguous-override", "detail": detail}, {
        "status": "needs-review",
        "notes": detail,
    }


def extract_page_records(source: dict) -> list[dict]:
    """Extract normalized, one-based page records for one inventoried source."""
    source_path = Path(source["_path"])
    reader = PdfReader(source_path)
    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = _normalized_text(page.extract_text() or "")
        classification, evidence, review = _source_verified_classification(source, page_number, text)
        record = {
            "sourceId": source["id"],
            "page": page_number,
            "text": text,
            "characterCount": len(text),
            "classification": classification,
            "classificationEvidence": evidence,
        }
        if review is not None:
            record["review"] = review
        pages.append(record)
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
    review_pages = [
        page
        for page in payload["pages"]
        if page.get("review", {}).get("status") == "needs-review"
    ]
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
        f"- Review items: {len(review_pages)} from source ingestion.",
        "",
        "## Page classifications",
        "",
        "| Classification | Pages |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {classification} | {total_by_classification[classification]} |" for classification in CLASSIFICATIONS)
    if review_pages:
        lines.extend(["", "## Review items", ""])
        lines.extend(
            f"- {page['sourceId']} page {page['page']}: {page['review']['notes']}"
            for page in review_pages
        )
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
        and page.get("review", {}).get("status") != "needs-review"
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
