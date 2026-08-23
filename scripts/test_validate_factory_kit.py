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
    validate_example_payload,
    validate_json_file,
    validate_required_files,
    validate_kit,
)


class FactoryKitValidatorTests(unittest.TestCase):
    source_ref = {
        "sourceId": "source-01", "locationType": "page", "location": 12
    }
    evidence_targets = (
        "prompt", "correctAnswer", "rationale",
        "options[0]", "options[1]", "options[2]", "options[3]",
        "distractorRationales[0]", "distractorRationales[1]",
        "distractorRationales[2]", "distractorRationales[3]",
    )

    def make_generated_question(self, review_status="human-reviewed"):
        states = {
            "draft": ("draft", "unreviewed", True, None),
            "validated": ("validated", "unreviewed", True, None),
            "human-reviewed": ("approved", "approved", False, "approved"),
            "needs-review": (
                "needs-review", "needs-review", True, "needs-review"
            ),
            "rejected": ("rejected", "rejected", True, "rejected"),
        }
        quality, canonical_review, needs_review, decision = states[review_status]
        review = {"status": review_status}
        if decision is not None:
            review["approval"] = {
                "status": "completed",
                "decision": decision,
                "reviewedRecordId": "gq-review-001",
                "reviewedContentVersion": "1.0.0",
            }
        return {
            "id": "gq-review-001",
            "origin": "generated",
            "type": "mcq",
            "prompt": "Prompt",
            "options": ["A", "B", "C", "D"],
            "correctAnswer": 0,
            "rationale": "Rationale",
            "distractorRationales": ["A", "B", "C", "D"],
            "difficulty": "medium",
            "bloomLevel": "apply",
            "cognitiveLevel": "apply",
            "learningObjectiveId": "objective-review-001",
            "sourceRefs": [self.source_ref],
            "evidenceMap": [
                {
                    "claimId": f"claim-{index}",
                    "target": target,
                    "sourceRefs": [self.source_ref],
                    "support": "direct",
                }
                for index, target in enumerate(self.evidence_targets)
            ],
            "contentVersion": "1.0.0",
            "qualityState": quality,
            "reviewState": canonical_review,
            "needsReview": needs_review,
            "reviewNotes": "",
            "review": review,
        }

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

    def test_examples_have_required_keys(self):
        root = Path("docs/study-site-factory")
        for relative, required in EXAMPLE_REQUIRED_KEYS.items():
            with self.subTest(relative=relative):
                payload = json.loads(
                    (root / relative).read_text(encoding="utf-8")
                )
                self.assertTrue(required.issubset(payload))

    def test_generated_mcq_example_has_complete_answer_contract(self):
        payload = json.loads(
            Path(
                "docs/study-site-factory/examples/"
                "generated-question.example.json"
            ).read_text(encoding="utf-8")
        )

        self.assertEqual(payload["origin"], "generated")
        self.assertEqual(len(payload["options"]), 4)
        self.assertEqual(len(payload["distractorRationales"]), 4)
        self.assertIsInstance(payload["correctAnswer"], int)
        self.assertIn(payload["correctAnswer"], range(4))
        self.assertGreaterEqual(len(payload["sourceRefs"]), 1)

    def test_lesson_rejects_explanation_outside_two_to_five_paragraphs(self):
        for explanation in (["Only one."], ["One.", "", "Three."], [
            "One.", "Two.", "Three.", "Four.", "Five.", "Six."
        ]):
            with self.subTest(explanation=explanation):
                errors = validate_example_payload(
                    "examples/lesson.example.json",
                    {
                        "explanation": explanation,
                        "recap": ["One.", "Two.", "Three."],
                        "review": {"status": "draft"},
                    },
                )
                self.assertIn(
                    "examples/lesson.example.json: explanation: must contain "
                    "two to five non-empty paragraphs",
                    errors,
                )

    def test_lesson_rejects_recap_outside_three_to_seven_points(self):
        for recap in (["One.", "Two."], ["One.", "", "Three."], [
            "One.", "Two.", "Three.", "Four.", "Five.", "Six.",
            "Seven.", "Eight."
        ]):
            with self.subTest(recap=recap):
                errors = validate_example_payload(
                    "examples/lesson.example.json",
                    {
                        "explanation": ["One.", "Two."],
                        "recap": recap,
                        "review": {"status": "draft"},
                    },
                )
                self.assertIn(
                    "examples/lesson.example.json: recap: must contain three "
                    "to seven non-empty strings",
                    errors,
                )

    def test_lesson_requires_canonical_compilation_fields(self):
        self.assertTrue({
            "objectiveIds", "body", "needsReview", "reviewNotes"
        }.issubset(EXAMPLE_REQUIRED_KEYS["examples/lesson.example.json"]))

    def test_lesson_rejects_canonical_body_or_objective_mapping_drift(self):
        payload = {
            "objectiveIds": ["objective-dhcp"],
            "learningObjectives": [{"id": "objective-dns"}],
            "explanation": ["First paragraph.", "Second paragraph."],
            "body": "First paragraph. Second paragraph.",
            "recap": ["One.", "Two.", "Three."],
            "review": {"status": "draft"},
        }

        errors = validate_example_payload(
            "examples/lesson.example.json", payload
        )

        self.assertIn(
            "examples/lesson.example.json: learningObjectives: IDs must "
            "equal objectiveIds in the same order",
            errors,
        )
        self.assertIn(
            "examples/lesson.example.json: body: must equal explanation "
            "paragraphs joined with two newlines",
            errors,
        )

    def test_lesson_rejects_empty_canonical_objective_ids(self):
        errors = validate_example_payload(
            "examples/lesson.example.json",
            {
                "objectiveIds": [""],
                "learningObjectives": [{"id": ""}],
                "explanation": ["First paragraph.", "Second paragraph."],
                "body": "First paragraph.\n\nSecond paragraph.",
                "recap": ["One.", "Two.", "Three."],
                "review": {"status": "draft"},
            },
        )

        self.assertIn(
            "examples/lesson.example.json: learningObjectives: IDs must "
            "equal non-empty objectiveIds in the same order",
            errors,
        )

    def test_generated_mcq_rejects_invalid_shape_and_rubric_values(self):
        payload = {
            "origin": "official",
            "type": "mcq",
            "options": ["A", "B", "C"],
            "correctAnswer": 3,
            "distractorRationales": ["A", "B", "C"],
            "difficulty": "extreme",
            "bloomLevel": "understand",
            "sourceRefs": [],
            "review": {"status": "queued"},
        }

        errors = validate_example_payload(
            "examples/generated-question.example.json", payload
        )

        for error in (
            "examples/generated-question.example.json: origin: must be generated",
            "examples/generated-question.example.json: options: must contain exactly four non-empty strings",
            "examples/generated-question.example.json: distractorRationales: must contain exactly four non-empty strings",
            "examples/generated-question.example.json: correctAnswer: must be a valid zero-based option index",
            "examples/generated-question.example.json: difficulty: invalid value: extreme",
            "examples/generated-question.example.json: bloomLevel: invalid value: understand",
            "examples/generated-question.example.json: sourceRefs: must contain at least one source reference",
            "examples/generated-question.example.json: review.status: invalid value: queued",
        ):
            with self.subTest(error=error):
                self.assertIn(error, errors)

    def test_generated_question_requires_complete_claim_evidence(self):
        payload = self.make_generated_question()
        payload["evidenceMap"] = [{
            "claimId": "claim-prompt",
            "target": "prompt",
            "sourceRefs": [self.source_ref],
            "support": "direct",
        }]

        errors = validate_example_payload(
            "examples/generated-question.example.json", payload
        )

        self.assertIn(
            "examples/generated-question.example.json: evidenceMap: missing "
            "claim targets: correctAnswer, distractorRationales[0], "
            "distractorRationales[1], distractorRationales[2], "
            "distractorRationales[3], options[0], options[1], options[2], "
            "options[3], rationale",
            errors,
        )

    def test_generated_question_rejects_empty_claim_evidence_map(self):
        payload = self.make_generated_question()
        payload["evidenceMap"] = []

        errors = validate_example_payload(
            "examples/generated-question.example.json", payload
        )

        self.assertIn(
            "examples/generated-question.example.json: evidenceMap: must be "
            "a non-empty array",
            errors,
        )

    def test_generated_question_rejects_non_string_claim_target(self):
        payload = self.make_generated_question()
        payload["evidenceMap"][0]["target"] = []

        errors = validate_example_payload(
            "examples/generated-question.example.json", payload
        )

        self.assertIn(
            "examples/generated-question.example.json: evidenceMap[0]: "
            "invalid claim target: []",
            errors,
        )

    def test_generated_question_enforces_review_truth_table(self):
        mutations = (
            (
                "draft", "qualityState", "approved",
                "qualityState: must be draft when review.status is draft",
            ),
            (
                "validated", "reviewState", "approved",
                "reviewState: must be unreviewed when review.status is validated",
            ),
            (
                "human-reviewed", "approval.decision", "rejected",
                "review.approval.decision: must be approved when review.status is human-reviewed",
            ),
            (
                "needs-review", "approval.decision", "approved",
                "review.approval.decision: must be needs-review when review.status is needs-review",
            ),
            (
                "rejected", "needsReview", False,
                "needsReview: must be true when review.status is rejected",
            ),
        )
        name = "examples/generated-question.example.json"
        for status, field, invalid_value, expected_suffix in mutations:
            with self.subTest(status=status, field=field):
                valid = self.make_generated_question(status)
                self.assertEqual(validate_example_payload(name, valid), [])
                invalid = self.make_generated_question(status)
                if field == "approval.decision":
                    invalid["review"]["approval"]["decision"] = invalid_value
                else:
                    invalid[field] = invalid_value
                errors = validate_example_payload(name, invalid)
                self.assertIn(f"{name}: {expected_suffix}", errors)

    def test_generated_question_review_binds_record_and_content_version(self):
        payload = self.make_generated_question()
        payload["review"]["approval"]["reviewedRecordId"] = "gq-other"
        payload["review"]["approval"]["reviewedContentVersion"] = "0.9.0"

        errors = validate_example_payload(
            "examples/generated-question.example.json", payload
        )

        self.assertIn(
            "examples/generated-question.example.json: "
            "review.approval.reviewedRecordId: must equal id",
            errors,
        )
        self.assertIn(
            "examples/generated-question.example.json: "
            "review.approval.reviewedContentVersion: must equal contentVersion",
            errors,
        )

    def test_generated_question_review_requires_exact_boolean_needs_review(self):
        payload = self.make_generated_question("draft")
        payload["needsReview"] = 1

        errors = validate_example_payload(
            "examples/generated-question.example.json", payload
        )

        self.assertIn(
            "examples/generated-question.example.json: needsReview: must be "
            "true when review.status is draft",
            errors,
        )

    def test_explanation_requires_true_guidance_and_two_or_three_paragraphs(self):
        cases = (
            (
                1,
                ["One.", "Two."],
                "examples/explanation.example.json: generatedStudyGuidance: must be exactly true",
            ),
            (
                True,
                ["Only one."],
                "examples/explanation.example.json: explanation: must contain two or three non-empty paragraphs",
            ),
            (
                True,
                ["One.", "", "Three."],
                "examples/explanation.example.json: explanation: must contain two or three non-empty paragraphs",
            ),
            (
                True,
                ["One.", "Two.", "Three.", "Four."],
                "examples/explanation.example.json: explanation: must contain two or three non-empty paragraphs",
            ),
        )
        for guidance, explanation, expected in cases:
            with self.subTest(guidance=guidance, explanation=explanation):
                errors = validate_example_payload(
                    "examples/explanation.example.json",
                    {
                        "generatedStudyGuidance": guidance,
                        "explanation": explanation,
                        "review": {"status": "validated"},
                    },
                )
                self.assertIn(expected, errors)

    def test_every_generated_content_review_rejects_unknown_status(self):
        fixtures = {
            "examples/lesson.example.json": {
                "explanation": ["One.", "Two."],
                "recap": ["One.", "Two.", "Three."],
                "review": {"status": "approved"},
            },
            "examples/generated-question.example.json": {
                "origin": "generated", "type": "mcq",
                "options": ["A", "B", "C", "D"], "correctAnswer": 0,
                "distractorRationales": ["A", "B", "C", "D"],
                "difficulty": "medium", "bloomLevel": "apply",
                "sourceRefs": [self.source_ref],
                "review": {"status": "approved"},
            },
            "examples/explanation.example.json": {
                "generatedStudyGuidance": True,
                "explanation": ["One.", "Two."],
                "review": {"status": "approved"},
            },
        }

        for name, payload in fixtures.items():
            with self.subTest(name=name):
                errors = validate_example_payload(name, payload)
                self.assertIn(
                    f"{name}: review.status: invalid value: approved", errors
                )

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
