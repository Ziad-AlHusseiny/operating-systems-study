import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_factory_kit import (
    EXAMPLE_REQUIRED_KEYS,
    REQUIRED_DOCS,
    REQUIRED_EXAMPLES,
    collect_template_variables,
    validate_markdown_headings,
    validate_json_file,
    validate_required_files,
    validate_kit,
)


class FactoryKitValidatorTests(unittest.TestCase):
    def make_complete_kit(self, root, source_manifest, official_question):
        for name in REQUIRED_DOCS:
            (root / name).write_text("# placeholder\n", encoding="utf-8")
        for name in REQUIRED_EXAMPLES:
            payload = {}
            if name == "examples/source-manifest.example.json":
                payload = source_manifest
            elif name == "examples/official-question.example.json":
                payload = official_question
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(json.dumps(payload), encoding="utf-8")

    def test_source_and_official_question_examples_have_required_keys(self):
        root = Path("docs/study-site-factory")
        for relative, required in EXAMPLE_REQUIRED_KEYS.items():
            payload = json.loads(
                (root / relative).read_text(encoding="utf-8")
            )
            self.assertTrue(required.issubset(payload))

    def test_reports_missing_top_level_keys_in_required_examples(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_complete_kit(
                root,
                {"sources": []},
                {
                    "id": "q-001", "origin": "official", "type": "mcq",
                    "prompt": "Prompt", "topic": "Topic", "correctAnswer": 0,
                    "sourceRefs": [], "needsReview": False, "reviewNotes": "",
                },
            )
            errors = validate_kit(root)
        self.assertIn(
            "examples/source-manifest.example.json: missing required top-level "
            "keys: version",
            errors,
        )

    def test_reports_invalid_source_reference_location_type(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_complete_kit(
                root,
                {"version": "1.0", "sources": []},
                {
                    "id": "q-001", "origin": "official", "type": "mcq",
                    "prompt": "Prompt", "topic": "Topic", "correctAnswer": 0,
                    "sourceRefs": [
                        {"sourceId": "source-01", "locationType": "chapter", "location": 1}
                    ],
                    "needsReview": False, "reviewNotes": "",
                },
            )
            errors = validate_kit(root)
        self.assertIn(
            "examples/official-question.example.json: sourceRefs[0]: invalid "
            "locationType: chapter",
            errors,
        )

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

    def test_prd_excludes_review_items_from_every_mock_exam_pool(self):
        text = Path("docs/study-site-factory/02-PRD-TEMPLATE.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "Items marked `Needs review — unscored` are excluded from every "
            "Mock Exam pool.",
            text,
        )
        self.assertIn(
            "Generated questions may enter a Mock Exam only when they are "
            "approved and scoreable",
            text,
        )

    def test_content_contract_defines_complete_material_section_records(self):
        text = Path(
            "docs/study-site-factory/04-CONTENT-AND-DATA-CONTRACTS.md"
        ).read_text(encoding="utf-8")
        self.assertIn("## Material Sections", text)
        for field in (
            "`summaries`", "`terms`", "`examples`", "`mistakes`",
            "`examTips`", "`recaps`", "`sourceRefs`", "`linkedQuestionIds`",
        ):
            self.assertIn(field, text)

    def test_content_contract_defines_generated_question_quality_and_duplicates(self):
        text = Path(
            "docs/study-site-factory/04-CONTENT-AND-DATA-CONTRACTS.md"
        ).read_text(encoding="utf-8")
        self.assertIn("## Generated Question Quality and Duplication", text)
        for field in (
            "`difficulty`", "`cognitiveLevel`", "`evidenceMap`",
            "`qualityState`", "`reviewState`", "`duplicateComparison`",
            "`duplicateDisposition`",
        ):
            self.assertIn(field, text)
        self.assertIn("Unicode NFKC", text)
        self.assertIn("lexicographic question ID order", text)

    def test_content_contract_defines_review_approval_records_and_scoring_effects(self):
        text = Path(
            "docs/study-site-factory/04-CONTENT-AND-DATA-CONTRACTS.md"
        ).read_text(encoding="utf-8")
        self.assertIn("| Review approval |", text)
        for field in (
            "`status`", "`decision`", "`reviewer`", "`reviewedAt`",
            "`reason`", "`notes`", "`reviewedRecordId`",
            "`reviewedContentVersion`",
        ):
            self.assertIn(field, text)
        self.assertIn("only when both `qualityState` and `reviewState` are `approved`", text)


if __name__ == "__main__":
    unittest.main()
