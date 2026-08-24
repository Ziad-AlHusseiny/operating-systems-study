"""Regression tests for deterministic Operating Systems public payloads."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from scripts.build_os_site_data import (
    ROOT,
    build_payloads,
    build_reports,
    measure_payloads,
    eligible_question_ids,
    load_content_parts,
    payload_bytes,
    validate_payloads,
    write_artifacts,
)
from scripts.validate_os_site import _independent_checks


class BuildOperatingSystemsSiteDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payloads = build_payloads(load_content_parts())

    def test_build_combines_all_canonical_records(self):
        self.assertEqual(7, len(self.payloads["course"]["modules"]))
        self.assertEqual(21, len(self.payloads["lessons"]["lessons"]))
        self.assertEqual(210, len(self.payloads["questions"]["questions"]))
        self.assertEqual(210, len(self.payloads["explanations-ar"]["explanations"]))

    def test_project_input_matches_low_stakes_exam_policy_and_pages_deployment(self):
        config = json.loads((ROOT / "input" / "project-config.json").read_text(encoding="utf-8"))
        project_input = (ROOT / "input" / "PROJECT_INPUT.md").read_text(encoding="utf-8")
        self.assertFalse(config["contentPolicy"]["generatedQuestionsRequireHumanReviewForExam"])
        self.assertIn("Human review is not required only for source-backed, validated, low-stakes study questions.", project_input)
        self.assertIn("High-stakes, credentialing, admissions, employment, compliance, and externally reported assessment remain prohibited without complete current human approval.", project_input)
        self.assertIn("GitHub repository: Ziad-AlHusseiny/operating-systems-study", project_input)
        self.assertIn("GitHub branch: main", project_input)
        self.assertIn("Public URL: https://ziad-alhusseiny.github.io/operating-systems-study/", project_input)

    def test_chapters_one_and_two_explanation_bodies_join_every_arabic_paragraph_and_reviewed_records_are_precise(self):
        parts = load_content_parts()
        first_part = parts[0]
        self.assertEqual(70, len(first_part["explanations"]))
        for explanation in first_part["explanations"]:
            self.assertEqual("\n\n".join(explanation["explanation"]), explanation["body"], explanation["id"])

        question = next(item for part in parts for item in part["questions"] if item["id"] == "gq-os-ch05-part3-010")
        self.assertEqual("Priority and round-robin scheduling trace", question["topic"])
        scheduling_note = next(item for part in parts for item in part["explanations"] if item["questionId"] == question["id"])["note"]
        self.assertIn("الجدولة بالأولوية وبالدوران الدوري", scheduling_note)

        priority_explanation = next(item for part in parts for item in part["explanations"] if item["questionId"] == "gq-os-ch06-part2-009")
        joined_priority_text = " ".join(priority_explanation["explanation"])
        self.assertIn("توريث الأولوية", joined_priority_text)
        self.assertNotIn("أو تحريره", joined_priority_text)
        self.assertNotIn("or release it", joined_priority_text)

    def test_valid_payloads_resolve_every_public_reference(self):
        self.assertEqual([], validate_payloads(self.payloads))

    def test_invalid_question_id_and_unknown_public_key_are_rejected(self):
        mutated = copy.deepcopy(self.payloads)
        mutated["questions"]["questions"][0]["id"] = "question-invalid"
        mutated["questions"]["questions"][1]["unexpected"] = True
        errors = validate_payloads(mutated)
        self.assertTrue(any("question id" in error.lower() for error in errors))
        self.assertTrue(any("unexpected keys" in error.lower() for error in errors))

    def test_invalid_answer_and_duplicate_normalized_prompt_are_rejected(self):
        mutated = copy.deepcopy(self.payloads)
        questions = mutated["questions"]["questions"]
        questions[0]["correctAnswer"] = "one"
        questions[1]["prompt"] = questions[0]["prompt"].upper() + "!!!"
        errors = validate_payloads(mutated)
        self.assertTrue(any("answer index" in error.lower() for error in errors))
        self.assertTrue(any("duplicate normalized prompt" in error.lower() for error in errors))

    def test_review_state_and_exam_gate_are_enforced(self):
        require_review = copy.deepcopy(self.payloads)
        require_review["course"]["contentPolicy"]["generatedQuestionsRequireHumanReviewForExam"] = True
        self.assertEqual([], eligible_question_ids(require_review, "mock-exam"))
        mutated = copy.deepcopy(self.payloads)
        mutated["questions"]["questions"][0]["review"]["status"] = "draft"
        errors = validate_payloads(mutated)
        self.assertTrue(any("review state" in error.lower() for error in errors))

    def test_page_classification_and_complete_coverage_are_enforced(self):
        mutated = copy.deepcopy(self.payloads)
        mutated["lessons"]["lessons"][0]["materialSections"][0]["sourceRefs"][0]["location"] = 999
        errors = validate_payloads(mutated)
        self.assertTrue(any("page bounds" in error.lower() for error in errors))
        mutated = copy.deepcopy(self.payloads)
        mutated["course"]["coverage"]["referencedTeachingPages"].pop()
        errors = validate_payloads(mutated)
        self.assertTrue(any("coverage" in error.lower() for error in errors))

    def test_arabic_linkage_and_paragraph_completeness_are_enforced(self):
        mutated = copy.deepcopy(self.payloads)
        explanation = mutated["explanations-ar"]["explanations"][0]
        explanation["questionId"] = "gq-missing"
        explanation["explanation"] = ["فقرة واحدة فقط"]
        errors = validate_payloads(mutated)
        self.assertTrue(any("arabic" in error.lower() for error in errors))
        self.assertTrue(any("paragraph" in error.lower() for error in errors))

    def test_dangerous_source_text_stays_in_json_data(self):
        parts = load_content_parts()
        parts[0]["lessons"][0]["materialSections"][0]["summary"] = '<img src=x onerror="alert(1)">'
        payloads = build_payloads(parts)
        encoded = payload_bytes(payloads["lessons"])
        self.assertIn(b'\\"alert(1)\\"', encoded)
        self.assertNotIn(b"<script>", encoded)

    def test_check_mode_detects_artifact_drift(self):
        write_artifacts(self.payloads)
        course_path = ROOT / "study-website" / "data" / "course.json"
        original = course_path.read_bytes()
        course_path.write_bytes(original + b" ")
        completed = subprocess.run(
            [sys.executable, "-B", "scripts/build_os_site_data.py", "--check"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        course_path.write_bytes(original)
        self.assertNotEqual(0, completed.returncode)
        self.assertIn("drift", completed.stderr.lower() + completed.stdout.lower())

    def test_missing_generated_explanation_id_is_rejected(self):
        mutated = copy.deepcopy(self.payloads)
        del mutated["questions"]["questions"][0]["generatedExplanationId"]
        self.assertTrue(any("generatedexplanationid" in error.lower() for error in validate_payloads(mutated)))

    def test_unresolved_module_objective_is_rejected(self):
        mutated = copy.deepcopy(self.payloads)
        mutated["course"]["modules"][0]["objectiveIds"][0] = "objective-missing"
        self.assertTrue(any("module objective" in error.lower() for error in validate_payloads(mutated)))

    def test_nonsemantic_content_version_is_rejected(self):
        mutated = copy.deepcopy(self.payloads)
        mutated["lessons"]["lessons"][0]["contentVersion"] = "version-one"
        self.assertTrue(any("content version" in error.lower() for error in validate_payloads(mutated)))

    def test_unknown_nested_review_and_provenance_keys_are_rejected(self):
        mutated = copy.deepcopy(self.payloads)
        question = mutated["questions"]["questions"][0]
        question["review"]["extra"] = True
        question["provenance"]["extra"] = True
        self.assertTrue(any("review" in error.lower() and "unexpected" in error.lower() for error in validate_payloads(mutated)))
        self.assertTrue(any("provenance" in error.lower() and "unexpected" in error.lower() for error in validate_payloads(mutated)))

    def test_duplicate_section_id_is_rejected(self):
        mutated = copy.deepcopy(self.payloads)
        second = mutated["lessons"]["lessons"][1]["materialSections"][0]
        second["id"] = mutated["lessons"]["lessons"][0]["materialSections"][0]["id"]
        self.assertTrue(any("duplicate section" in error.lower() for error in validate_payloads(mutated)))

    def test_eighth_module_and_out_of_order_public_records_are_rejected(self):
        mutated = copy.deepcopy(self.payloads)
        extra = copy.deepcopy(mutated["course"]["modules"][0])
        extra["id"] = "module-extra"
        extra["order"] = 8
        mutated["course"]["modules"].append(extra)
        mutated["lessons"]["lessons"].reverse()
        mutated["explanations-ar"]["explanations"].reverse()
        errors = validate_payloads(mutated)
        self.assertTrue(any("module total" in error.lower() for error in errors))
        self.assertTrue(any("lessons are not ordered" in error.lower() for error in errors))
        self.assertTrue(any("explanations are not ordered" in error.lower() for error in errors))

    def test_question_objective_must_belong_to_its_own_lesson(self):
        mutated = copy.deepcopy(self.payloads)
        mutated["questions"]["questions"][0]["learningObjectiveId"] = mutated["lessons"]["lessons"][1]["objectiveIds"][0]
        self.assertTrue(any("owning lesson" in error.lower() for error in validate_payloads(mutated)))

    def test_guidance_flag_and_prohibited_official_exam_wording_are_rejected(self):
        mutated = copy.deepcopy(self.payloads)
        mutated["explanations-ar"]["explanations"][0]["generatedStudyGuidance"] = "true"
        mutated["questions"]["questions"][0]["prompt"] = "Official exam question: choose the answer"
        errors = validate_payloads(mutated)
        self.assertTrue(any("guidance flag" in error.lower() for error in errors))
        self.assertTrue(any("prohibited" in error.lower() for error in errors))

    def test_human_reviewed_question_is_exam_eligible_when_gate_is_enabled(self):
        mutated = copy.deepcopy(self.payloads)
        question = mutated["questions"]["questions"][0]
        question["qualityState"] = "approved"
        question["reviewState"] = "approved"
        question["review"] = {
            "status": "human-reviewed",
            "approval": {
                "reviewedRecordId": question["id"],
                "reviewedContentVersion": question["contentVersion"],
                "status": "completed",
                "decision": "approved",
                "reviewer": "reviewer-1",
                "reviewedAt": "2026-08-23T12:00:00Z",
                "reason": "Evidence and rubric checked.",
                "notes": "Approved for low-stakes use."
            }
        }
        mutated["course"]["contentPolicy"]["generatedQuestionsRequireHumanReviewForExam"] = True
        self.assertEqual([question["id"]], eligible_question_ids(mutated, "mock-exam"))

    def test_reports_measure_mutated_outcomes_instead_of_printing_constants(self):
        mutated = copy.deepcopy(self.payloads)
        mutated["course"]["coverage"]["referencedTeachingPages"].pop()
        reports = build_reports(mutated)
        self.assertIn("missing 1", reports["coverage"])

    def test_html_round_trips_as_parsed_inert_json_data(self):
        parts = load_content_parts()
        parts[0]["lessons"][0]["materialSections"][0]["summary"] = '<img src=x onerror="alert(1)">'
        payload = build_payloads(parts)["lessons"]
        parsed = json.loads(payload_bytes(payload))
        self.assertEqual('<img src=x onerror="alert(1)">', parsed["lessons"][0]["materialSections"][0]["summaries"][0]["body"])

    def test_non_teaching_page_classification_and_duplicate_source_id_are_rejected(self):
        mutated = copy.deepcopy(self.payloads)
        mutated["lessons"]["lessons"][0]["materialSections"][0]["sourceRefs"][0]["location"] = 1
        mutated["course"]["sources"][1]["id"] = mutated["course"]["sources"][0]["id"]
        errors = validate_payloads(mutated)
        self.assertTrue(any("non-teaching" in error.lower() for error in errors))
        self.assertTrue(any("duplicate source" in error.lower() for error in errors))

    def test_malformed_nested_record_and_stale_human_approval_are_rejected_without_crashing(self):
        mutated = copy.deepcopy(self.payloads)
        question = mutated["questions"]["questions"][0]
        question["provenance"] = []
        errors = validate_payloads(mutated)
        self.assertTrue(any("provenance must be an object" in error.lower() for error in errors))
        approved = copy.deepcopy(self.payloads)
        question = approved["questions"]["questions"][0]
        question["qualityState"] = "approved"
        question["reviewState"] = "approved"
        question["review"] = {"status": "human-reviewed", "approval": {"reviewedRecordId": question["id"], "reviewedContentVersion": "9.9.9", "status": "completed", "decision": "approved", "reviewer": "reviewer-1", "reviewedAt": "2026-08-23T12:00:00Z", "reason": "checked", "notes": "checked"}}
        self.assertTrue(any("review state" in error.lower() for error in validate_payloads(approved)))

    def test_section_order_and_lesson_review_binding_are_enforced(self):
        mutated = copy.deepcopy(self.payloads)
        lesson = mutated["lessons"]["lessons"][0]
        lesson["materialSections"][1]["order"] = 0
        lesson["review"] = {
            "status": "human-reviewed",
            "approval": {
                "reviewedRecordId": "lesson-other",
                "reviewedContentVersion": lesson["contentVersion"],
                "status": "completed",
                "decision": "approved",
                "reviewer": "reviewer-1",
                "reviewedAt": "2026-08-23T12:00:00Z",
                "reason": "checked",
                "notes": "checked"
            }
        }
        errors = validate_payloads(mutated)
        self.assertTrue(any("section order" in error.lower() for error in errors))
        self.assertTrue(any("lesson review" in error.lower() and "binding" in error.lower() for error in errors))

    def test_invalid_approval_timestamp_and_answer_evidence_exclude_eligibility(self):
        mutated = copy.deepcopy(self.payloads)
        question = mutated["questions"]["questions"][0]
        question["qualityState"] = "approved"
        question["reviewState"] = "approved"
        question["review"] = {"status": "human-reviewed", "approval": {"reviewedRecordId": question["id"], "reviewedContentVersion": question["contentVersion"], "status": "completed", "decision": "approved", "reviewer": "reviewer-1", "reviewedAt": "not-a-dateZ", "reason": "checked", "notes": "checked"}}
        mutated["course"]["contentPolicy"]["generatedQuestionsRequireHumanReviewForExam"] = True
        self.assertNotIn(question["id"], eligible_question_ids(mutated, "mock-exam"))
        question["review"]["approval"]["reviewedAt"] = "2026-08-23T12:00:00Z"
        question["correctAnswer"] = "bad"
        self.assertNotIn(question["id"], eligible_question_ids(mutated, "mock-exam"))

    def test_arabic_review_binding_and_malformed_root_are_rejected(self):
        mutated = copy.deepcopy(self.payloads)
        explanation = mutated["explanations-ar"]["explanations"][0]
        explanation["review"] = {"status": "human-reviewed", "approval": {"reviewedRecordId": "wrong", "reviewedContentVersion": explanation["contentVersion"], "status": "completed", "decision": "approved", "reviewer": "reviewer-1", "reviewedAt": "2026-08-23T12:00:00Z", "reason": "checked", "notes": "checked"}}
        self.assertTrue(any("arabic explanation review" in error.lower() and "binding" in error.lower() for error in validate_payloads(mutated)))
        malformed = copy.deepcopy(self.payloads)
        malformed["course"] = []
        self.assertTrue(validate_payloads(malformed))

    def test_reports_measure_omissions_and_validation_categories(self):
        mutated = copy.deepcopy(self.payloads)
        mutated["lessons"]["lessons"].pop()
        mutated["questions"]["questions"][0]["rationale"] = ""
        mutated["explanations-ar"]["explanations"][0]["translation"] = ""
        mutated["questions"]["questions"][1]["prompt"] = mutated["questions"]["questions"][0]["prompt"]
        reports = build_reports(mutated)
        self.assertIn("omitted lessons 1", reports["coverage"].lower())
        self.assertIn("Evidence/source references: failed", reports["quality"])
        self.assertIn("Arabic records: failed", reports["quality"])
        self.assertIn("duplicate normalized prompts: failed", reports["quality"])

    def test_incomplete_claim_level_evidence_excludes_human_approved_eligibility(self):
        mutated = copy.deepcopy(self.payloads)
        question = mutated["questions"]["questions"][0]
        question["qualityState"] = "approved"
        question["reviewState"] = "approved"
        question["review"] = {"status": "human-reviewed", "approval": {"reviewedRecordId": question["id"], "reviewedContentVersion": question["contentVersion"], "status": "completed", "decision": "approved", "reviewer": "reviewer-1", "reviewedAt": "2026-08-23T12:00:00Z", "reason": "checked", "notes": "checked"}}
        question["evidenceMap"] = [question["evidenceMap"][0]]
        mutated["course"]["contentPolicy"]["generatedQuestionsRequireHumanReviewForExam"] = True
        self.assertNotIn(question["id"], eligible_question_ids(mutated, "mock-exam"))
        self.assertTrue(any("evidence map" in error.lower() for error in validate_payloads(mutated)))
        source_mutated = copy.deepcopy(self.payloads)
        question = source_mutated["questions"]["questions"][0]
        question["qualityState"] = "approved"
        question["reviewState"] = "approved"
        question["review"] = {"status": "human-reviewed", "approval": {"reviewedRecordId": question["id"], "reviewedContentVersion": question["contentVersion"], "status": "completed", "decision": "approved", "reviewer": "reviewer-1", "reviewedAt": "2026-08-23T12:00:00Z", "reason": "checked", "notes": "checked"}}
        question["evidenceMap"][0]["sourceRefs"][0]["location"] = 1
        source_mutated["course"]["contentPolicy"]["generatedQuestionsRequireHumanReviewForExam"] = True
        self.assertNotIn(question["id"], eligible_question_ids(source_mutated, "mock-exam"))
        self.assertIn("Evidence/source references: failed", build_reports(source_mutated)["quality"])

    def test_reports_fail_for_arabic_bijection_and_non_dict_question(self):
        mutated = copy.deepcopy(self.payloads)
        mutated["explanations-ar"]["explanations"][1] = copy.deepcopy(mutated["explanations-ar"]["explanations"][0])
        mutated["questions"]["questions"][2] = []
        reports = build_reports(mutated)
        self.assertIn("Arabic records: failed", reports["quality"])
        self.assertIn("Evidence/source references: failed", reports["quality"])
        self.assertTrue(measure_payloads(mutated)["errors"])

    def test_every_artifact_root_and_distribution_mutation_returns_errors(self):
        for name in self.payloads:
            mutated = copy.deepcopy(self.payloads)
            mutated[name] = []
            self.assertTrue(validate_payloads(mutated), name)
        mutated = copy.deepcopy(self.payloads)
        mutated["questions"]["questions"][0]["difficulty"] = "hard"
        self.assertTrue(any("difficulty distribution" in error.lower() for error in validate_payloads(mutated)))

    def test_every_acceptance_total_and_question_distribution_is_enforced(self):
        mutations = (
            ("course", "modules", "module total"),
            ("lessons", "lessons", "lesson total"),
            ("questions", "questions", "question total"),
            ("explanations-ar", "explanations", "arabic explanation total"),
        )
        for root, key, expected_error in mutations:
            mutated = copy.deepcopy(self.payloads)
            mutated[root][key].pop()
            self.assertTrue(any(expected_error in error.lower() for error in validate_payloads(mutated)), expected_error)
        for field, value, expected_error in (
            ("type", "true-false", "question type distribution"),
            ("bloomLevel", "analyze", "bloom distribution"),
        ):
            mutated = copy.deepcopy(self.payloads)
            mutated["questions"]["questions"][0][field] = value
            self.assertTrue(any(expected_error in error.lower() for error in validate_payloads(mutated)), expected_error)
        mutated = copy.deepcopy(self.payloads)
        true_false = next(question for question in mutated["questions"]["questions"] if question["type"] == "true-false")
        true_false["correctAnswer"] = not true_false["correctAnswer"]
        self.assertTrue(any("answer balance" in error.lower() for error in validate_payloads(mutated)))

    def test_standalone_checks_reject_malformed_config_and_source_inputs(self):
        config = json.loads((ROOT / "input" / "project-config.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / "content" / "source-manifest.json").read_text(encoding="utf-8"))
        extraction = json.loads((ROOT / "extraction" / "os-pages.json").read_text(encoding="utf-8"))
        malformed_config = copy.deepcopy(config)
        malformed_config["questionGeneration"]["difficultyPercent"] = {"easy": 101, "medium": -1, "hard": 0}
        errors, _, _ = _independent_checks(self.payloads, malformed_config, manifest, extraction)
        self.assertTrue(any("question generation" in error.lower() for error in errors))
        malformed_config = {"version": 1}
        errors, _, _ = _independent_checks(self.payloads, malformed_config, manifest, extraction)
        self.assertTrue(errors)
        duplicate_manifest = copy.deepcopy(manifest)
        duplicate_manifest["sources"].append(copy.deepcopy(duplicate_manifest["sources"][0]))
        errors, _, _ = _independent_checks(self.payloads, config, duplicate_manifest, extraction)
        self.assertTrue(any("duplicate source" in error.lower() for error in errors))
        malformed_manifest = copy.deepcopy(manifest)
        malformed_manifest["sources"][0]["pages"] = "twenty-nine"
        errors, _, _ = _independent_checks(self.payloads, config, malformed_manifest, extraction)
        self.assertTrue(any("malformed source" in error.lower() for error in errors))
        malformed_extraction_source = copy.deepcopy(extraction)
        malformed_extraction_source["sources"][0]["pages"] = "twenty-nine"
        errors, _, _ = _independent_checks(self.payloads, config, manifest, malformed_extraction_source)
        self.assertTrue(any("malformed source" in error.lower() for error in errors))
        malformed_extraction = copy.deepcopy(extraction)
        malformed_extraction["pages"][0] = []
        errors, _, _ = _independent_checks(self.payloads, config, manifest, malformed_extraction)
        self.assertTrue(any("malformed page" in error.lower() for error in errors))

    def test_reports_require_exact_arabic_generated_explanation_body_and_note(self):
        mutations = (
            ("generated explanation ID", lambda payloads: payloads["questions"]["questions"][0].__setitem__("generatedExplanationId", "explanation-wrong-ar")),
            ("body", lambda payloads: payloads["explanations-ar"]["explanations"][0].__setitem__("body", "")),
            ("note", lambda payloads: payloads["explanations-ar"]["explanations"][0].__setitem__("note", "")),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                mutated = copy.deepcopy(self.payloads)
                mutate(mutated)
                quality = build_reports(mutated)["quality"]
                self.assertIn("Arabic records: failed", quality)
                self.assertNotIn("Arabic records: complete", quality)

    def test_reports_count_non_object_questions_as_invalid_and_fail_retention_status(self):
        mutated = copy.deepcopy(self.payloads)
        mutated["questions"]["questions"][0] = []

        quality = build_reports(mutated)["quality"]

        self.assertIn("Questions: 210 (invalid 1, mcq 125, true-false 84).", quality)
        self.assertIn("Invalid question records: 1; retained and validated: failed.", quality)
        self.assertNotIn("all retained and validated", quality)
        self.assertIn("Evidence/source references: failed", quality)

    def test_standalone_config_accepts_exact_contract_with_one_generated_type_enabled(self):
        config = json.loads((ROOT / "input" / "project-config.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / "content" / "source-manifest.json").read_text(encoding="utf-8"))
        extraction = json.loads((ROOT / "extraction" / "os-pages.json").read_text(encoding="utf-8"))
        cases = (
            ("source-plus-generated", 6, 0),
            ("source-plus-generated", 0, 4),
            ("generated-only", 6, 0),
            ("generated-only", 0, 4),
            ("source-only", 0, 0),
        )
        for mode, mcq_count, true_false_count in cases:
            with self.subTest(mode=mode, mcq=mcq_count, true_false=true_false_count):
                compatible_config = copy.deepcopy(config)
                compatible_config["contentPolicy"]["mode"] = mode
                compatible_config["questionGeneration"]["mcqPerLesson"] = mcq_count
                compatible_config["questionGeneration"]["trueFalsePerLesson"] = true_false_count
                compatible_payloads = copy.deepcopy(self.payloads)
                compatible_payloads["course"]["contentPolicy"] = copy.deepcopy(compatible_config["contentPolicy"])
                compatible_payloads["course"]["questionGeneration"] = copy.deepcopy(compatible_config["questionGeneration"])

                errors, _, _ = _independent_checks(compatible_payloads, compatible_config, manifest, extraction)

                self.assertFalse(any("policy" in error.lower() or "question generation" in error.lower() for error in errors), errors)

    def test_standalone_config_rejects_mode_incompatible_counts_and_wrong_types(self):
        config = json.loads((ROOT / "input" / "project-config.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / "content" / "source-manifest.json").read_text(encoding="utf-8"))
        extraction = json.loads((ROOT / "extraction" / "os-pages.json").read_text(encoding="utf-8"))
        mutations = (
            ("generated types disabled", lambda value: value["questionGeneration"].update({"mcqPerLesson": 0, "trueFalsePerLesson": 0})),
            ("source-only generation enabled", lambda value: (value["contentPolicy"].__setitem__("mode", "source-only"), value["questionGeneration"].__setitem__("mcqPerLesson", 1))),
            ("Boolean count", lambda value: value["questionGeneration"].__setitem__("mcqPerLesson", False)),
            ("unexpected key", lambda value: value["questionGeneration"].__setitem__("extra", 1)),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                malformed = copy.deepcopy(config)
                mutate(malformed)
                errors, _, _ = _independent_checks(self.payloads, malformed, manifest, extraction)
                self.assertTrue(any("question generation" in error.lower() for error in errors), errors)

    def test_standalone_config_rejects_non_object_nested_records_without_crashing(self):
        config = json.loads((ROOT / "input" / "project-config.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / "content" / "source-manifest.json").read_text(encoding="utf-8"))
        extraction = json.loads((ROOT / "extraction" / "os-pages.json").read_text(encoding="utf-8"))
        expected_errors = {
            "project": "project metadata",
            "contentPolicy": "policy",
            "questionGeneration": "question generation",
            "exam": "exam",
            "deployment": "deployment",
        }
        for key, expected_error in expected_errors.items():
            with self.subTest(key=key):
                malformed = copy.deepcopy(config)
                malformed[key] = []

                errors, _, _ = _independent_checks(self.payloads, malformed, manifest, extraction)

                self.assertTrue(any(expected_error in error.lower() for error in errors), errors)

    def test_standalone_checks_reject_unhashable_manifest_and_extraction_ids_without_crashing(self):
        config = json.loads((ROOT / "input" / "project-config.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / "content" / "source-manifest.json").read_text(encoding="utf-8"))
        extraction = json.loads((ROOT / "extraction" / "os-pages.json").read_text(encoding="utf-8"))
        cases = (
            ("manifest", "malformed source", lambda man, ext: man["sources"][0].__setitem__("id", [])),
            ("extraction source", "malformed source", lambda man, ext: ext["sources"][0].__setitem__("id", {})),
            ("extraction page", "malformed page", lambda man, ext: ext["pages"][0].__setitem__("sourceId", [])),
        )
        for label, expected_error, mutate in cases:
            with self.subTest(label=label):
                malformed_manifest = copy.deepcopy(manifest)
                malformed_extraction = copy.deepcopy(extraction)
                mutate(malformed_manifest, malformed_extraction)

                errors, _, _ = _independent_checks(self.payloads, config, malformed_manifest, malformed_extraction)

                self.assertTrue(any(expected_error in error.lower() for error in errors), errors)

    def test_standalone_checks_enforce_all_source_page_and_classification_totals(self):
        config = json.loads((ROOT / "input" / "project-config.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / "content" / "source-manifest.json").read_text(encoding="utf-8"))
        extraction = json.loads((ROOT / "extraction" / "os-pages.json").read_text(encoding="utf-8"))

        short_manifest = copy.deepcopy(manifest)
        short_manifest["sources"].pop()
        errors, _, _ = _independent_checks(self.payloads, config, short_manifest, extraction)
        self.assertTrue(any("acceptance totals" in error.lower() for error in errors), errors)

        short_extraction = copy.deepcopy(extraction)
        short_extraction["pages"].pop()
        errors, _, total_pages = _independent_checks(self.payloads, config, manifest, short_extraction)
        self.assertEqual(516, total_pages)
        self.assertTrue(any("acceptance totals" in error.lower() for error in errors), errors)

        classification_mutations = (
            ("teaching", "cover"),
            ("cover", "teaching"),
            ("divider", "teaching"),
            ("closing", "teaching"),
            ("cover", "reference"),
        )
        for original, replacement in classification_mutations:
            with self.subTest(original=original, replacement=replacement):
                malformed_extraction = copy.deepcopy(extraction)
                page = next(item for item in malformed_extraction["pages"] if item["classification"] == original)
                page["classification"] = replacement

                errors, page_counts, _ = _independent_checks(self.payloads, config, manifest, malformed_extraction)

                self.assertNotEqual(Counter({"teaching": 454, "cover": 21, "divider": 21, "closing": 21}), page_counts)
                self.assertTrue(any("acceptance totals" in error.lower() for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
