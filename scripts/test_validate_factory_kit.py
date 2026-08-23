import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import scripts.validate_factory_kit as factory_validator
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
            "contentVersion",
            "materialSectionIds",
            "learningObjectives",
            "materialSections",
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
            "contentVersion",
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
            "contentVersion",
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
            ("sources", 0, "collection"),
            ("sources", 0, "label"),
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
            ("materialSections", 0, "id"),
            ("materialSections", 0, "order"),
            ("materialSections", 0, "title"),
            ("materialSections", 0, "origin"),
            ("materialSections", 0, "label"),
            ("materialSections", 0, "generatedStudyGuidance"),
            ("materialSections", 0, "summary"),
            ("materialSections", 0, "explanation"),
            ("materialSections", 0, "body"),
            ("materialSections", 0, "keyTerms", 0, "term"),
            ("materialSections", 0, "keyTerms", 0, "definition"),
            ("materialSections", 0, "keyTerms", 0, "sourceRefs"),
            ("materialSections", 0, "workedExamples", 0, "title"),
            ("materialSections", 0, "workedExamples", 0, "body"),
            ("materialSections", 0, "workedExamples", 0, "sourceRefs"),
            ("materialSections", 0, "commonMistakes", 0, "misconception"),
            ("materialSections", 0, "commonMistakes", 0, "correction"),
            ("materialSections", 0, "commonMistakes", 0, "sourceRefs"),
            ("materialSections", 0, "examTips", 0, "body"),
            ("materialSections", 0, "examTips", 0, "sourceRefs"),
            ("materialSections", 0, "recap"),
            ("materialSections", 0, "sourceRefs"),
            ("materialSections", 0, "linkedQuestionIds"),
            ("materialSections", 0, "needsReview"),
            ("materialSections", 0, "reviewNotes"),
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
        return factory_validator.parse_json(
            Path("docs/study-site-factory", name).read_text(encoding="utf-8")
        )

    def make_deployment_evidence(self, event="push"):
        commit = "a" * 40
        browser_checks = [
            "Dashboard",
            "Material",
            "Practice",
            "active-Exam non-leakage",
            "Results",
            "search",
            "combined filters",
            "pagination",
            "bookmarks",
            "progress export/import",
            "light/dark",
            "LTR/RTL",
            "responsive navigation",
            "asset/base-path loading",
            "no horizontal overflow",
        ]
        return {
            "releaseCommit": commit,
            "remoteBranchCommit": commit,
            "workflow": {
                "event": event,
                "headSha": commit,
                "conclusion": "success",
                "jobs": {"build": "success", "deploy": "success"},
            },
            "publicHtml": {
                "commit": commit,
                "status": 200,
                "contentType": "text/html; charset=utf-8",
            },
            "requiredPayloadPaths": ["lessons.json", "questions.json"],
            "publicPayloads": [
                {
                    "path": "lessons.json",
                    "commit": commit,
                    "status": 200,
                    "contentType": "application/json",
                    "parsed": True,
                    "localCount": 1,
                    "publicCount": 1,
                    "localIds": ["lesson-01"],
                    "publicIds": ["lesson-01"],
                },
                {
                    "path": "questions.json",
                    "commit": commit,
                    "status": 200,
                    "contentType": "application/json; charset=utf-8",
                    "parsed": True,
                    "localCount": 2,
                    "publicCount": 2,
                    "localIds": ["gq-001", "q-001"],
                    "publicIds": ["gq-001", "q-001"],
                },
            ],
            "browserSmokes": [
                {
                    "viewport": viewport,
                    "commit": commit,
                    "passed": True,
                    "checks": browser_checks,
                    "consoleErrors": 0,
                    "failedRequests": 0,
                }
                for viewport in ("1440x1000", "390x844")
            ],
        }

    def make_multi_origin_lesson(self):
        source_ref = copy.deepcopy(self.source_ref)
        guidance_ref = {
            "sourceId": "source-02",
            "locationType": "slide",
            "location": 5,
        }
        return {
            "id": "lesson-dhcp-across-subnets",
            "moduleId": "module-network-services",
            "objectiveIds": ["objective-dhcp-across-subnets"],
            "title": "DHCP Address Assignment Across Subnets",
            "contentVersion": "1.0.0",
            "materialSectionIds": [
                "material-section-dhcp-source",
                "material-section-dhcp-guidance",
            ],
            "learningObjectives": [
                {
                    "id": "objective-dhcp-across-subnets",
                    "text": "Explain why DHCP relay is required across subnets.",
                    "sourceRefs": [source_ref],
                }
            ],
            "materialSections": [
                {
                    "id": "material-section-dhcp-source",
                    "order": 1,
                    "title": "Source material",
                    "origin": "source",
                    "label": "Source material",
                    "generatedStudyGuidance": False,
                    "summary": "DHCP broadcasts do not cross routers directly.",
                    "explanation": [
                        "A client begins with a local broadcast.",
                        "A relay forwards the exchange to the remote server.",
                    ],
                    "body": "A client begins with a local broadcast.\n\nA relay forwards the exchange to the remote server.",
                    "keyTerms": [
                        {
                            "term": "DHCP relay",
                            "definition": "A device that forwards DHCP messages.",
                            "sourceRefs": [source_ref],
                        }
                    ],
                    "workedExamples": [],
                    "commonMistakes": [],
                    "examTips": [],
                    "recap": [
                        "Broadcast starts locally.",
                        "Routers separate broadcasts.",
                        "A relay forwards DHCP.",
                    ],
                    "sourceRefs": [source_ref],
                    "linkedQuestionIds": ["q-network-dhcp-001"],
                    "needsReview": False,
                    "reviewNotes": "",
                },
                {
                    "id": "material-section-dhcp-guidance",
                    "order": 2,
                    "title": "Study guidance",
                    "origin": "generated",
                    "label": "Generated study guidance",
                    "generatedStudyGuidance": True,
                    "summary": "Trace the client, relay, and server path.",
                    "explanation": [
                        "Identify the broadcast-domain boundary first.",
                        "Then place the relay on the client-facing interface.",
                    ],
                    "body": "Identify the broadcast-domain boundary first.\n\nThen place the relay on the client-facing interface.",
                    "keyTerms": [
                        {
                            "term": "Relay path",
                            "definition": "The evidence-backed forwarding path.",
                            "sourceRefs": [guidance_ref],
                        }
                    ],
                    "workedExamples": [],
                    "commonMistakes": [],
                    "examTips": [],
                    "recap": [
                        "Find the boundary.",
                        "Find the relay.",
                        "Trace the server reply.",
                    ],
                    "sourceRefs": [guidance_ref],
                    "linkedQuestionIds": ["gq-network-dhcp-001"],
                    "needsReview": False,
                    "reviewNotes": "",
                },
            ],
            "needsReview": False,
            "reviewNotes": "",
            "review": {
                "status": "human-reviewed",
                "approval": {
                    "reviewedRecordId": "lesson-dhcp-across-subnets",
                    "reviewedContentVersion": "1.0.0",
                    "status": "completed",
                    "decision": "approved",
                    "reviewer": "reviewer-lesson-01",
                    "reviewedAt": "2026-08-22T10:30:00Z",
                    "reason": "Evidence and lesson structure verified.",
                    "notes": "Both origins remain separate.",
                },
            },
        }

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
            (("questionGeneration", "mcqPerLesson"), -1),
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

    def test_project_config_uses_zero_quota_to_disable_one_question_type(self):
        name = "examples/project-config.example.json"
        for disabled, enabled in (
            ("mcqPerLesson", "trueFalsePerLesson"),
            ("trueFalsePerLesson", "mcqPerLesson"),
        ):
            with self.subTest(disabled=disabled):
                payload = self.load_example(name)
                payload["questionGeneration"][disabled] = 0
                self.assertGreater(payload["questionGeneration"][enabled], 0)
                self.assertEqual(validate_example_payload(name, payload), [])

    def test_project_config_rejects_disabling_both_question_types(self):
        name = "examples/project-config.example.json"
        payload = self.load_example(name)
        payload["questionGeneration"]["mcqPerLesson"] = 0
        payload["questionGeneration"]["trueFalsePerLesson"] = 0

        errors = validate_example_payload(name, payload)

        self.assertIn(
            f"{name}: questionGeneration: at least one question type must be enabled",
            errors,
        )

    def test_generated_only_project_config_accepts_one_enabled_question_type(self):
        name = "examples/project-config.example.json"
        for disabled, enabled in (
            ("mcqPerLesson", "trueFalsePerLesson"),
            ("trueFalsePerLesson", "mcqPerLesson"),
        ):
            with self.subTest(disabled=disabled):
                payload = self.load_example(name)
                payload["contentPolicy"]["mode"] = "generated-only"
                payload["questionGeneration"][disabled] = 0
                self.assertGreater(payload["questionGeneration"][enabled], 0)
                self.assertEqual(validate_example_payload(name, payload), [])

    def test_generated_only_project_config_rejects_disabling_both_question_types(self):
        name = "examples/project-config.example.json"
        payload = self.load_example(name)
        payload["contentPolicy"]["mode"] = "generated-only"
        payload["questionGeneration"]["mcqPerLesson"] = 0
        payload["questionGeneration"]["trueFalsePerLesson"] = 0

        errors = validate_example_payload(name, payload)

        self.assertIn(
            f"{name}: questionGeneration: at least one question type must be enabled",
            errors,
        )

    def test_source_only_project_config_accepts_no_generated_question_types(self):
        name = "examples/project-config.example.json"
        payload = self.load_example(name)
        payload["contentPolicy"]["mode"] = "source-only"
        payload["questionGeneration"]["mcqPerLesson"] = 0
        payload["questionGeneration"]["trueFalsePerLesson"] = 0

        self.assertEqual(validate_example_payload(name, payload), [])

    def test_source_only_project_config_rejects_enabled_generated_question_types(self):
        name = "examples/project-config.example.json"
        for enabled_field in ("mcqPerLesson", "trueFalsePerLesson"):
            with self.subTest(enabled_field=enabled_field):
                payload = self.load_example(name)
                payload["contentPolicy"]["mode"] = "source-only"
                payload["questionGeneration"]["mcqPerLesson"] = 0
                payload["questionGeneration"]["trueFalsePerLesson"] = 0
                payload["questionGeneration"][enabled_field] = 1

                errors = validate_example_payload(name, payload)

                self.assertIn(
                    f"{name}: questionGeneration: source-only mode requires "
                    "both generated question quotas to be zero",
                    errors,
                )

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
            (
                "examples/lesson.example.json",
                ("materialSections", 0, "sourceRefs"),
            ),
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

    def test_source_reference_enforces_exact_shape_and_string_context(self):
        name = "examples/generated-question.example.json"
        cases = (
            (
                "unknown-field",
                {**self.source_ref, "unknown": "not allowed"},
                "sourceRefs[0]: unexpected keys: unknown",
            ),
            (
                "non-string-context",
                {**self.source_ref, "context": 12},
                "sourceRefs[0]: context must be a string",
            ),
        )
        for label, source_ref, expected in cases:
            with self.subTest(label=label):
                payload = self.make_generated_question()
                payload["sourceRefs"][0] = source_ref

                errors = validate_example_payload(name, payload)

                self.assertTrue(any(expected in error for error in errors), errors)

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
                    "collection": "Format examples",
                    "label": f"{source_format} example",
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

    def test_page_and_slide_manifest_locations_enforce_declared_bounds(self):
        name = "examples/source-manifest.example.json"
        for source_format, count_field, location_type in (
            ("pdf", "pages", "page"),
            ("pptx", "slides", "slide"),
        ):
            for location, valid in ((1, True), (3, True), (4, False), ("1", False)):
                with self.subTest(
                    source_format=source_format, location=location, valid=valid
                ):
                    source = {
                        "id": "source-bounds",
                        "fileName": f"example.{source_format}",
                        "collection": "Bounds",
                        "label": "Bounds example",
                        "format": source_format,
                        "checksum": "sha256:bounds-example",
                        count_field: 3,
                        "status": "accepted",
                        "locations": [
                            {"locationType": location_type, "location": location}
                        ],
                    }

                    errors = validate_example_payload(
                        name, {"version": "1.0", "sources": [source]}
                    )

                    if valid:
                        self.assertEqual(errors, [])
                    else:
                        self.assertTrue(
                            any(
                                "location must be an integer from 1 to 3" in e
                                for e in errors
                            ),
                            errors,
                        )

    def test_page_and_slide_references_enforce_declared_bounds(self):
        for source_format, count_field, location_type in (
            ("pdf", "pages", "page"),
            ("pptx", "slides", "slide"),
        ):
            source = {
                "id": "source-bounds",
                "format": source_format,
                count_field: 3,
                "locations": [
                    {"locationType": location_type, "location": location}
                    for location in (1, 3, 4)
                ],
            }
            for location, valid in ((1, True), (3, True), (4, False)):
                with self.subTest(
                    source_format=source_format, location=location, valid=valid
                ):
                    payloads = {
                        "examples/source-manifest.example.json": {"sources": [source]},
                        "examples/official-question.example.json": {
                            "id": "q-bounds",
                            "sourceRefs": [
                                {
                                    "sourceId": "source-bounds",
                                    "locationType": location_type,
                                    "location": location,
                                }
                            ],
                        },
                    }

                    errors = factory_validator.validate_example_links(payloads)

                    if valid:
                        self.assertEqual(errors, [])
                    else:
                        self.assertIn(
                            "examples/official-question.example.json: "
                            f"sourceRefs[0]: {location_type} location must be "
                            "an integer from 1 to 3",
                            errors,
                        )

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
                    "collection": "Format examples",
                    "label": f"{source_format} example",
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

    def test_official_review_item_accepts_explicitly_missing_answer(self):
        name = "examples/official-question.example.json"
        payload = self.load_example(name)
        payload["correctAnswer"] = None
        payload["needsReview"] = True
        payload["reviewNotes"] = "The supplied material has no reliable answer key."

        self.assertEqual(validate_example_payload(name, payload), [])

    def test_scoreable_official_question_rejects_missing_answer(self):
        name = "examples/official-question.example.json"
        payload = self.load_example(name)
        payload["correctAnswer"] = None

        errors = validate_example_payload(name, payload)

        self.assertTrue(
            any(
                "correctAnswer: must be a valid zero-based option index" in e
                for e in errors
            ),
            errors,
        )

    def test_missing_official_answer_rejects_non_string_review_note(self):
        name = "examples/official-question.example.json"
        payload = self.load_example(name)
        payload["correctAnswer"] = None
        payload["needsReview"] = True
        payload["reviewNotes"] = None

        errors = validate_example_payload(name, payload)

        self.assertIn(f"{name}: reviewNotes: must be a string", errors)

    def test_generated_questions_accept_mcq_and_true_false_conditional_shapes(self):
        name = "examples/generated-question.example.json"
        mcq = self.make_generated_question()
        true_false = self.make_generated_question()
        true_false["type"] = "true-false"
        true_false.pop("options")
        true_false["correctAnswer"] = False
        true_false["correctedStatement"] = "The corrected proposition is true."
        true_false.pop("distractorRationales")
        targets = (
            "prompt",
            "correctAnswer",
            "rationale",
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
        true_statement["correctAnswer"] = True
        true_statement["correctedStatement"] = None
        true_statement["evidenceMap"] = [
            evidence
            for evidence in true_statement["evidenceMap"]
            if evidence["target"] != "correctedStatement"
        ]

        self.assertEqual(validate_example_payload(name, mcq), [])
        self.assertEqual(validate_example_payload(name, true_false), [])
        self.assertEqual(validate_example_payload(name, true_statement), [])

    def test_generated_true_false_uses_boolean_answer_without_options(self):
        name = "examples/generated-question.example.json"
        payload = self.make_generated_question()
        payload["type"] = "true-false"
        payload.pop("options")
        payload.pop("distractorRationales")
        payload["correctAnswer"] = False
        payload["correctedStatement"] = "The corrected proposition is true."
        payload["evidenceMap"] = [
            {
                "claimId": f"claim-{index}",
                "target": target,
                "sourceRefs": [self.source_ref],
                "support": "direct",
            }
            for index, target in enumerate(
                ("prompt", "correctAnswer", "rationale", "correctedStatement")
            )
        ]

        self.assertEqual(validate_example_payload(name, payload), [])

    def test_generated_questions_reject_mixed_or_unsupported_type_fields(self):
        name = "examples/generated-question.example.json"
        mixed = self.make_generated_question()
        mixed["correctedStatement"] = None
        mixed_true_false = self.make_generated_question()
        mixed_true_false["type"] = "true-false"
        mixed_true_false["correctAnswer"] = True
        mixed_true_false["correctedStatement"] = None
        mixed_true_false.pop("distractorRationales")
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
                "unexpected top-level keys: options" in e
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
            (True, "Not allowed for true.", "must be null when correctAnswer is true"),
            (False, None, "must be a non-empty string when correctAnswer is false"),
        ):
            with self.subTest(answer=answer):
                payload = self.make_generated_question()
                payload["type"] = "true-false"
                payload.pop("options")
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
                ("materialSections", 0, "linkedQuestionIds"),
                ["q-missing"],
                "materialSections[0].linkedQuestionIds[0] does not resolve",
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
                    payload = factory_validator.parse_json(
                        path.read_text(encoding="utf-8")
                    )
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

    def test_generated_question_objective_must_resolve_to_its_lesson(self):
        for objective_id in ("objective-drift", "objective-"):
            with self.subTest(objective_id=objective_id):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory) / "factory"
                    shutil.copytree(Path("docs/study-site-factory"), root)
                    path = root / "examples" / "generated-question.example.json"
                    payload = factory_validator.parse_json(
                        path.read_text(encoding="utf-8")
                    )
                    payload["learningObjectiveId"] = objective_id
                    path.write_text(json.dumps(payload), encoding="utf-8")

                    errors = validate_kit(root)

                self.assertIn(
                    "examples/generated-question.example.json: "
                    "learningObjectiveId does not resolve to the lesson",
                    errors,
                )

    def test_generated_explanation_must_describe_its_owning_question(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "factory"
            shutil.copytree(Path("docs/study-site-factory"), root)
            path = root / "examples" / "explanation.example.json"
            payload = factory_validator.parse_json(path.read_text(encoding="utf-8"))
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
                ("materialSections", 0, "linkedQuestionIds"),
                7,
                "linkedQuestionIds: must be an array",
            ),
            (
                "lesson.example.json",
                ("materialSections", 0, "linkedQuestionIds"),
                {},
                "linkedQuestionIds: must be an array",
            ),
            (
                "lesson.example.json",
                ("materialSections", 0, "linkedQuestionIds"),
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
                    payload = factory_validator.parse_json(
                        path.read_text(encoding="utf-8")
                    )
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

    def test_malformed_question_and_duplicate_values_aggregate_without_raising(self):
        cases = (
            (
                "duplicate candidates",
                "generated-question.example.json",
                lambda payload: payload["duplicateComparison"].update(
                    {"candidateIds": [{}, {}]}
                ),
                "candidateIds: must contain only non-empty strings",
            ),
            (
                "ordering answer",
                "official-question.example.json",
                lambda payload: (
                    payload.pop("options"),
                    payload.update(
                        {
                            "type": "ordering",
                            "items": [
                                {"id": "step-a", "text": "First"},
                                {"id": "step-b", "text": "Second"},
                            ],
                            "correctAnswer": [{}, {}],
                        }
                    ),
                ),
                "correctAnswer: must order every item ID exactly once",
            ),
            (
                "question type",
                "official-question.example.json",
                lambda payload: payload.update({"type": {}}),
                "type: invalid value: {}",
            ),
            (
                "duplicate match class",
                "generated-question.example.json",
                lambda payload: payload["duplicateComparison"].update(
                    {"matchClass": {}}
                ),
                "duplicateComparison.matchClass: invalid value",
            ),
            (
                "duplicate disposition",
                "generated-question.example.json",
                lambda payload: payload.update({"duplicateDisposition": {}}),
                "duplicateDisposition: invalid value: {}",
            ),
        )
        for case, relative, mutate, expected in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory) / "factory"
                    shutil.copytree(Path("docs/study-site-factory"), root)
                    path = root / "examples" / relative
                    payload = factory_validator.parse_json(
                        path.read_text(encoding="utf-8")
                    )
                    mutate(payload)
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
            "validated": ("validated", "unreviewed", False, None),
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
                payload = factory_validator.parse_json(
                    (root / relative).read_text(encoding="utf-8")
                )
                self.assertTrue(required.issubset(payload))

    def test_generated_mcq_example_has_complete_answer_contract(self):
        payload = factory_validator.parse_json(
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
                payload = self.make_multi_origin_lesson()
                payload["materialSections"][0]["explanation"] = explanation
                errors = validate_example_payload(
                    "examples/lesson.example.json", payload
                )
                self.assertTrue(
                    any(
                        "materialSections[0]: explanation: must contain two to five "
                        "non-empty paragraphs" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_lesson_rejects_recap_outside_three_to_seven_points(self):
        for recap in (
            ["One.", "Two."],
            ["One.", "", "Three."],
            ["One.", "Two.", "Three.", "Four.", "Five.", "Six.", "Seven.", "Eight."],
        ):
            with self.subTest(recap=recap):
                payload = self.make_multi_origin_lesson()
                payload["materialSections"][0]["recap"] = recap
                errors = validate_example_payload(
                    "examples/lesson.example.json", payload
                )
                self.assertTrue(
                    any(
                        "materialSections[0]: recap: must contain three to seven "
                        "non-empty strings" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_lesson_requires_canonical_compilation_fields(self):
        self.assertTrue(
            {
                "objectiveIds",
                "contentVersion",
                "materialSectionIds",
                "materialSections",
                "needsReview",
                "reviewNotes",
            }.issubset(EXAMPLE_REQUIRED_KEYS["examples/lesson.example.json"])
        )

    def test_lesson_declares_generated_material_origin(self):
        payload = self.load_example("examples/lesson.example.json")

        self.assertEqual(
            [section["origin"] for section in payload["materialSections"]],
            ["source", "generated"],
        )
        self.assertEqual(
            [section["label"] for section in payload["materialSections"]],
            ["Source material", "Generated study guidance"],
        )
        self.assertEqual(
            [
                section["generatedStudyGuidance"]
                for section in payload["materialSections"]
            ],
            [False, True],
        )

    def test_lesson_spec_defines_each_content_policy_mode(self):
        text = Path("docs/study-site-factory/05-MATERIAL-LESSONS-SPEC.md").read_text(
            encoding="utf-8"
        )

        for mode in ("`source-only`", "`source-plus-generated`", "`generated-only`"):
            with self.subTest(mode=mode):
                self.assertIn(mode, text)
        self.assertIn("`origin: source`", text)
        self.assertIn("`origin: generated`", text)

    def test_multi_origin_lesson_compiles_distinct_ordered_material_sections(self):
        compile_sections = getattr(
            factory_validator, "compile_lesson_material_sections", lambda payload: ()
        )
        payload = self.make_multi_origin_lesson()

        self.assertEqual(
            validate_example_payload("examples/lesson.example.json", payload), []
        )
        compiled = compile_sections(payload)
        self.assertEqual(
            tuple(
                (
                    section["id"],
                    section["lessonId"],
                    section["order"],
                    section["origin"],
                    section["label"],
                    section["generatedStudyGuidance"],
                    section["sourceRefs"],
                )
                for section in compiled
            ),
            (
                (
                    "material-section-dhcp-source",
                    "lesson-dhcp-across-subnets",
                    1,
                    "source",
                    "Source material",
                    False,
                    [self.source_ref],
                ),
                (
                    "material-section-dhcp-guidance",
                    "lesson-dhcp-across-subnets",
                    2,
                    "generated",
                    "Generated study guidance",
                    True,
                    [
                        {
                            "sourceId": "source-02",
                            "locationType": "slide",
                            "location": 5,
                        }
                    ],
                ),
            ),
        )
        expected_keys = {
            "id",
            "lessonId",
            "order",
            "title",
            "origin",
            "label",
            "generatedStudyGuidance",
            "summaries",
            "terms",
            "examples",
            "mistakes",
            "examTips",
            "recaps",
            "sourceRefs",
            "linkedQuestionIds",
            "contentVersion",
            "needsReview",
            "reviewNotes",
        }
        self.assertEqual(
            tuple(set(section) for section in compiled), (expected_keys, expected_keys)
        )

    def test_multi_origin_lesson_rejects_ambiguous_section_identity_and_origin(self):
        name = "examples/lesson.example.json"
        mutations = []

        duplicate_id = self.make_multi_origin_lesson()
        duplicate_id["materialSections"][1]["id"] = duplicate_id["materialSections"][0][
            "id"
        ]
        mutations.append(
            ("duplicate-id", duplicate_id, "materialSections: IDs must be unique")
        )

        duplicate_order = self.make_multi_origin_lesson()
        duplicate_order["materialSections"][1]["order"] = 1
        mutations.append(
            (
                "duplicate-order",
                duplicate_order,
                "materialSections: order values must be unique",
            )
        )

        wrong_sequence = self.make_multi_origin_lesson()
        wrong_sequence["materialSections"].reverse()
        mutations.append(
            (
                "wrong-sequence",
                wrong_sequence,
                "materialSections: must be sorted by ascending order",
            )
        )

        wrong_id_index = self.make_multi_origin_lesson()
        wrong_id_index["materialSectionIds"].reverse()
        mutations.append(
            (
                "wrong-id-index",
                wrong_id_index,
                "materialSectionIds: must equal materialSections IDs in order",
            )
        )

        wrong_label = self.make_multi_origin_lesson()
        wrong_label["materialSections"][1]["label"] = "Source material"
        mutations.append(("wrong-label", wrong_label, "label: must match origin"))

        wrong_guidance = self.make_multi_origin_lesson()
        wrong_guidance["materialSections"][0]["generatedStudyGuidance"] = True
        mutations.append(
            (
                "wrong-guidance",
                wrong_guidance,
                "generatedStudyGuidance: must match origin",
            )
        )

        missing_sources = self.make_multi_origin_lesson()
        missing_sources["materialSections"][1]["sourceRefs"] = []
        mutations.append(
            (
                "missing-sources",
                missing_sources,
                "sourceRefs: must contain at least one source reference",
            )
        )

        body_drift = self.make_multi_origin_lesson()
        body_drift["materialSections"][0]["body"] = "Drifted body."
        mutations.append(
            (
                "body-drift",
                body_drift,
                "body: must equal explanation paragraphs joined with two newlines",
            )
        )

        for label, payload, expected in mutations:
            with self.subTest(label=label):
                errors = validate_example_payload(name, payload)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_lesson_rejects_canonical_body_or_objective_mapping_drift(self):
        payload = self.make_multi_origin_lesson()
        payload["learningObjectives"][0]["id"] = "objective-dns"
        payload["materialSections"][0]["body"] = "Drifted body."

        errors = validate_example_payload("examples/lesson.example.json", payload)

        self.assertIn(
            "examples/lesson.example.json: learningObjectives: IDs must "
            "equal objectiveIds in the same order",
            errors,
        )
        self.assertTrue(
            any(
                "materialSections[0]: body: must equal explanation paragraphs "
                "joined with two newlines" in error
                for error in errors
            ),
            errors,
        )

    def test_lesson_rejects_empty_canonical_objective_ids(self):
        payload = self.make_multi_origin_lesson()
        payload["objectiveIds"] = [""]
        payload["learningObjectives"][0]["id"] = ""
        errors = validate_example_payload("examples/lesson.example.json", payload)

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

    def test_validated_generated_question_is_not_a_review_item(self):
        name = "examples/generated-question.example.json"
        payload = self.make_generated_question("validated")
        payload["needsReview"] = False

        self.assertEqual(validate_example_payload(name, payload), [])

    def test_question_spec_honors_configured_mock_exam_review_gate(self):
        text = Path("docs/study-site-factory/06-QUESTION-GENERATION-SPEC.md").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "When `generatedQuestionsRequireHumanReviewForExam` is false, a "
            "validated item may enter Mock Exam",
            text,
        )
        prd = Path("docs/study-site-factory/02-PRD-TEMPLATE.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "human-approved when that policy requires human review",
            " ".join(prd.split()),
        )

    def test_mock_exam_eligibility_reference_policy_matrix(self):
        eligible = getattr(
            factory_validator,
            "generated_question_is_mock_exam_eligible",
            lambda *args, **kwargs: False,
        )
        validated = self.make_generated_question("validated")
        human_reviewed = self.make_generated_question("human-reviewed")
        human_reviewed["review"]["approval"]["notes"] = "Eligibility review completed."
        draft = self.make_generated_question("draft")
        needs_review = self.make_generated_question("needs-review")
        rejected = self.make_generated_question("rejected")

        cases = (
            ("validated-open-gate", validated, False, False, True, True),
            ("validated-human-gate", validated, True, False, True, False),
            ("validated-high-stakes", validated, False, True, True, False),
            ("human-open-gate", human_reviewed, False, False, True, True),
            ("human-required-gate", human_reviewed, True, False, True, True),
            ("human-high-stakes", human_reviewed, False, True, True, True),
            ("non-scoreable", human_reviewed, False, False, False, False),
            ("draft-open-gate", draft, False, False, True, False),
            ("draft-high-stakes", draft, False, True, True, False),
            ("needs-review-open-gate", needs_review, False, False, True, False),
            ("needs-review-high-stakes", needs_review, False, True, True, False),
            ("rejected-open-gate", rejected, False, False, True, False),
            ("rejected-high-stakes", rejected, False, True, True, False),
        )
        for (
            label,
            record,
            require_human,
            high_stakes,
            is_scoreable,
            expected,
        ) in cases:
            with self.subTest(label=label):
                self.assertIs(
                    eligible(
                        copy.deepcopy(record),
                        generated_questions_require_human_review=require_human,
                        high_stakes=high_stakes,
                        is_scoreable=is_scoreable,
                    ),
                    expected,
                )

    def test_mock_exam_eligibility_requires_complete_human_approval(self):
        eligible = factory_validator.generated_question_is_mock_exam_eligible
        base = self.make_generated_question("human-reviewed")
        base["review"]["approval"]["notes"] = "Eligibility review completed."
        cases = []

        missing_approval = copy.deepcopy(base)
        missing_approval["review"].pop("approval")
        cases.append(("missing-approval", missing_approval))

        malformed_approval = copy.deepcopy(base)
        malformed_approval["review"]["approval"] = []
        cases.append(("malformed-approval", malformed_approval))

        for field in (
            "reviewedRecordId",
            "reviewedContentVersion",
            "status",
            "decision",
            "reviewer",
            "reviewedAt",
            "reason",
            "notes",
        ):
            missing_field = copy.deepcopy(base)
            del missing_field["review"]["approval"][field]
            cases.append((f"missing-{field}", missing_field))

        for field, malformed_value in (
            ("reviewedRecordId", 7),
            ("reviewedContentVersion", "not-a-version"),
            ("status", "pending"),
            ("decision", "needs-review"),
            ("reviewer", ""),
            ("reviewedAt", "not-a-date"),
            ("reason", ""),
            ("notes", ""),
        ):
            malformed_field = copy.deepcopy(base)
            malformed_field["review"]["approval"][field] = malformed_value
            cases.append((f"malformed-{field}", malformed_field))

        for label, record in cases:
            for high_stakes in (False, True):
                with self.subTest(label=label, high_stakes=high_stakes):
                    self.assertIs(
                        eligible(
                            record,
                            generated_questions_require_human_review=False,
                            high_stakes=high_stakes,
                            is_scoreable=True,
                        ),
                        False,
                    )

    def test_reviewed_at_requires_a_real_utc_datetime(self):
        invalid_values = (
            "2026-99-22T10:30:00Z",
            "2026-02-30T10:30:00Z",
            "2026-08-22T25:30:00Z",
            "2026-08-22T10:30:00+00:00",
        )
        for reviewed_at in invalid_values:
            with self.subTest(reviewed_at=reviewed_at):
                payload = self.make_generated_question("human-reviewed")
                payload["review"]["approval"]["reviewedAt"] = reviewed_at

                errors = validate_example_payload(
                    "examples/generated-question.example.json", payload
                )

                self.assertIn(
                    "examples/generated-question.example.json: "
                    "review.approval.reviewedAt: must be ISO 8601 UTC",
                    errors,
                )
                self.assertFalse(
                    factory_validator.generated_question_is_mock_exam_eligible(
                        payload,
                        generated_questions_require_human_review=False,
                        high_stakes=False,
                        is_scoreable=True,
                    )
                )

    def test_mock_exam_eligibility_rejects_invalid_record_states(self):
        eligible = getattr(
            factory_validator,
            "generated_question_is_mock_exam_eligible",
            lambda *args, **kwargs: True,
        )
        base = self.make_generated_question("human-reviewed")
        base["review"]["approval"]["notes"] = "Eligibility review completed."
        cases = []

        stale_version = copy.deepcopy(base)
        stale_version["review"]["approval"]["reviewedContentVersion"] = "0.9.0"
        cases.append(("stale-version", stale_version))

        stale_id = copy.deepcopy(base)
        stale_id["review"]["approval"]["reviewedRecordId"] = "gq-stale"
        cases.append(("stale-record-id", stale_id))

        review_only = copy.deepcopy(base)
        review_only["needsReview"] = True
        cases.append(("review-only", review_only))

        duplicate = copy.deepcopy(base)
        duplicate["duplicateDisposition"] = "reject-duplicate"
        cases.append(("duplicate", duplicate))

        wrong_quality = copy.deepcopy(base)
        wrong_quality["qualityState"] = "validated"
        cases.append(("wrong-quality-state", wrong_quality))

        wrong_review_state = copy.deepcopy(base)
        wrong_review_state["reviewState"] = "unreviewed"
        cases.append(("wrong-review-state", wrong_review_state))

        rejected_approval = copy.deepcopy(base)
        rejected_approval["review"]["approval"]["decision"] = "rejected"
        cases.append(("rejected-approval", rejected_approval))

        validated_with_approval = self.make_generated_question("validated")
        validated_with_approval["review"]["approval"] = copy.deepcopy(
            base["review"]["approval"]
        )
        cases.append(("validated-with-approval", validated_with_approval))

        for label, record in cases:
            with self.subTest(label=label):
                self.assertIs(
                    eligible(
                        record,
                        generated_questions_require_human_review=False,
                        high_stakes=False,
                        is_scoreable=True,
                    ),
                    False,
                )

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

    def test_json_parsing_rejects_nested_duplicate_object_keys(self):
        duplicate_json = '{"outer": {"stableId": "first", "stableId": "second"}}'
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key: stableId"):
            factory_validator.parse_json(duplicate_json)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text(duplicate_json, encoding="utf-8")
            errors = validate_json_file(path)

        self.assertTrue(
            any("duplicate JSON object key: stableId" in error for error in errors),
            errors,
        )

    def test_complete_validation_rejects_nested_duplicate_object_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "factory"
            shutil.copytree(Path("docs/study-site-factory"), root)
            path = root / "examples" / "project-config.example.json"
            text = path.read_text(encoding="utf-8").replace(
                '"difficultyPercent": {"easy": 30,',
                '"difficultyPercent": {"easy": 30, "easy": 30,',
                1,
            )
            path.write_text(text, encoding="utf-8")

            errors = validate_kit(root)

        self.assertTrue(
            any("duplicate JSON object key: easy" in error for error in errors),
            errors,
        )

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

    def test_ux_navigation_includes_question_explanations(self):
        text = Path("docs/study-site-factory/07-UX-AND-SYSTEM-FLOW.md").read_text(
            encoding="utf-8"
        )
        section = text.split("## Navigation and responsiveness", 1)[1].split(
            "## Route-level states", 1
        )[0]
        normalized = " ".join(section.split())

        self.assertIn(
            "Question Bank, Question Explanations, Revision Summary", normalized
        )
        self.assertIn(
            "A More menu contains Question Bank, Question Explanations", normalized
        )

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

    def test_deployment_verdict_accepts_complete_push_or_dispatch_evidence(self):
        is_verified = getattr(
            factory_validator, "deployment_is_verified", lambda *args, **kwargs: False
        )
        for event in ("push", "workflow_dispatch"):
            with self.subTest(event=event):
                evidence = self.make_deployment_evidence(event)
                self.assertTrue(
                    is_verified(evidence, expected_commit=evidence["releaseCommit"])
                )

    def test_deployment_verdict_rejects_incomplete_or_stale_gate_8_evidence(self):
        is_verified = getattr(
            factory_validator, "deployment_is_verified", lambda *args, **kwargs: True
        )
        mutations = []

        invalid_event = self.make_deployment_evidence()
        invalid_event["workflow"]["event"] = "schedule"
        mutations.append(("invalid-event", invalid_event))

        wrong_workflow_commit = self.make_deployment_evidence()
        wrong_workflow_commit["workflow"]["headSha"] = "b" * 40
        mutations.append(("wrong-workflow-commit", wrong_workflow_commit))

        failed_job = self.make_deployment_evidence()
        failed_job["workflow"]["jobs"]["deploy"] = "failure"
        mutations.append(("failed-job", failed_job))

        stale_html = self.make_deployment_evidence()
        stale_html["publicHtml"]["commit"] = "b" * 40
        mutations.append(("stale-html", stale_html))

        missing_payload = self.make_deployment_evidence()
        missing_payload["publicPayloads"].pop()
        mutations.append(("missing-payload", missing_payload))

        count_mismatch = self.make_deployment_evidence()
        count_mismatch["publicPayloads"][0]["publicCount"] = 0
        mutations.append(("count-mismatch", count_mismatch))

        id_mismatch = self.make_deployment_evidence()
        id_mismatch["publicPayloads"][0]["publicIds"] = ["lesson-stale"]
        mutations.append(("id-mismatch", id_mismatch))

        missing_viewport = self.make_deployment_evidence()
        missing_viewport["browserSmokes"].pop()
        mutations.append(("missing-viewport", missing_viewport))

        browser_errors = self.make_deployment_evidence()
        browser_errors["browserSmokes"][0]["consoleErrors"] = 1
        mutations.append(("browser-errors", browser_errors))

        missing_browser_check = self.make_deployment_evidence()
        missing_browser_check["browserSmokes"][0]["checks"].remove("Material")
        mutations.append(("missing-browser-check", missing_browser_check))

        for label, evidence in mutations:
            with self.subTest(label=label):
                self.assertFalse(
                    is_verified(
                        evidence,
                        expected_commit=self.make_deployment_evidence()[
                            "releaseCommit"
                        ],
                    )
                )

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
        normalized = " ".join(text.split())
        self.assertIn(
            "Items marked `Needs review — unscored` are excluded from every "
            "Mock Exam pool.",
            normalized,
        )
        self.assertIn(
            "Generated questions may enter a Mock Exam only when they are "
            "validated and scoreable",
            normalized,
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
        self.assertIn("eligible for scored Practice", text)
        self.assertIn("additional configured human-review gate", text)

    def test_source_manifest_preserves_configured_collection_and_label(self):
        payload = self.load_example("examples/source-manifest.example.json")

        for source in payload["sources"]:
            with self.subTest(source_id=source["id"]):
                self.assertIsInstance(source.get("collection"), str)
                self.assertTrue(source["collection"].strip())
                self.assertIsInstance(source.get("label"), str)
                self.assertTrue(source["label"].strip())

    def test_ingestion_covers_compatible_document_and_slide_formats(self):
        text = Path("docs/study-site-factory/03-SOURCE-INGESTION-SPEC.md").read_text(
            encoding="utf-8"
        )

        for extension in ("`.doc`", "`.odt`", "`.rtf`", "`.ppt`", "`.odp`"):
            with self.subTest(extension=extension):
                self.assertIn(extension, text)
        self.assertIn("preserves the original file and checksum", text)

    def test_generated_content_examples_bind_approval_to_content_version(self):
        for name in (
            "examples/lesson.example.json",
            "examples/explanation.example.json",
        ):
            with self.subTest(name=name):
                payload = self.load_example(name)
                self.assertRegex(payload.get("contentVersion", ""), r"^\d+\.\d+\.\d+$")
                self.assertEqual(
                    payload["review"]["approval"]["reviewedContentVersion"],
                    payload["contentVersion"],
                )

    def test_content_contract_declares_exact_generated_example_fields(self):
        text = Path(
            "docs/study-site-factory/04-CONTENT-AND-DATA-CONTRACTS.md"
        ).read_text(encoding="utf-8")
        section = text.split("## Generated Question Quality and Duplication", 1)[
            1
        ].split("## Question Explanation", 1)[0]

        for field in (
            "rationale",
            "bloomLevel",
            "learningObjectiveId",
            "contentVersion",
            "review",
        ):
            with self.subTest(field=field):
                self.assertIn(f"`{field}`", section)

    def test_content_contract_declares_exact_explanation_example_fields(self):
        text = Path(
            "docs/study-site-factory/04-CONTENT-AND-DATA-CONTRACTS.md"
        ).read_text(encoding="utf-8")
        section = text.split("## Question Explanation", 1)[1].split(
            "## Review State and Scoring", 1
        )[0]

        for field in (
            "language",
            "generatedStudyGuidance",
            "translation",
            "explanation",
            "body",
            "note",
            "contentVersion",
            "review",
        ):
            with self.subTest(field=field):
                self.assertIn(f"`{field}`", section)

    def test_true_false_answer_order_has_a_stable_reproducible_input(self):
        text = Path("docs/study-site-factory/06-QUESTION-GENERATION-SPEC.md").read_text(
            encoding="utf-8"
        )

        for contract in (
            "SHA-256",
            "`project.slug`",
            "`lesson.id`",
            "`TTFF`, `TFTF`, `TFFT`, `FTTF`, `FTFT`, `FFTT`",
            "first `floor(P / 2)` records",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, text)

    def test_default_true_false_assignment_matches_golden_vector(self):
        digest = getattr(
            factory_validator, "true_false_default_seed_digest", lambda *args: ""
        )
        assign = getattr(
            factory_validator, "default_true_false_answer_assignment", lambda *args: ()
        )

        self.assertEqual(
            digest("network-fundamentals-study", "lesson-dhcp"),
            "8ac2ef592fffbe692d7a716f305d4ea2e313f6bb20f46f4b14c9f89a0df53bd4",
        )
        self.assertEqual(
            assign(
                "network-fundamentals-study",
                "lesson-dhcp",
                ("gq-dhcp-004", "gq-dhcp-001", "gq-dhcp-003", "gq-dhcp-002"),
            ),
            (
                ("gq-dhcp-001", False),
                ("gq-dhcp-002", True),
                ("gq-dhcp-003", True),
                ("gq-dhcp-004", False),
            ),
        )

    def test_nondefault_even_true_false_assignment_matches_golden_vector(self):
        digest = getattr(
            factory_validator, "true_false_record_digest", lambda *args: ""
        )
        assign = getattr(
            factory_validator,
            "nondefault_true_false_answer_assignment",
            lambda *args: (),
        )
        question_ids = (
            "gq-pool-06",
            "gq-pool-01",
            "gq-pool-04",
            "gq-pool-02",
            "gq-pool-05",
            "gq-pool-03",
        )

        self.assertEqual(
            digest("network-fundamentals-study", "gq-pool-05"),
            "70adb69e40b40a3bc619f35d8b5b4094d608eca0e17952c10d04091f2b41cc54",
        )
        self.assertEqual(
            assign("network-fundamentals-study", question_ids),
            (
                ("gq-pool-05", True),
                ("gq-pool-01", True),
                ("gq-pool-03", True),
                ("gq-pool-02", False),
                ("gq-pool-06", False),
                ("gq-pool-04", False),
            ),
        )

    def test_nondefault_odd_true_false_assignment_matches_both_residual_vectors(self):
        assign = getattr(
            factory_validator,
            "nondefault_true_false_answer_assignment",
            lambda *args: (),
        )
        question_ids = (
            "gq-odd-05",
            "gq-odd-02",
            "gq-odd-04",
            "gq-odd-01",
            "gq-odd-03",
        )

        self.assertEqual(
            assign("network-fundamentals-study", question_ids),
            (
                ("gq-odd-03", True),
                ("gq-odd-05", True),
                ("gq-odd-01", False),
                ("gq-odd-04", False),
                ("gq-odd-02", True),
            ),
        )
        self.assertEqual(
            assign("security-study", question_ids),
            (
                ("gq-odd-04", True),
                ("gq-odd-03", True),
                ("gq-odd-05", False),
                ("gq-odd-02", False),
                ("gq-odd-01", False),
            ),
        )

    def test_question_generation_profile_honors_configured_overrides(self):
        text = Path("docs/study-site-factory/06-QUESTION-GENERATION-SPEC.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("defaults unless project configuration overrides them", text)
        self.assertIn("largest-remainder allocation", text)

    def test_project_input_identifies_github_pages_as_fixed_provider(self):
        text = Path("docs/study-site-factory/01-PROJECT-INPUT-TEMPLATE.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("- Hosting provider: GitHub Pages (fixed for this kit).", text)

    def test_project_input_declares_restrained_brand_color_tokens(self):
        project_input = Path(
            "docs/study-site-factory/01-PROJECT-INPUT-TEMPLATE.md"
        ).read_text(encoding="utf-8")
        prd = Path("docs/study-site-factory/02-PRD-TEMPLATE.md").read_text(
            encoding="utf-8"
        )

        for token in ("{{BRAND_PRIMARY_COLOR}}", "{{BRAND_ACCENT_COLOR}}"):
            with self.subTest(token=token):
                self.assertIn(token, project_input)
                self.assertIn(token, prd)

    def test_project_input_declares_default_practice_count(self):
        project_input = Path(
            "docs/study-site-factory/01-PROJECT-INPUT-TEMPLATE.md"
        ).read_text(encoding="utf-8")
        prd = Path("docs/study-site-factory/02-PRD-TEMPLATE.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("{{DEFAULT_PRACTICE_COUNT}}", project_input)
        self.assertIn("{{DEFAULT_PRACTICE_COUNT}}", prd)

    def test_source_corrections_invalidate_version_bound_approval(self):
        text = Path("docs/study-site-factory/11-HANDOFF-AND-DEPLOYMENT.md").read_text(
            encoding="utf-8"
        )
        section = text.split("### Source-derived content", 1)[1].split(
            "### Generated content", 1
        )[0]
        normalized = " ".join(section.split())

        self.assertIn("increments `contentVersion`", normalized)
        self.assertIn("invalidates any prior approval", normalized)

    def test_factory_docs_do_not_reference_internal_task_numbers(self):
        for path in Path("docs/study-site-factory").glob("*.md"):
            with self.subTest(path=path):
                self.assertNotRegex(path.read_text(encoding="utf-8"), r"\bTask \d+\b")


if __name__ == "__main__":
    unittest.main()
