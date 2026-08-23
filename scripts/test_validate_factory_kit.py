import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_factory_kit import (
    collect_template_variables,
    validate_markdown_headings,
    validate_json_file,
    validate_required_files,
)


class FactoryKitValidatorTests(unittest.TestCase):
    def test_collects_uppercase_double_brace_variables(self):
        text = "{{PROJECT_TITLE}} {{STUDY_LANGUAGE}} {{PROJECT_TITLE}}"
        self.assertEqual(
            collect_template_variables(text),
            {"PROJECT_TITLE", "STUDY_LANGUAGE"},
        )

    def test_reports_missing_required_files(self):
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_required_files(
                Path(directory),
                ("README.md", "examples/project-config.example.json"),
            )
        self.assertEqual(len(errors), 2)

    def test_reports_invalid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{", encoding="utf-8")
            self.assertTrue(validate_json_file(path))

    def test_prd_contains_complete_product_contract(self):
        path = Path("docs/study-site-factory/02-PRD-TEMPLATE.md")
        errors = validate_markdown_headings(path, (
            "Product Goal",
            "Users and Jobs",
            "Content Modes",
            "Functional Requirements",
            "Material Requirements",
            "Question Requirements",
            "Persistence",
            "Non-Functional Requirements",
            "Acceptance Criteria",
        ))
        self.assertEqual(errors, [])

    def test_ux_document_contains_every_route(self):
        path = Path("docs/study-site-factory/07-UX-AND-SYSTEM-FLOW.md")
        text = path.read_text(encoding="utf-8")
        routes = (
            "Dashboard", "Material", "Practice", "Mock Exam",
            "Question Bank", "Question Explanations", "Revision Summary",
            "Mistakes", "Bookmarks",
        )
        for route in routes:
            self.assertIn(route, text)


if __name__ == "__main__":
    unittest.main()
