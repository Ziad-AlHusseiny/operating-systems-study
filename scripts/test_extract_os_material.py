import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from pypdf import PdfWriter

from scripts.extract_os_material import (
    _classify_page,
    _source_verified_classification,
    build_payload,
    check_artifacts,
    write_artifacts,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SOURCE_IDS = [f"os-lec-{number:02d}" for number in range(1, 22)]
EXPECTED_CLASS_COUNTS = {
    "teaching": 454,
    "cover": 21,
    "divider": 21,
    "reference": 0,
    "closing": 21,
}


class ExtractOperatingSystemsMaterialTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.fixture_root = Path(self.temporary_directory.name)
        self._write_fixture_pdf("2-ch1_part2.pdf", 2)
        self._write_fixture_pdf("1-ch1_part1.pdf", 1)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write_fixture_pdf(self, filename, page_count):
        writer = PdfWriter()
        for _ in range(page_count):
            writer.add_blank_page(width=72, height=72)
        with (self.fixture_root / filename).open("wb") as output_file:
            writer.write(output_file)

    def test_natural_source_order_and_complete_page_inventory(self):
        payload = build_payload(self.fixture_root)

        self.assertEqual(
            [source["file"] for source in payload["sources"]],
            ["1-ch1_part1.pdf", "2-ch1_part2.pdf"],
        )
        self.assertEqual(
            len(payload["pages"]),
            sum(source["pages"] for source in payload["sources"]),
        )

    def test_page_numbers_are_one_based_and_text_is_preserved(self):
        payload = build_payload(self.fixture_root)

        self.assertEqual(min(page["page"] for page in payload["pages"]), 1)
        self.assertTrue(
            all(page["characterCount"] == len(page["text"]) for page in payload["pages"])
        )

    def test_reference_word_in_teaching_content_is_not_a_reference_page(self):
        self.assertEqual(
            _classify_page(
                3,
                5,
                "An invalid memory reference must be handled by the operating system.",
            ),
            "teaching",
        )

    def test_mismatched_non_teaching_override_is_flagged_for_review(self):
        classification, evidence, review = _source_verified_classification(
            {"id": "os-lec-01", "pages": 29},
            1,
            "Substantive content that does not match the verified cover page.",
        )

        self.assertEqual(classification, "teaching")
        self.assertEqual(evidence["method"], "ambiguous-override")
        self.assertEqual(review["status"], "needs-review")

    def test_changed_source_digest_cannot_use_a_non_teaching_override(self):
        classification, evidence, review = _source_verified_classification(
            {"id": "os-lec-01", "pages": 29, "sha256": "changed-source"},
            1,
            "Operating System Concepts",
        )

        self.assertEqual(classification, "teaching")
        self.assertEqual(evidence["method"], "ambiguous-override")
        self.assertEqual(review["status"], "needs-review")

    def test_check_artifacts_reports_drift_without_rewriting_committed_files(self):
        """Check mode compares every generated artifact and never repairs drift."""
        payload = build_payload(self.fixture_root)
        with tempfile.TemporaryDirectory() as directory:
            repository_root = Path(directory)
            write_artifacts(payload, repository_root)

            self.assertEqual(check_artifacts(payload, repository_root), [])

            manifest_path = repository_root / "content" / "source-manifest.json"
            manifest_path.write_text("stale manifest\n", encoding="utf-8")

            self.assertEqual(
                check_artifacts(payload, repository_root),
                ["generated artifact drift: content/source-manifest.json"],
            )
            self.assertEqual(manifest_path.read_text(encoding="utf-8"), "stale manifest\n")

    def test_committed_corpus_inventory_and_classification_evidence(self):
        payload = json.loads(
            (REPOSITORY_ROOT / "extraction" / "os-pages.json").read_text(encoding="utf-8")
        )
        audit = (REPOSITORY_ROOT / "reports" / "SOURCE_AUDIT_REPORT.md").read_text(
            encoding="utf-8"
        )

        self.assertEqual([source["id"] for source in payload["sources"]], EXPECTED_SOURCE_IDS)
        self.assertEqual(len(payload["sources"]), 21)
        self.assertEqual(len(payload["pages"]), 517)
        self.assertEqual(sum(source["pages"] for source in payload["sources"]), 517)
        class_counts = Counter(page["classification"] for page in payload["pages"])
        self.assertEqual(
            {classification: class_counts[classification] for classification in EXPECTED_CLASS_COUNTS},
            EXPECTED_CLASS_COUNTS,
        )
        self.assertTrue(
            all(page["text"].strip() for page in payload["pages"] if page["classification"] == "teaching")
        )
        self.assertTrue(
            all(
                page["classificationEvidence"]["method"] == "source-verified-override"
                for page in payload["pages"]
                if page["classification"] != "teaching"
            )
        )
        for classification, count in EXPECTED_CLASS_COUNTS.items():
            self.assertIn(f"| {classification} | {count} |", audit)


if __name__ == "__main__":
    unittest.main()
