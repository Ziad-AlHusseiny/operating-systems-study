import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.validate_factory_kit import (
    EXAMPLE_REQUIRED_KEYS,
    REQUIRED_DOCS,
    REQUIRED_EXAMPLES,
    collect_declared_variables,
    collect_template_variables,
    validate_generated_evidence_map,
    validate_internal_links,
    validate_markdown_headings,
    validate_example_payload,
    validate_json_file,
    validate_required_files,
    validate_kit,
)


class FactoryKitValidatorTests(unittest.TestCase):
    canonical_example_fields = {
        "examples/project-config.example.json": (
            "version",
            "project",
            "contentPolicy",
            "questionGeneration",
            "exam",
            "deployment",
        ),
        "examples/source-manifest.example.json": ("version", "sources"),
        "examples/lesson.example.json": (
            "id",
            "moduleId",
            "objectiveIds",
            "title",
            "learningObjectives",
            "summary",
            "explanation",
            "body",
            "keyTerms",
            "workedExamples",
            "commonMistakes",
            "examTips",
            "recap",
            "sourceRefs",
            "linkedQuestionIds",
            "needsReview",
            "reviewNotes",
            "review",
        ),
        "examples/official-question.example.json": (
            "id",
            "origin",
            "type",
            "prompt",
            "topic",
            "options",
            "correctAnswer",
            "sourceRefs",
            "duplicateSources",
            "officialExplanation",
            "needsReview",
            "reviewNotes",
        ),
        "examples/generated-question.example.json": (
            "id",
            "origin",
            "type",
            "prompt",
            "topic",
            "options",
            "correctAnswer",
            "rationale",
            "distractorRationales",
            "difficulty",
            "bloomLevel",
            "cognitiveLevel",
            "learningObjectiveId",
            "sourceRefs",
            "generationMethod",
            "generatedExplanationId",
            "provenance",
            "evidenceMap",
            "contentVersion",
            "qualityState",
            "reviewState",
            "duplicateComparison",
            "duplicateDisposition",
            "needsReview",
            "reviewNotes",
            "review",
        ),
        "examples/explanation.example.json": (
            "id",
            "questionId",
            "language",
            "generatedStudyGuidance",
            "translation",
            "explanation",
            "body",
            "note",
            "sourceRefs",
            "needsReview",
            "reviewNotes",
            "review",
        ),
    }
    nested_canonical_fields = {
        "examples/project-config.example.json": (
            ("project", "title"),
            ("project", "shortTitle"),
            ("project", "slug"),
            ("project", "description"),
            ("project", "brandInitials"),
            ("project", "sourceLanguage"),
            ("project", "studyLanguage"),
            ("contentPolicy", "mode"),
            ("contentPolicy", "allowOutsideSources"),
            ("contentPolicy", "generatedQuestionsRequireHumanReviewForExam"),
            ("questionGeneration", "mcqPerLesson"),
            ("questionGeneration", "trueFalsePerLesson"),
            ("questionGeneration", "difficultyPercent"),
            ("questionGeneration", "difficultyPercent", "easy"),
            ("questionGeneration", "difficultyPercent", "medium"),
            ("questionGeneration", "difficultyPercent", "hard"),
            ("questionGeneration", "bloomPercent"),
            ("questionGeneration", "bloomPercent", "remember"),
            ("questionGeneration", "bloomPercent", "apply"),
            ("questionGeneration", "bloomPercent", "analyze"),
            ("exam", "defaultCount"),
            ("exam", "defaultMinutes"),
            ("deployment", "provider"),
            ("deployment", "repository"),
            ("deployment", "branch"),
            ("deployment", "publicUrl"),
        ),
        "examples/source-manifest.example.json": (
            ("sources", 0, "id"),
            ("sources", 0, "fileName"),
            ("sources", 0, "format"),
            ("sources", 0, "checksum"),
            ("sources", 0, "pages"),
            ("sources", 0, "status"),
            ("sources", 0, "locations"),
            ("sources", 0, "locations", 0, "locationType"),
            ("sources", 0, "locations", 0, "location"),
            ("sources", 1, "slides"),
        ),
        "examples/lesson.example.json": (
            ("learningObjectives", 0, "id"),
            ("learningObjectives", 0, "text"),
            ("learningObjectives", 0, "sourceRefs"),
            ("keyTerms", 0, "term"),
            ("keyTerms", 0, "definition"),
            ("keyTerms", 0, "sourceRefs"),
            ("workedExamples", 0, "title"),
            ("workedExamples", 0, "body"),
            ("workedExamples", 0, "sourceRefs"),
            ("commonMistakes", 0, "misconception"),
            ("commonMistakes", 0, "correction"),
            ("commonMistakes", 0, "sourceRefs"),
            ("examTips", 0, "body"),
            ("examTips", 0, "sourceRefs"),
            ("review", "status"),
            ("review", "approval"),
            ("review", "approval", "reviewedRecordId"),
            ("review", "approval", "reviewedContentVersion"),
            ("review", "approval", "status"),
            ("review", "approval", "decision"),
            ("review", "approval", "reviewer"),
            ("review", "approval", "reviewedAt"),
            ("review", "approval", "reason"),
            ("review", "approval", "notes"),
        ),
        "examples/official-question.example.json": (
            ("sourceRefs", 0, "sourceId"),
            ("sourceRefs", 0, "locationType"),
            ("sourceRefs", 0, "location"),
        ),
        "examples/generated-question.example.json": (
            ("provenance", "sourceRefs"),
            ("provenance", "modelVersion"),
            ("provenance", "promptVersion"),
            ("evidenceMap", 0, "claimId"),
            ("evidenceMap", 0, "target"),
            ("evidenceMap", 0, "sourceRefs"),
            ("evidenceMap", 0, "support"),
            ("duplicateComparison", "algorithmVersion"),
            ("duplicateComparison", "normalizedPrompt"),
            ("duplicateComparison", "candidateIds"),
            ("duplicateComparison", "matchClass"),
            ("review", "status"),
            ("review", "approval"),
            ("review", "approval", "reviewedRecordId"),
            ("review", "approval", "reviewedContentVersion"),
            ("review", "approval", "status"),
            ("review", "approval", "decision"),
            ("review", "approval", "reviewer"),
            ("review", "approval", "reviewedAt"),
            ("review", "approval", "reason"),
            ("review", "approval", "notes"),
        ),
        "examples/explanation.example.json": (
            ("review", "status"),
            ("review", "approval"),
            ("review", "approval", "reviewedRecordId"),
            ("review", "approval", "reviewedContentVersion"),
            ("review", "approval", "status"),
            ("review", "approval", "decision"),
            ("review", "approval", "reviewer"),
            ("review", "approval", "reviewedAt"),
            ("review", "approval", "reason"),
            ("review", "approval", "notes"),
        ),
    }
    source_ref = {"sourceId": "source-01", "locationType": "page", "location": 12}
    evidence_targets = (
        "prompt",
        "correctAnswer",
        "rationale",
        "options[0]",
        "options[1]",
        "options[2]",
        "options[3]",
        "distractorRationales[0]",
        "distractorRationales[1]",
        "distractorRationales[2]",
        "distractorRationales[3]",
    )

    def load_example(self, name):
        return json.loads(
            Path("docs/study-site-factory", name).read_text(encoding="utf-8")
        )

    def remove_nested_field(self, payload, path):
        container = payload
        for part in path[:-1]:
            container = container[part]
        del container[path[-1]]

    def test_every_example_rejects_each_missing_top_level_field(self):
        for name, fields in self.canonical_example_fields.items():
            for field in fields:
                with self.subTest(name=name, field=field):
                    payload = self.load_example(name)
                    del payload[field]
                    errors = validate_example_payload(name, payload)
                    self.assertIn(
                        f"{name}: missing required top-level keys: {field}",
                        errors,
                    )

    def test_every_nested_canonical_field_is_required(self):
        for name, paths in self.nested_canonical_fields.items():
            for field_path in paths:
                with self.subTest(name=name, field_path=field_path):
                    payload = self.load_example(name)
                    self.remove_nested_field(payload, field_path)
                    self.assertTrue(
                        validate_example_payload(name, payload),
                        f"accepted missing canonical field {name}:{field_path}",
                    )

    def test_project_config_enforces_types_enums_and_percent_totals(self):
        mutations = (
            (("version",), "1"),
            (("project", "slug"), "Not A Slug"),
            (("project", "sourceLanguage"), ""),
            (("contentPolicy", "mode"), "hybrid"),
            (("contentPolicy", "allowOutsideSources"), "false"),
            (("contentPolicy", "generatedQuestionsRequireHumanReviewForExam"), 1),
            (("questionGeneration", "mcqPerLesson"), 0),
            (("questionGeneration", "difficultyPercent", "hard"), 19),
            (("questionGeneration", "bloomPercent", "remember"), "25"),
            (("exam", "defaultMinutes"), 0),
            (("deployment", "provider"), "automatic"),
            (("deployment", "repository"), "missing-slash"),
            (("deployment", "publicUrl"), "ftp://example.test"),
        )
        name = "examples/project-config.example.json"
        for field_path, invalid_value in mutations:
            with self.subTest(field_path=field_path):
                payload = self.load_example(name)
                container = payload
                for part in field_path[:-1]:
                    container = container[part]
                container[field_path[-1]] = invalid_value
                self.assertTrue(validate_example_payload(name, payload))

    def test_project_config_rejects_unknown_nested_fields(self):
        name = "examples/project-config.example.json"
        for field_path in ((), ("project",), ("questionGeneration",)):
            with self.subTest(field_path=field_path):
                payload = self.load_example(name)
                container = payload
                for part in field_path:
                    container = container[part]
                container["unexpected"] = True
                self.assertTrue(validate_example_payload(name, payload))

    def test_every_example_rejects_unknown_top_level_fields(self):
        for name in self.canonical_example_fields:
            with self.subTest(name=name):
                payload = self.load_example(name)
                payload["unexpected"] = True
                self.assertTrue(validate_example_payload(name, payload))

    def test_source_and_evidence_collections_must_be_non_empty(self):
        mutations = (
            ("examples/source-manifest.example.json", ("sources",)),
            ("examples/lesson.example.json", ("sourceRefs",)),
            ("examples/official-question.example.json", ("sourceRefs",)),
            ("examples/generated-question.example.json", ("sourceRefs",)),
            ("examples/generated-question.example.json", ("evidenceMap",)),
            (
                "examples/generated-question.example.json",
                ("provenance", "sourceRefs"),
            ),
            ("examples/explanation.example.json", ("sourceRefs",)),
        )
        for name, field_path in mutations:
            with self.subTest(name=name, field_path=field_path):
                payload = self.load_example(name)
                container = payload
                for part in field_path[:-1]:
                    container = container[part]
                container[field_path[-1]] = []
                self.assertTrue(validate_example_payload(name, payload))

    def test_source_formats_enforce_compatible_counts_and_locations(self):
        name = "examples/source-manifest.example.json"
        cases = (
            ("pdf", "pages", "page", 1),
            ("pptx", "slides", "slide", 1),
            ("docx", None, "section", "introduction"),
            ("text", None, "section", "lines-1-4"),
            ("markdown", None, "section", "format-rules"),
            ("csv", None, "row", 2),
            ("json", None, "section", "$.questions[0]"),
            ("image", None, "image", "diagram-1"),
        )
        for source_format, count_field, location_type, location in cases:
            with self.subTest(source_format=source_format):
                source = {
                    "id": "source-format",
                    "fileName": f"example.{source_format}",
                    "format": source_format,
                    "checksum": "sha256:format-example",
                    "status": "accepted",
                    "locations": [
                        {"locationType": location_type, "location": location}
                    ],
                }
                if count_field is not None:
                    source[count_field] = 3
                payload = {"version": "1.0", "sources": [source]}
                self.assertEqual(validate_example_payload(name, payload), [])

    def test_source_formats_reject_incompatible_counts_and_locations(self):
        name = "examples/source-manifest.example.json"
        cases = (
            ("pdf", "slides", "slide"),
            ("pptx", "pages", "page"),
            ("docx", "pages", "page"),
            ("text", "slides", "row"),
            ("markdown", "pages", "page"),
            ("csv", "slides", "section"),
            ("json", "pages", "row"),
            ("image", "slides", "section"),
        )
        for source_format, incompatible_count, incompatible_location in cases:
            with self.subTest(source_format=source_format):
                source = {
                    "id": "source-format",
                    "fileName": f"example.{source_format}",
                    "format": source_format,
                    "checksum": "sha256:format-example",
                    "status": "accepted",
                    "locations": [
                        {
                            "locationType": incompatible_location,
                            "location": 1,
                        }
                    ],
                    incompatible_count: 3,
                }
                if source_format == "pdf":
                    source["pages"] = 3
                elif source_format == "pptx":
                    source["slides"] = 3
                errors = validate_example_payload(
                    name, {"version": "1.0", "sources": [source]}
                )
                self.assertTrue(
                    any("unexpected keys" in error for error in errors), errors
                )
                self.assertTrue(
                    any("locationType must be" in error for error in errors), errors
                )

    def test_question_examples_enforce_type_specific_fields(self):
        name = "examples/official-question.example.json"
        mutations = (
            ("options", ["A", "B", "C"]),
            ("correctAnswer", 4),
            ("type", "essay"),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                payload = self.load_example(name)
                payload[field] = value
                self.assertTrue(validate_example_payload(name, payload))

    def test_official_questions_accept_every_conditional_type_shape(self):
        name = "examples/official-question.example.json"
        cases = {
            "mcq": ({"options": ["A", "B", "C", "D"]}, 0),
            "true-false": ({"options": ["True", "False"]}, 0),
            "true-false-group": (
                {
                    "statements": [
                        {"id": "statement-a", "text": "A is true."},
                        {"id": "statement-b", "text": "B is false."},
                    ]
                },
                {"statement-a": True, "statement-b": False},
            ),
            "multi-select": ({"options": ["A", "B", "C"]}, [0, 2]),
            "matching": (
                {
                    "leftItems": [{"id": "left-a", "text": "Left A"}],
                    "rightItems": [{"id": "right-a", "text": "Right A"}],
                },
                {"left-a": "right-a"},
            ),
            "ordering": (
                {
                    "items": [
                        {"id": "step-a", "text": "First"},
                        {"id": "step-b", "text": "Second"},
                    ]
                },
                ["step-a", "step-b"],
            ),
        }
        conditional_fields = {
            "options",
            "statements",
            "leftItems",
            "rightItems",
            "allowManyToOne",
            "items",
        }
        for question_type, (fields, answer) in cases.items():
            with self.subTest(question_type=question_type):
                payload = self.load_example(name)
                for field in conditional_fields:
                    payload.pop(field, None)
                payload.update(fields)
                payload["type"] = question_type
                payload["correctAnswer"] = answer
                self.assertEqual(validate_example_payload(name, payload), [])

    def test_official_questions_reject_missing_or_mixed_conditional_fields(self):
        name = "examples/official-question.example.json"
        missing = self.load_example(name)
        missing.pop("options")
        mixed = self.load_example(name)
        mixed["items"] = [{"id": "step-a", "text": "First"}]

        missing_errors = validate_example_payload(name, missing)
        mixed_errors = validate_example_payload(name, mixed)

        self.assertTrue(
            any("missing required top-level keys: options" in e for e in missing_errors)
        )
        self.assertTrue(
            any("unexpected top-level keys: items" in e for e in mixed_errors)
        )

    def test_generated_questions_accept_mcq_and_true_false_conditional_shapes(self):
        name = "examples/generated-question.example.json"
        mcq = self.make_generated_question()
        true_false = self.make_generated_question()
        true_false["type"] = "true-false"
        true_false["options"] = ["True", "False"]
        true_false["correctAnswer"] = 1
        true_false["correctedStatement"] = "The corrected proposition is true."
        true_false.pop("distractorRationales")
        targets = (
            "prompt",
            "correctAnswer",
            "rationale",
            "options[0]",
            "options[1]",
            "correctedStatement",
        )
        true_false["evidenceMap"] = [
            {
                "claimId": f"claim-{index}",
                "target": target,
                "sourceRefs": [self.source_ref],
                "support": "direct",
            }
            for index, target in enumerate(targets)
        ]
        true_statement = copy.deepcopy(true_false)
        true_statement["correctAnswer"] = 0
        true_statement["correctedStatement"] = None
        true_statement["evidenceMap"] = [
            evidence
            for evidence in true_statement["evidenceMap"]
            if evidence["target"] != "correctedStatement"
        ]

        self.assertEqual(validate_example_payload(name, mcq), [])
        self.assertEqual(validate_example_payload(name, true_false), [])
        self.assertEqual(validate_example_payload(name, true_statement), [])

    def test_generated_questions_reject_mixed_or_unsupported_type_fields(self):
        name = "examples/generated-question.example.json"
        mixed = self.make_generated_question()
        mixed["correctedStatement"] = None
        mixed_true_false = self.make_generated_question()
        mixed_true_false["type"] = "true-false"
        mixed_true_false["options"] = ["True", "False"]
        mixed_true_false["correctAnswer"] = 0
        mixed_true_false["correctedStatement"] = None
        unsupported = self.make_generated_question()
        unsupported["type"] = "ordering"
        unsupported.pop("options")
        unsupported.pop("distractorRationales")
        unsupported["items"] = [{"id": "step-a", "text": "First"}]
        unsupported["correctAnswer"] = ["step-a"]

        mixed_errors = validate_example_payload(name, mixed)
        mixed_true_false_errors = validate_example_payload(name, mixed_true_false)
        unsupported_errors = validate_example_payload(name, unsupported)

        self.assertTrue(
            any(
                "unexpected top-level keys: correctedStatement" in e
                for e in mixed_errors
            )
        )
        self.assertTrue(
            any(
                "unexpected top-level keys: distractorRationales" in e
                for e in mixed_true_false_errors
            )
        )
        self.assertTrue(
            any(
                "type: generated questions support only mcq or true-false" in e
                for e in unsupported_errors
            )
        )

    def test_generated_true_false_enforces_correction_semantics(self):
        name = "examples/generated-question.example.json"
        for answer, correction, expected in (
            (0, "Not allowed for true.", "must be null when correctAnswer is 0"),
            (1, None, "must be a non-empty string when correctAnswer is 1"),
        ):
            with self.subTest(answer=answer):
                payload = self.make_generated_question()
                payload["type"] = "true-false"
                payload["options"] = ["True", "False"]
                payload["correctAnswer"] = answer
                payload["correctedStatement"] = correction
                payload.pop("distractorRationales")
                errors = validate_example_payload(name, payload)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_complete_validation_rejects_broken_example_identity_links(self):
        mutations = (
            (
                "generated-question.example.json",
                ("generatedExplanationId",),
                "explanation-missing",
                "generatedExplanationId does not resolve",
            ),
            (
                "explanation.example.json",
                ("questionId",),
                "gq-missing",
                "questionId does not resolve",
            ),
            (
                "lesson.example.json",
                ("linkedQuestionIds",),
                ["q-missing"],
                "linkedQuestionIds[0] does not resolve",
            ),
            (
                "official-question.example.json",
                ("sourceRefs", 0, "sourceId"),
                "source-missing",
                "sourceId does not resolve",
            ),
        )
        for relative, field_path, value, expected in mutations:
            with self.subTest(relative=relative, field_path=field_path):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory) / "factory"
                    shutil.copytree(Path("docs/study-site-factory"), root)
                    path = root / "examples" / relative
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    container = payload
                    for part in field_path[:-1]:
                        container = container[part]
                    container[field_path[-1]] = value
                    path.write_text(json.dumps(payload), encoding="utf-8")

                    errors = validate_kit(root)

                self.assertTrue(
                    any(expected in error for error in errors),
                    f"missing linkage error {expected}: {errors}",
                )

    def test_generated_explanation_must_describe_its_owning_question(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "factory"
            shutil.copytree(Path("docs/study-site-factory"), root)
            path = root / "examples" / "explanation.example.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["questionId"] = "q-001"
            path.write_text(json.dumps(payload), encoding="utf-8")

            errors = validate_kit(root)

        self.assertTrue(
            any(
                "explanation does not describe generated question" in error
                for error in errors
            )
        )

    def test_duplicate_candidate_ids_must_be_lexicographically_sorted(self):
        name = "examples/generated-question.example.json"
        payload = self.load_example(name)
        payload["duplicateComparison"].update(
            {
                "candidateIds": ["q-002", "q-001"],
                "matchClass": "exact",
            }
        )
        payload["duplicateDisposition"] = "reject-duplicate"

        errors = validate_example_payload(name, payload)

        self.assertTrue(
            any(
                "candidateIds: must use lexicographic order" in error
                for error in errors
            )
        )

    def test_exact_duplicate_disposition_is_deterministic(self):
        name = "examples/generated-question.example.json"
        cases = (
            ("gq-current", ["q-001"], "reject-duplicate"),
            ("gq-002", ["gq-001"], "reject-duplicate"),
            ("gq-001", ["gq-002"], "retain"),
        )
        for question_id, candidate_ids, disposition in cases:
            with self.subTest(question_id=question_id, candidate_ids=candidate_ids):
                payload = self.make_generated_question()
                payload["id"] = question_id
                payload["review"]["approval"]["reviewedRecordId"] = question_id
                payload["duplicateComparison"].update(
                    {"candidateIds": candidate_ids, "matchClass": "exact"}
                )
                payload["duplicateDisposition"] = disposition
                self.assertEqual(validate_example_payload(name, payload), [])

    def test_exact_duplicate_requires_candidates_and_correct_disposition(self):
        name = "examples/generated-question.example.json"
        empty = self.make_generated_question()
        empty["duplicateComparison"]["matchClass"] = "exact"

        empty_errors = validate_example_payload(name, empty)
        self.assertTrue(
            any(
                "exact match requires at least one candidate" in e for e in empty_errors
            )
        )

        cases = (
            ("gq-current", ["q-001"], "retain", "reject-duplicate"),
            ("gq-002", ["gq-001"], "retain", "reject-duplicate"),
            ("gq-001", ["gq-002"], "reject-duplicate", "retain"),
        )
        for question_id, candidate_ids, disposition, expected in cases:
            with self.subTest(question_id=question_id, candidate_ids=candidate_ids):
                payload = self.make_generated_question()
                payload["id"] = question_id
                payload["review"]["approval"]["reviewedRecordId"] = question_id
                payload["duplicateComparison"].update(
                    {"candidateIds": candidate_ids, "matchClass": "exact"}
                )
                payload["duplicateDisposition"] = disposition
                errors = validate_example_payload(name, payload)
                self.assertTrue(
                    any(
                        f"must be {expected} for exact match" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_malformed_linkage_collections_aggregate_without_raising(self):
        cases = (
            (
                "source-manifest.example.json",
                ("sources",),
                7,
                "sources: must be a non-empty array",
            ),
            (
                "source-manifest.example.json",
                ("sources",),
                {},
                "sources: must be a non-empty array",
            ),
            (
                "source-manifest.example.json",
                ("sources", 0, "locations"),
                7,
                "locations: must be a non-empty array",
            ),
            (
                "source-manifest.example.json",
                ("sources", 0, "locations"),
                {},
                "locations: must be a non-empty array",
            ),
            (
                "lesson.example.json",
                ("linkedQuestionIds",),
                7,
                "linkedQuestionIds: must be an array",
            ),
            (
                "lesson.example.json",
                ("linkedQuestionIds",),
                {},
                "linkedQuestionIds: must be an array",
            ),
            (
                "lesson.example.json",
                ("linkedQuestionIds",),
                [{}],
                "linkedQuestionIds: must contain only non-empty strings",
            ),
            (
                "official-question.example.json",
                ("sourceRefs", 0, "sourceId"),
                {},
                "sourceId must use the source- prefix",
            ),
            (
                "official-question.example.json",
                ("sourceRefs", 0, "location"),
                {},
                "location must be a positive integer or string",
            ),
            (
                "generated-question.example.json",
                ("generatedExplanationId",),
                {},
                "generatedExplanationId: must be a non-empty string",
            ),
            (
                "explanation.example.json",
                ("questionId",),
                {},
                "questionId: must use q- or gq- prefix",
            ),
        )
        for relative, field_path, value, expected in cases:
            with self.subTest(relative=relative, field_path=field_path, value=value):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory) / "factory"
                    shutil.copytree(Path("docs/study-site-factory"), root)
                    path = root / "examples" / relative
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    container = payload
                    for part in field_path[:-1]:
                        container = container[part]
                    container[field_path[-1]] = value
                    path.write_text(json.dumps(payload), encoding="utf-8")

                    try:
                        errors = validate_kit(root)
                    except (TypeError, AttributeError) as error:
                        self.fail(f"validation raised instead of aggregating: {error}")

                self.assertTrue(any(expected in error for error in errors), errors)

    def test_complete_factory_kit_passes(self):
        root = Path("docs/study-site-factory")
        self.assertEqual(validate_kit(root), [])

    def test_all_template_variables_are_declared(self):
        root = Path("docs/study-site-factory")
        declared = collect_declared_variables(root / "01-PROJECT-INPUT-TEMPLATE.md")
        used = set().union(
            *(
                collect_template_variables(path.read_text(encoding="utf-8"))
                for path in root.glob("*.md")
            )
        )
        self.assertEqual(used - declared, set())

    def test_bare_variable_names_are_not_declarations(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.md"
            path.write_text("| `PROJECT_TITLE` | Bare name. |\n", encoding="utf-8")
            self.assertEqual(collect_declared_variables(path), set())

    def test_complete_validation_reports_undeclared_template_variables(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "factory"
            shutil.copytree(Path("docs/study-site-factory"), root)
            with (root / "README.md").open("a", encoding="utf-8") as stream:
                stream.write("\n{{UNDECLARED_FACTORY_VALUE}}\n")

            errors = validate_kit(root)

        self.assertIn("undeclared template variable: UNDECLARED_FACTORY_VALUE", errors)

    def test_complete_validation_reports_broken_relative_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "factory"
            shutil.copytree(Path("docs/study-site-factory"), root)
            with (root / "README.md").open("a", encoding="utf-8") as stream:
                stream.write("\n[Missing](missing-document.md)\n")

            errors = validate_kit(root)

        self.assertIn(
            f"{root / 'README.md'}: broken relative link: missing-document.md",
            errors,
        )

    def test_complete_validation_reports_unfinished_markers(self):
        markers = (
            "T" + "BD",
            "T" + "ODO",
            "implement" + " later",
            "fill" + " in later",
        )
        for marker in markers:
            with (
                self.subTest(marker=marker),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory) / "factory"
                shutil.copytree(Path("docs/study-site-factory"), root)
                with (root / "README.md").open("a", encoding="utf-8") as stream:
                    stream.write(f"\n{marker}\n")

                errors = validate_kit(root)

            self.assertIn(f"{root / 'README.md'}: unfinished marker: {marker}", errors)

    def test_complete_validation_reports_missing_required_headings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "factory"
            shutil.copytree(Path("docs/study-site-factory"), root)
            path = root / "02-PRD-TEMPLATE.md"
            text = path.read_text(encoding="utf-8").replace(
                "## Product Goal", "## Removed Product Goal", 1
            )
            path.write_text(text, encoding="utf-8")

            errors = validate_kit(root)

        self.assertIn(f"{path}: missing heading: Product Goal", errors)

    def test_extra_root_markdown_receives_every_document_safety_check(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "factory"
            shutil.copytree(Path("docs/study-site-factory"), root)
            path = root / "EXTRA.md"
            path.write_text(
                "{{UNDECLARED_EXTRA}}\n[Missing](missing-extra.md)\n" + "T" + "ODO\n",
                encoding="utf-8",
            )

            errors = validate_kit(root)

        self.assertIn("undeclared template variable: UNDECLARED_EXTRA", errors)
        self.assertIn(f"{path}: broken relative link: missing-extra.md", errors)
        self.assertIn(f"{path}: unfinished marker: {'T' + 'ODO'}", errors)

    def test_internal_links_enforce_root_containment(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = parent / "repository"
            root.mkdir()
            (root / "inside.md").write_text("# Inside\n", encoding="utf-8")
            (parent / "outside.md").write_text("# Outside\n", encoding="utf-8")
            (root / "nested").mkdir()
            path = root / "nested" / "links.md"
            targets = (
                "../inside.md",
                "../../outside.md",
                "C:/Windows/System32/drivers/etc/hosts",
                "\\\\server\\share\\file.md",
                "/Windows/System32/drivers/etc/hosts",
            )
            path.write_text(
                "\n".join(f"[Target]({target})" for target in targets),
                encoding="utf-8",
            )

            errors = validate_internal_links(root, [path])

        self.assertNotIn(f"{path}: unsafe link target: ../inside.md", errors)
        for target in targets[1:]:
            with self.subTest(target=target):
                self.assertIn(f"{path}: unsafe link target: {target}", errors)

    def test_invalid_utf8_markdown_is_reported_and_validation_continues(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "factory"
            shutil.copytree(Path("docs/study-site-factory"), root)
            path = root / "01-PROJECT-INPUT-TEMPLATE.md"
            path.write_bytes(b"\xff\xfe")

            try:
                errors = validate_kit(root)
            except UnicodeError as error:
                self.fail(f"validation raised instead of aggregating: {error}")

        self.assertTrue(
            any(
                str(path) in error and "cannot read Markdown" in error
                for error in errors
            )
        )

    def make_generated_question(self, review_status="human-reviewed"):
        states = {
            "draft": ("draft", "unreviewed", True, None),
            "validated": ("validated", "unreviewed", True, None),
            "human-reviewed": ("approved", "approved", False, "approved"),
            "needs-review": ("needs-review", "needs-review", True, "needs-review"),
            "rejected": ("rejected", "rejected", True, "rejected"),
        }
        quality, canonical_review, needs_review, decision = states[review_status]
        payload = self.load_example("examples/generated-question.example.json")
        review = {"status": review_status}
        if decision is not None:
            approval = copy.deepcopy(payload["review"]["approval"])
            approval["decision"] = decision
            review["approval"] = approval
        payload.update(
            {
                "qualityState": quality,
                "reviewState": canonical_review,
                "needsReview": needs_review,
                "review": review,
            }
        )
        return payload

    def validate_mutated_evidence_source_refs(self, source_refs):
        payload = self.make_generated_question()
        payload["evidenceMap"][0]["sourceRefs"] = source_refs
        return validate_generated_evidence_map(
            payload, "examples/generated-question.example.json"
        )

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
                payload = json.loads((root / relative).read_text(encoding="utf-8"))
                self.assertTrue(required.issubset(payload))

    def test_generated_mcq_example_has_complete_answer_contract(self):
        payload = json.loads(
            Path(
                "docs/study-site-factory/examples/generated-question.example.json"
            ).read_text(encoding="utf-8")
        )

        self.assertEqual(payload["origin"], "generated")
        self.assertEqual(len(payload["options"]), 4)
        self.assertEqual(len(payload["distractorRationales"]), 4)
        self.assertIsInstance(payload["correctAnswer"], int)
        self.assertIn(payload["correctAnswer"], range(4))
        self.assertGreaterEqual(len(payload["sourceRefs"]), 1)

    def test_lesson_rejects_explanation_outside_two_to_five_paragraphs(self):
        for explanation in (
            ["Only one."],
            ["One.", "", "Three."],
            ["One.", "Two.", "Three.", "Four.", "Five.", "Six."],
        ):
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
        for recap in (
            ["One.", "Two."],
            ["One.", "", "Three."],
            ["One.", "Two.", "Three.", "Four.", "Five.", "Six.", "Seven.", "Eight."],
        ):
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
        self.assertTrue(
            {"objectiveIds", "body", "needsReview", "reviewNotes"}.issubset(
                EXAMPLE_REQUIRED_KEYS["examples/lesson.example.json"]
            )
        )

    def test_lesson_rejects_canonical_body_or_objective_mapping_drift(self):
        payload = {
            "objectiveIds": ["objective-dhcp"],
            "learningObjectives": [{"id": "objective-dns"}],
            "explanation": ["First paragraph.", "Second paragraph."],
            "body": "First paragraph. Second paragraph.",
            "recap": ["One.", "Two.", "Three."],
            "review": {"status": "draft"},
        }

        errors = validate_example_payload("examples/lesson.example.json", payload)

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
        payload["evidenceMap"] = [
            {
                "claimId": "claim-prompt",
                "target": "prompt",
                "sourceRefs": [self.source_ref],
                "support": "direct",
            }
        ]

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

    def test_generated_evidence_rejects_non_list_source_refs(self):
        errors = self.validate_mutated_evidence_source_refs("not-a-list")
        self.assertIn(
            "examples/generated-question.example.json: evidenceMap[0]: "
            "sourceRefs: must be a non-empty array",
            errors,
        )

    def test_generated_evidence_rejects_empty_source_refs(self):
        errors = self.validate_mutated_evidence_source_refs([])
        self.assertIn(
            "examples/generated-question.example.json: evidenceMap[0]: "
            "sourceRefs: must be a non-empty array",
            errors,
        )

    def test_generated_evidence_rejects_non_object_source_reference(self):
        errors = self.validate_mutated_evidence_source_refs(["not-a-reference"])
        self.assertIn(
            "examples/generated-question.example.json: evidenceMap[0]: "
            "sourceRefs[0]: source reference must be an object",
            errors,
        )

    def test_generated_evidence_rejects_missing_source_reference_fields(self):
        errors = self.validate_mutated_evidence_source_refs([{}])
        self.assertIn(
            "examples/generated-question.example.json: evidenceMap[0]: "
            "sourceRefs[0]: missing required keys: location, locationType, "
            "sourceId",
            errors,
        )

    def test_generated_evidence_rejects_invalid_source_location_type(self):
        errors = self.validate_mutated_evidence_source_refs(
            [
                {
                    "sourceId": "source-01",
                    "locationType": "chapter",
                    "location": 12,
                }
            ]
        )
        self.assertIn(
            "examples/generated-question.example.json: evidenceMap[0]: "
            "sourceRefs[0]: invalid locationType: chapter",
            errors,
        )

    def test_generated_question_enforces_review_truth_table(self):
        mutations = (
            (
                "draft",
                "qualityState",
                "approved",
                "qualityState: must be draft when review.status is draft",
            ),
            (
                "validated",
                "reviewState",
                "approved",
                "reviewState: must be unreviewed when review.status is validated",
            ),
            (
                "human-reviewed",
                "approval.decision",
                "rejected",
                "review.approval.decision: must be approved when review.status is human-reviewed",
            ),
            (
                "needs-review",
                "approval.decision",
                "approved",
                "review.approval.decision: must be needs-review when review.status is needs-review",
            ),
            (
                "rejected",
                "needsReview",
                False,
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
                "origin": "generated",
                "type": "mcq",
                "options": ["A", "B", "C", "D"],
                "correctAnswer": 0,
                "distractorRationales": ["A", "B", "C", "D"],
                "difficulty": "medium",
                "bloomLevel": "apply",
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
                self.assertIn(f"{name}: review.status: invalid value: approved", errors)

    def test_reports_missing_top_level_keys_in_required_examples(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_complete_kit(
                root,
                {"sources": []},
                {
                    "id": "q-001",
                    "origin": "official",
                    "type": "mcq",
                    "prompt": "Prompt",
                    "topic": "Topic",
                    "correctAnswer": 0,
                    "sourceRefs": [],
                    "needsReview": False,
                    "reviewNotes": "",
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
                    "id": "q-001",
                    "origin": "official",
                    "type": "mcq",
                    "prompt": "Prompt",
                    "topic": "Topic",
                    "correctAnswer": 0,
                    "sourceRefs": [
                        {
                            "sourceId": "source-01",
                            "locationType": "chapter",
                            "location": 1,
                        }
                    ],
                    "needsReview": False,
                    "reviewNotes": "",
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
        errors = validate_markdown_headings(
            path,
            (
                "Product Goal",
                "Users and Jobs",
                "Content Modes",
                "Functional Requirements",
                "Material Requirements",
                "Question Requirements",
                "Persistence",
                "Non-Functional Requirements",
                "Acceptance Criteria",
            ),
        )
        self.assertEqual(errors, [])

    def test_ux_document_contains_every_route(self):
        path = Path("docs/study-site-factory/07-UX-AND-SYSTEM-FLOW.md")
        text = path.read_text(encoding="utf-8")
        routes = (
            "Dashboard",
            "Material",
            "Practice",
            "Mock Exam",
            "Question Bank",
            "Question Explanations",
            "Revision Summary",
            "Mistakes",
            "Bookmarks",
        )
        for route in routes:
            self.assertIn(route, text)

    def test_qa_document_contains_all_blocking_gates(self):
        path = Path("docs/study-site-factory/09-QA-GATES.md")
        text = path.read_text(encoding="utf-8")
        for gate in (
            "Gate 1: Input Completeness",
            "Gate 2: Extraction and Provenance",
            "Gate 3: Canonical Content",
            "Gate 4: Lessons and Guidance",
            "Gate 5: Generated Questions",
            "Gate 6: Application Safety and Logic",
            "Gate 7: Browser QA",
            "Gate 8: Deployment",
        ):
            self.assertIn(gate, text)

    def test_build_workflow_names_resumable_artifacts(self):
        path = Path("docs/study-site-factory/08-BUILD-WORKFLOW.md")
        text = path.read_text(encoding="utf-8")
        artifacts = (
            "SOURCE_AUDIT_REPORT.md",
            "CONTENT_COVERAGE_REPORT.md",
            "QUESTION_QUALITY_REPORT.md",
            "FINAL_QA_REPORT.md",
            "progress-ledger.md",
        )
        for artifact in artifacts:
            self.assertIn(artifact, text)

    def test_deployment_monitoring_is_bound_to_verified_commit(self):
        for relative in ("09-QA-GATES.md", "11-HANDOFF-AND-DEPLOYMENT.md"):
            with self.subTest(relative=relative):
                text = Path("docs/study-site-factory", relative).read_text(
                    encoding="utf-8"
                )
                for contract in (
                    "$ExpectedSha = (git rev-parse HEAD).Trim()",
                    "git ls-remote --heads origin",
                    "$RemoteSha -ne $ExpectedSha",
                    "--event workflow_dispatch",
                    "--json headSha,conclusion,jobs",
                    "$Run.headSha -ne $ExpectedSha",
                    '$Run.conclusion -ne "success"',
                    '$RequiredJobs = @("build", "deploy")',
                ):
                    self.assertIn(contract, text)

    def test_public_verification_checks_every_published_json_payload(self):
        for relative in ("09-QA-GATES.md", "11-HANDOFF-AND-DEPLOYMENT.md"):
            with self.subTest(relative=relative):
                text = Path("docs/study-site-factory", relative).read_text(
                    encoding="utf-8"
                )
                for contract in (
                    "$RequiredPayloads = @(Get-ChildItem $DataRoot -Recurse "
                    "-Filter *.json -File)",
                    "foreach ($LocalFile in $RequiredPayloads)",
                    "$MapEntries = @($Value.PSObject.Properties",
                    "$MapPropertyCount = @($Value.PSObject.Properties).Count",
                    '"__stableId"',
                    "$Response.StatusCode -ne 200",
                    "$ContentType -notmatch",
                    "ConvertFrom-Json",
                    "$PublicRecords.Count -ne $LocalRecords.Count",
                    "Sort-Object",
                    "Compare-Object $LocalIds $PublicIds",
                ):
                    self.assertIn(contract, text)

    def test_factory_docs_do_not_use_ad_hoc_placeholder_forms(self):
        root = Path("docs/study-site-factory")
        for path in root.glob("*.md"):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertNotRegex(
                    text,
                    r"replace-with-[A-Za-z0-9_-]+|<[^>\r\n]+>",
                )

    def test_final_handoff_assigns_all_runtime_values_before_use(self):
        text = Path("docs/study-site-factory/11-HANDOFF-AND-DEPLOYMENT.md").read_text(
            encoding="utf-8"
        )
        section = text.split("## Final handoff summary", 1)[1]
        block = section.split("```powershell", 1)[1].split("```", 1)[0]

        for name in (
            "DeploymentVerified",
            "CountsSummary",
            "ReviewItemSummary",
            "TestSummary",
            "KnownLimitationsSummary",
        ):
            with self.subTest(name=name):
                reference = f"${name}"
                assignment = f"{reference} ="
                self.assertIn(assignment, block)
                self.assertEqual(block.find(reference), block.find(assignment))
                self.assertIn(
                    reference, block[block.find(assignment) + len(assignment) :]
                )

    def test_final_handoff_compares_every_committed_evidence_path_to_head(self):
        text = Path("docs/study-site-factory/11-HANDOFF-AND-DEPLOYMENT.md").read_text(
            encoding="utf-8"
        )
        section = text.split("## Final handoff summary", 1)[1]
        block = section.split("```powershell", 1)[1].split("```", 1)[0]

        for evidence_path in ("$Path", "$Test.evidence"):
            with self.subTest(evidence_path=evidence_path):
                self.assertIn(
                    f"git ls-files --error-unmatch -- {evidence_path}",
                    block,
                )
                self.assertIn(
                    f"git diff --quiet HEAD -- {evidence_path}",
                    block,
                )
                self.assertNotIn(
                    f"git diff --quiet -- {evidence_path}",
                    block,
                )

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
            "`summaries`",
            "`terms`",
            "`examples`",
            "`mistakes`",
            "`examTips`",
            "`recaps`",
            "`sourceRefs`",
            "`linkedQuestionIds`",
        ):
            self.assertIn(field, text)

    def test_content_contract_defines_generated_question_quality_and_duplicates(self):
        text = Path(
            "docs/study-site-factory/04-CONTENT-AND-DATA-CONTRACTS.md"
        ).read_text(encoding="utf-8")
        self.assertIn("## Generated Question Quality and Duplication", text)
        for field in (
            "`difficulty`",
            "`cognitiveLevel`",
            "`evidenceMap`",
            "`qualityState`",
            "`reviewState`",
            "`duplicateComparison`",
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
            "`status`",
            "`decision`",
            "`reviewer`",
            "`reviewedAt`",
            "`reason`",
            "`notes`",
            "`reviewedRecordId`",
            "`reviewedContentVersion`",
        ):
            self.assertIn(field, text)
        self.assertIn(
            "only when both `qualityState` and `reviewState` are `approved`", text
        )


if __name__ == "__main__":
    unittest.main()
