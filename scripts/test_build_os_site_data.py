"""Regression tests for deterministic Operating Systems public payloads."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.build_os_site_data import (
    ROOT,
    build_payloads,
    build_reports,
    eligible_question_ids,
    load_content_parts,
    payload_bytes,
    validate_payloads,
    write_artifacts,
)


class BuildOperatingSystemsSiteDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payloads = build_payloads(load_content_parts())

    def test_build_combines_all_canonical_records(self):
        self.assertEqual(7, len(self.payloads["course"]["modules"]))
        self.assertEqual(21, len(self.payloads["lessons"]["lessons"]))
        self.assertEqual(210, len(self.payloads["questions"]["questions"]))
        self.assertEqual(210, len(self.payloads["explanations-ar"]["explanations"]))

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


if __name__ == "__main__":
    unittest.main()
