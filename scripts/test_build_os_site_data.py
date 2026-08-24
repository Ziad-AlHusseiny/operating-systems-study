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


if __name__ == "__main__":
    unittest.main()
