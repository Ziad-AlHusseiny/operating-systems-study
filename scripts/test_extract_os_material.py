import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter

from scripts.extract_os_material import _classify_page, build_payload


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


if __name__ == "__main__":
    unittest.main()
