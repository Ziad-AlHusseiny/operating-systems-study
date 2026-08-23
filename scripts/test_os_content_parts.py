import hashlib
import json
import re
import unittest
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTRACTION_PATH = ROOT / "extraction" / "os-pages.json"
MANIFEST_PATH = ROOT / "content" / "source-manifest.json"

PART_KEYS = {"version", "modules", "lessons", "questions", "explanations"}
MODULE_KEYS = {"id", "title", "order", "objectiveIds", "sourceRefs"}
LESSON_KEYS = {
    "id", "moduleId", "objectiveIds", "title", "contentVersion",
    "materialSectionIds", "learningObjectives", "materialSections",
    "needsReview", "reviewNotes", "review",
}
OBJECTIVE_KEYS = {"id", "moduleId", "text", "order", "sourceRefs"}
SECTION_KEYS = {
    "id", "order", "title", "origin", "label", "generatedStudyGuidance",
    "summary", "explanation", "body", "keyTerms", "workedExamples",
    "commonMistakes", "examTips", "recap", "sourceRefs",
    "linkedQuestionIds", "needsReview", "reviewNotes",
}
QUESTION_COMMON_KEYS = {
    "id", "origin", "type", "prompt", "topic", "correctAnswer", "rationale",
    "difficulty", "bloomLevel", "cognitiveLevel", "learningObjectiveId",
    "sourceRefs", "generationMethod", "generatedExplanationId", "provenance",
    "evidenceMap", "contentVersion", "qualityState", "reviewState",
    "duplicateComparison", "duplicateDisposition", "needsReview", "reviewNotes",
    "review",
}
EXPLANATION_KEYS = {
    "id", "questionId", "language", "generatedStudyGuidance", "translation",
    "explanation", "body", "note", "contentVersion", "sourceRefs",
    "needsReview", "reviewNotes", "review",
}
ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
EVIDENCE_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "by", "does",
    "for", "from", "in", "into", "is", "it", "its", "of", "on", "or",
    "that", "the", "their", "this", "to", "which", "while", "with",
}
SEMANTIC_STOP_WORDS = EVIDENCE_STOP_WORDS | {
    "answer", "correct", "described", "lecture", "option", "statement",
    "system", "what", "when",
}
VERIFIED_MCQ_ANSWER_KEY = {
    "gq-os-ch01-part1-001": 1,
    "gq-os-ch01-part1-002": 2,
    "gq-os-ch01-part1-003": 0,
    "gq-os-ch01-part1-004": 2,
    "gq-os-ch01-part1-005": 3,
    "gq-os-ch01-part1-006": 0,
    "gq-os-ch01-part2-001": 2,
    "gq-os-ch01-part2-002": 0,
    "gq-os-ch01-part2-003": 2,
    "gq-os-ch01-part2-004": 1,
    "gq-os-ch01-part2-005": 1,
    "gq-os-ch01-part2-006": 2,
    "gq-os-ch01-part3-001": 1,
    "gq-os-ch01-part3-002": 0,
    "gq-os-ch01-part3-003": 0,
    "gq-os-ch01-part3-004": 2,
    "gq-os-ch01-part3-005": 1,
    "gq-os-ch01-part3-006": 0,
    "gq-os-ch01-part4-001": 0,
    "gq-os-ch01-part4-002": 1,
    "gq-os-ch01-part4-003": 1,
    "gq-os-ch01-part4-004": 1,
    "gq-os-ch01-part4-005": 0,
    "gq-os-ch01-part4-006": 1,
    "gq-os-ch02-part1-001": 1,
    "gq-os-ch02-part1-002": 0,
    "gq-os-ch02-part1-003": 1,
    "gq-os-ch02-part1-004": 0,
    "gq-os-ch02-part1-005": 1,
    "gq-os-ch02-part1-006": 1,
    "gq-os-ch02-part2-001": 0,
    "gq-os-ch02-part2-002": 1,
    "gq-os-ch02-part2-003": 1,
    "gq-os-ch02-part2-004": 1,
    "gq-os-ch02-part2-005": 1,
    "gq-os-ch02-part2-006": 1,
    "gq-os-ch02-part3-001": 0,
    "gq-os-ch02-part3-002": 0,
    "gq-os-ch02-part3-003": 2,
    "gq-os-ch02-part3-004": 1,
    "gq-os-ch02-part3-005": 1,
    "gq-os-ch02-part3-006": 1,
    "gq-os-ch03-part1-001": 1,
    "gq-os-ch03-part1-002": 2,
    "gq-os-ch03-part1-003": 0,
    "gq-os-ch03-part1-004": 3,
    "gq-os-ch03-part1-005": 1,
    "gq-os-ch03-part1-006": 2,
    "gq-os-ch03-part2-001": 1,
    "gq-os-ch03-part2-002": 2,
    "gq-os-ch03-part2-003": 0,
    "gq-os-ch03-part2-004": 3,
    "gq-os-ch03-part2-005": 1,
    "gq-os-ch03-part2-006": 2,
    "gq-os-ch03-part3-001": 1,
    "gq-os-ch03-part3-002": 2,
    "gq-os-ch03-part3-003": 0,
    "gq-os-ch03-part3-004": 3,
    "gq-os-ch03-part3-005": 1,
    "gq-os-ch03-part3-006": 2,
    "gq-os-ch05-part1-001": 1,
    "gq-os-ch05-part1-002": 2,
    "gq-os-ch05-part1-003": 0,
    "gq-os-ch05-part1-004": 3,
    "gq-os-ch05-part1-005": 1,
    "gq-os-ch05-part1-006": 2,
    "gq-os-ch05-part2-001": 2,
    "gq-os-ch05-part2-002": 0,
    "gq-os-ch05-part2-003": 3,
    "gq-os-ch05-part2-004": 1,
    "gq-os-ch05-part2-005": 2,
    "gq-os-ch05-part2-006": 3,
    "gq-os-ch05-part3-001": 1,
    "gq-os-ch05-part3-002": 2,
    "gq-os-ch05-part3-003": 0,
    "gq-os-ch05-part3-004": 3,
    "gq-os-ch05-part3-005": 1,
    "gq-os-ch05-part3-006": 2,
    "gq-os-ch05-part4-001": 1,
    "gq-os-ch05-part4-002": 2,
    "gq-os-ch05-part4-003": 0,
    "gq-os-ch05-part4-004": 3,
    "gq-os-ch05-part4-005": 1,
    "gq-os-ch05-part4-006": 2,
}


class OSContentPartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extraction = json.loads(EXTRACTION_PATH.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def load_part(self, relative_path):
        return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))

    def existing_parts(self):
        content_dir = ROOT / "content" / "os"
        if not content_dir.exists():
            return []
        return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(content_dir.glob("*.json"))]

    def combined_part(self):
        parts = self.existing_parts()
        return {
            "version": "1.0",
            "modules": [item for part in parts for item in part["modules"]],
            "lessons": [item for part in parts for item in part["lessons"]],
            "questions": [item for part in parts for item in part["questions"]],
            "explanations": [item for part in parts for item in part["explanations"]],
        }

    def assert_all_teaching_pages_covered(self, part, source_ids):
        expected = {
            (page["sourceId"], page["page"])
            for page in self.extraction["pages"]
            if page["sourceId"] in source_ids and page["classification"] == "teaching"
        }
        actual = {
            (ref["sourceId"], ref["location"])
            for lesson in part["lessons"]
            for section in lesson["materialSections"]
            for ref in section["sourceRefs"]
            if ref["sourceId"] in source_ids and ref["locationType"] == "page"
        }
        self.assertEqual(actual, expected)

    def iter_source_refs(self, value):
        if isinstance(value, dict):
            if {"sourceId", "locationType", "location"}.issubset(value):
                yield value
            for child in value.values():
                yield from self.iter_source_refs(child)
        elif isinstance(value, list):
            for child in value:
                yield from self.iter_source_refs(child)

    def normalized_prompt(self, value):
        value = unicodedata.normalize("NFKC", value).strip().casefold()
        value = "".join(character if not unicodedata.category(character).startswith("P") else " " for character in value)
        return re.sub(r"\s+", " ", value).strip()

    def questions_for_lesson(self, part, lesson_id):
        prefix = lesson_id.replace("lesson-", "gq-") + "-"
        return [question for question in part["questions"] if question["id"].startswith(prefix)]

    def content_tokens(self, value, stop_words):
        tokens = set()
        for token in re.findall(r"[a-z0-9]+", value.casefold()):
            if (len(token) > 1 or token.isdigit()) and token not in stop_words:
                if len(token) > 4 and token.endswith("ies"):
                    token = token[:-3] + "y"
                elif len(token) > 3 and token.endswith("s"):
                    token = token[:-1]
                tokens.add(token)
        return tokens

    def proposition_tokens(self, question):
        value = question["prompt"] + " " + question["rationale"]
        if question["type"] == "mcq":
            value += " " + question["options"][question["correctAnswer"]]
        elif question["correctedStatement"]:
            value += " " + question["correctedStatement"]
        return self.content_tokens(value, SEMANTIC_STOP_WORDS)

    def test_chapters_one_and_two_have_seven_traceable_lessons(self):
        part = self.load_part("content/os/ch01-ch02.json")
        self.assertEqual([module["id"] for module in part["modules"]], ["module-os-ch01", "module-os-ch02"])
        expected_lessons = [
            ("lesson-os-ch01-part1", "os-lec-01"),
            ("lesson-os-ch01-part2", "os-lec-02"),
            ("lesson-os-ch01-part3", "os-lec-03"),
            ("lesson-os-ch01-part4", "os-lec-04"),
            ("lesson-os-ch02-part1", "os-lec-05"),
            ("lesson-os-ch02-part2", "os-lec-06"),
            ("lesson-os-ch02-part3", "os-lec-07"),
        ]
        self.assertEqual([lesson["id"] for lesson in part["lessons"]], [item[0] for item in expected_lessons])
        for lesson, (_, source_id) in zip(part["lessons"], expected_lessons):
            lesson_source_ids = {
                source_ref["sourceId"]
                for source_ref in self.iter_source_refs(lesson)
            }
            self.assertEqual(lesson_source_ids, {source_id})
        self.assert_all_teaching_pages_covered(part, {f"os-lec-{n:02d}" for n in range(1, 8)})

    def test_chapters_three_and_five_have_seven_traceable_lessons(self):
        part = self.load_part("content/os/ch03-ch05.json")
        self.assertEqual([module["id"] for module in part["modules"]], ["module-os-ch03", "module-os-ch05"])
        self.assertEqual([module["order"] for module in part["modules"]], [3, 4])
        self.assertEqual(len(part["lessons"]), 7)
        self.assert_all_teaching_pages_covered(part, {f"os-lec-{n:02d}" for n in range(8, 15)})

    def test_every_generated_question_has_separate_arabic_guidance(self):
        part = self.combined_part()
        explanations = {item["questionId"]: item for item in part["explanations"]}
        self.assertEqual(len(part["questions"]), 140)
        for question in part["questions"]:
            self.assertEqual(question["origin"], "generated")
            self.assertIn(question["id"], explanations)
            self.assertIn(len(explanations[question["id"]]["explanation"]), (2, 3))

    def test_part_and_authoring_records_use_exact_canonical_shapes(self):
        part = self.combined_part()
        self.assertEqual(set(part), PART_KEYS)
        self.assertEqual(part["version"], "1.0")
        for module in part["modules"]:
            self.assertEqual(set(module), MODULE_KEYS)
            self.assertTrue(module["id"].startswith("module-"))
        for lesson in part["lessons"]:
            self.assertEqual(set(lesson), LESSON_KEYS)
            self.assertTrue(lesson["id"].startswith("lesson-"))
            self.assertEqual(lesson["contentVersion"], "1.0.0")
            self.assertEqual(lesson["materialSectionIds"], [section["id"] for section in lesson["materialSections"]])
            self.assertEqual(lesson["objectiveIds"], [objective["id"] for objective in lesson["learningObjectives"]])
            for objective in lesson["learningObjectives"]:
                self.assertEqual(set(objective), OBJECTIVE_KEYS)
                self.assertTrue(objective["id"].startswith("objective-"))
                self.assertEqual(objective["moduleId"], lesson["moduleId"])
                self.assertGreaterEqual(len(objective["sourceRefs"]), 1)
            self.assertGreaterEqual(len(lesson["learningObjectives"]), 3)
            origins = set()
            for expected_order, section in enumerate(lesson["materialSections"], 1):
                self.assertEqual(set(section), SECTION_KEYS)
                self.assertTrue(section["id"].startswith("material-section-"))
                self.assertEqual(section["order"], expected_order)
                origins.add(section["origin"])
                expected_label = "Source material" if section["origin"] == "source" else "Generated study guidance"
                self.assertEqual(section["label"], expected_label)
                self.assertEqual(section["generatedStudyGuidance"], section["origin"] == "generated")
                self.assertIn(len(section["explanation"]), range(2, 6))
                self.assertEqual(section["body"], "\n\n".join(section["explanation"]))
                self.assertIn(len(section["recap"]), range(3, 8))
                self.assertGreaterEqual(len(section["sourceRefs"]), 1)
                for item in section["keyTerms"]:
                    self.assertEqual(set(item), {"term", "definition", "sourceRefs"})
                    self.assertTrue(item["sourceRefs"])
                for item in section["workedExamples"]:
                    self.assertEqual(set(item), {"title", "body", "sourceRefs"})
                    self.assertTrue(item["sourceRefs"])
                for item in section["commonMistakes"]:
                    self.assertEqual(set(item), {"misconception", "correction", "sourceRefs"})
                    self.assertTrue(item["sourceRefs"])
                for item in section["examTips"]:
                    self.assertEqual(set(item), {"body", "sourceRefs"})
                    self.assertTrue(item["sourceRefs"])
            self.assertEqual(origins, {"source", "generated"})
            for field in ("keyTerms", "workedExamples", "commonMistakes", "examTips"):
                self.assertTrue(any(section[field] for section in lesson["materialSections"]), f"{lesson['id']} lacks {field}")

    def test_source_references_resolve_within_teaching_page_bounds(self):
        part = self.combined_part()
        sources = {source["id"]: source for source in self.manifest["sources"]}
        classifications = {
            (page["sourceId"], page["page"]): page["classification"]
            for page in self.extraction["pages"]
        }
        all_refs = list(self.iter_source_refs(part))
        self.assertTrue(all_refs)
        for source_ref in all_refs:
            self.assertEqual(set(source_ref), {"sourceId", "locationType", "location"})
            self.assertIn(source_ref["sourceId"], sources)
            self.assertEqual(source_ref["locationType"], "page")
            self.assertIn(source_ref["location"], range(1, sources[source_ref["sourceId"]]["pages"] + 1))
            self.assertEqual(classifications[(source_ref["sourceId"], source_ref["location"])], "teaching")

    def test_module_objectives_and_lesson_question_links_resolve_in_order(self):
        part = self.combined_part()
        question_ids = {question["id"] for question in part["questions"]}
        for module in part["modules"]:
            module_lessons = [lesson for lesson in part["lessons"] if lesson["moduleId"] == module["id"]]
            expected_objectives = [objective["id"] for lesson in module_lessons for objective in lesson["learningObjectives"]]
            self.assertEqual(module["objectiveIds"], expected_objectives)
            orders = [objective["order"] for lesson in module_lessons for objective in lesson["learningObjectives"]]
            self.assertEqual(orders, list(range(1, len(orders) + 1)))
        for lesson in part["lessons"]:
            owned_question_ids = {question["id"] for question in self.questions_for_lesson(part, lesson["id"])}
            self.assertEqual(len(owned_question_ids), 10)
            for section in lesson["materialSections"]:
                self.assertEqual(len(section["linkedQuestionIds"]), len(set(section["linkedQuestionIds"])))
                self.assertTrue(set(section["linkedQuestionIds"]).issubset(owned_question_ids))
                self.assertTrue(set(section["linkedQuestionIds"]).issubset(question_ids))
            self.assertEqual(
                {question_id for section in lesson["materialSections"] for question_id in section["linkedQuestionIds"]},
                owned_question_ids,
            )

    def test_question_counts_quotas_and_deterministic_true_false_patterns(self):
        part = self.combined_part()
        self.assertEqual(Counter(question["type"] for question in part["questions"]), {"mcq": 84, "true-false": 56})
        patterns = ["TTFF", "TFTF", "TFFT", "FTTF", "FTFT", "FFTT"]
        true_false_answers = []
        for lesson in part["lessons"]:
            questions = self.questions_for_lesson(part, lesson["id"])
            expected_ids = [lesson["id"].replace("lesson-", "gq-") + f"-{number:03d}" for number in range(1, 11)]
            self.assertEqual([question["id"] for question in questions], expected_ids)
            self.assertEqual(Counter(question["type"] for question in questions), {"mcq": 6, "true-false": 4})
            self.assertEqual(Counter(question["difficulty"] for question in questions), {"easy": 3, "medium": 5, "hard": 2})
            self.assertEqual(Counter(question["bloomLevel"] for question in questions), {"remember": 3, "apply": 5, "analyze": 2})
            self.assertTrue(all(question["bloomLevel"] == question["cognitiveLevel"] for question in questions))
            true_false = sorted((question for question in questions if question["type"] == "true-false"), key=lambda item: item["id"])
            digest = hashlib.sha256(f"operating-systems-study\n{lesson['id']}".encode("utf-8")).hexdigest()
            expected_pattern = patterns[int(digest[:8], 16) % len(patterns)]
            actual_pattern = "".join("T" if question["correctAnswer"] else "F" for question in true_false)
            self.assertEqual(actual_pattern, expected_pattern)
            true_false_answers.extend(question["correctAnswer"] for question in true_false)
        self.assertEqual(Counter(true_false_answers), {True: 28, False: 28})

    def test_generated_questions_use_exact_answer_evidence_and_provenance_shapes(self):
        part = self.combined_part()
        lesson_objectives = {
            lesson["id"]: set(lesson["objectiveIds"])
            for lesson in part["lessons"]
        }
        for question in part["questions"]:
            lesson_id = "lesson-" + question["id"].removeprefix("gq-").rsplit("-", 1)[0]
            self.assertIn(question["learningObjectiveId"], lesson_objectives[lesson_id])
            self.assertEqual(question["origin"], "generated")
            self.assertEqual(question["generationMethod"], "source-grounded-authoring-v1")
            self.assertEqual(question["contentVersion"], "1.0.0")
            self.assertEqual(set(question["provenance"]), {"sourceRefs", "modelVersion", "promptVersion"})
            self.assertEqual(question["provenance"]["sourceRefs"], question["sourceRefs"])
            self.assertTrue(question["provenance"]["modelVersion"])
            self.assertEqual(question["provenance"]["promptVersion"], "os-question-generation-1.0")
            self.assertEqual(set(question["duplicateComparison"]), {"algorithmVersion", "normalizedPrompt", "candidateIds", "matchClass"})
            self.assertEqual(question["duplicateComparison"]["normalizedPrompt"], self.normalized_prompt(question["prompt"]))
            self.assertEqual(question["duplicateComparison"]["candidateIds"], [])
            self.assertEqual(question["duplicateComparison"]["matchClass"], "none")
            if question["type"] == "mcq":
                self.assertEqual(set(question), QUESTION_COMMON_KEYS | {"options", "distractorRationales"})
                self.assertEqual(len(question["options"]), 4)
                self.assertEqual(len(set(question["options"])), 4)
                self.assertEqual(len(question["distractorRationales"]), 4)
                self.assertIs(type(question["correctAnswer"]), int)
                self.assertIn(question["correctAnswer"], range(4))
                expected_targets = {"prompt", "correctAnswer", "rationale"}
                expected_targets |= {f"options[{index}]" for index in range(4)}
                expected_targets |= {f"distractorRationales[{index}]" for index in range(4)}
            else:
                self.assertEqual(set(question), QUESTION_COMMON_KEYS | {"correctedStatement"})
                self.assertIs(type(question["correctAnswer"]), bool)
                self.assertNotIn("options", question)
                self.assertNotIn("distractorRationales", question)
                if question["correctAnswer"]:
                    self.assertIsNone(question["correctedStatement"])
                else:
                    self.assertIsInstance(question["correctedStatement"], str)
                    self.assertTrue(question["correctedStatement"].strip())
                expected_targets = {"prompt", "correctAnswer", "rationale"}
                if question["correctedStatement"] is not None:
                    expected_targets.add("correctedStatement")
            self.assertEqual([item["target"] for item in question["evidenceMap"]], list(dict.fromkeys(item["target"] for item in question["evidenceMap"])))
            self.assertEqual({item["target"] for item in question["evidenceMap"]}, expected_targets)
            for claim in question["evidenceMap"]:
                self.assertEqual(set(claim), {"claimId", "target", "sourceRefs", "support"})
                self.assertTrue(claim["claimId"])
                self.assertTrue(claim["sourceRefs"])
                self.assertIn(claim["support"], {"direct", "derived"})

    def test_mcq_options_have_precise_source_grounded_evidence(self):
        part = self.combined_part()
        page_text = {
            (page["sourceId"], page["page"]): page["text"]
            for page in self.extraction["pages"]
        }
        uniform_option_evidence = Counter()
        direct_option_claims = Counter()
        option_claims = Counter()
        for question in (item for item in part["questions"] if item["type"] == "mcq"):
            part_name = "ch01-ch02" if question["id"].startswith(("gq-os-ch01-", "gq-os-ch02-")) else "ch03-ch05"
            evidence = {item["target"]: item for item in question["evidenceMap"]}
            signatures = []
            for index, option in enumerate(question["options"]):
                option_claim = evidence[f"options[{index}]"]
                rationale_claim = evidence[f"distractorRationales[{index}]"]
                signatures.append((
                    tuple((ref["sourceId"], ref["location"]) for ref in option_claim["sourceRefs"]),
                    option_claim["support"],
                ))
                source_text = " ".join(
                    page_text[(ref["sourceId"], ref["location"])]
                    for ref in option_claim["sourceRefs"]
                )
                option_tokens = self.content_tokens(option, EVIDENCE_STOP_WORDS)
                source_tokens = self.content_tokens(source_text, EVIDENCE_STOP_WORDS)
                self.assertTrue(
                    option_tokens & source_tokens,
                    f"{question['id']} option {index} has no lexical grounding in its cited pages",
                )
                self.assertLessEqual(len(option_claim["sourceRefs"]), 2)
                self.assertEqual(rationale_claim["sourceRefs"], option_claim["sourceRefs"])
                self.assertEqual(rationale_claim["support"], "derived")
                option_claims[part_name] += 1
                direct_option_claims[part_name] += option_claim["support"] == "direct"
            uniform_option_evidence[part_name] += len(set(signatures)) == 1
        for part_name in ("ch01-ch02", "ch03-ch05"):
            self.assertLessEqual(uniform_option_evidence[part_name], 8)
            self.assertLess(direct_option_claims[part_name], option_claims[part_name])

    def test_mcq_answer_indexes_match_the_manually_verified_source_oracle(self):
        part = self.combined_part()
        actual = {
            question["id"]: question["correctAnswer"]
            for question in part["questions"]
            if question["type"] == "mcq"
        }
        self.assertEqual(set(actual), set(VERIFIED_MCQ_ANSWER_KEY))
        for question_id, expected_answer in VERIFIED_MCQ_ANSWER_KEY.items():
            self.assertEqual(
                actual[question_id],
                expected_answer,
                f"{question_id} answer index drifted from the source-verified oracle",
            )

    def test_analyze_items_require_multistep_reasoning_signals(self):
        part = self.combined_part()
        analyze_items = [question for question in part["questions"] if question["bloomLevel"] == "analyze"]
        self.assertEqual(len(analyze_items), 28)
        reasoning_signal = re.compile(
            r"\b(after|although|before|because|compared|despite|diagnos|fails?|observes?|rather than|sequence|trade-off|when|while)\b",
            re.IGNORECASE,
        )
        for question in analyze_items:
            self.assertGreaterEqual(len(question["prompt"].split()), 18, question["id"])
            self.assertRegex(question["prompt"], reasoning_signal, question["id"])
            self.assertGreaterEqual(len(self.proposition_tokens(question)), 10, question["id"])

    def test_validated_questions_do_not_repeat_semantic_propositions(self):
        part = self.combined_part()
        known_pairs = {
            frozenset(("gq-os-ch01-part1-002", "gq-os-ch01-part1-007")),
            frozenset(("gq-os-ch01-part1-004", "gq-os-ch01-part1-009")),
            frozenset(("gq-os-ch01-part3-002", "gq-os-ch01-part3-005")),
            frozenset(("gq-os-ch02-part1-005", "gq-os-ch02-part1-010")),
            frozenset(("gq-os-ch02-part1-006", "gq-os-ch02-part1-009")),
            frozenset(("gq-os-ch02-part2-006", "gq-os-ch02-part2-008")),
            frozenset(("gq-os-ch02-part3-001", "gq-os-ch02-part3-007")),
            frozenset(("gq-os-ch02-part3-005", "gq-os-ch02-part3-009")),
        }
        observed_pairs = set()
        for lesson in part["lessons"]:
            questions = self.questions_for_lesson(part, lesson["id"])
            for left_index, left in enumerate(questions):
                for right in questions[left_index + 1:]:
                    left_tokens = self.proposition_tokens(left)
                    right_tokens = self.proposition_tokens(right)
                    overlap = len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))
                    pair = frozenset((left["id"], right["id"]))
                    if pair in known_pairs:
                        observed_pairs.add(pair)
                        self.assertLess(overlap, 0.35, f"known semantic overlap remains: {sorted(pair)}")
                    self.assertLess(overlap, 0.42, f"semantic near-duplicate remains: {left['id']} / {right['id']}")
        self.assertEqual(observed_pairs, known_pairs)
        for question in part["questions"]:
            self.assertEqual(question["duplicateComparison"]["candidateIds"], [])
            self.assertEqual(question["duplicateComparison"]["matchClass"], "none")

    def test_prompts_are_unique_and_validated_review_states_are_consistent(self):
        part = self.combined_part()
        normalized = [question["duplicateComparison"]["normalizedPrompt"] for question in part["questions"]]
        self.assertEqual(len(normalized), len(set(normalized)))
        for lesson in part["lessons"]:
            self.assertFalse(lesson["needsReview"])
            self.assertEqual(lesson["reviewNotes"], "")
            self.assertEqual(lesson["review"], {"status": "validated"})
            for section in lesson["materialSections"]:
                self.assertFalse(section["needsReview"])
                self.assertEqual(section["reviewNotes"], "")
        for question in part["questions"]:
            self.assertEqual(question["qualityState"], "validated")
            self.assertEqual(question["reviewState"], "unreviewed")
            self.assertEqual(question["duplicateDisposition"], "retain")
            self.assertFalse(question["needsReview"])
            self.assertEqual(question["reviewNotes"], "")
            self.assertEqual(question["review"], {"status": "validated"})
            self.assertNotIn("approval", question["review"])

    def test_arabic_explanations_use_exact_shape_and_match_questions(self):
        part = self.combined_part()
        questions = {question["id"]: question for question in part["questions"]}
        self.assertEqual(len(part["explanations"]), 140)
        self.assertEqual(len({item["id"] for item in part["explanations"]}), 140)
        for item in part["explanations"]:
            self.assertEqual(set(item), EXPLANATION_KEYS)
            self.assertEqual(item["id"], f"explanation-{item['questionId']}-ar")
            self.assertEqual(questions[item["questionId"]]["generatedExplanationId"], item["id"])
            self.assertEqual(item["language"], "ar")
            self.assertTrue(item["generatedStudyGuidance"])
            self.assertTrue(ARABIC_RE.search(item["translation"]))
            self.assertIn(len(item["explanation"]), (2, 3))
            self.assertTrue(all(ARABIC_RE.search(paragraph) for paragraph in item["explanation"]))
            self.assertTrue(item["body"].strip())
            self.assertIn("مراجعة مولدة", item["note"])
            self.assertIn("الامتحان", item["note"])
            self.assertEqual(item["contentVersion"], "1.0.0")
            self.assertEqual(item["sourceRefs"], questions[item["questionId"]]["sourceRefs"])
            self.assertFalse(item["needsReview"])
            self.assertEqual(item["reviewNotes"], "")
            self.assertEqual(item["review"], {"status": "validated"})

    def test_new_arabic_explanation_bodies_exactly_join_their_paragraphs(self):
        part = self.load_part("content/os/ch03-ch05.json")
        self.assertEqual(len(part["explanations"]), 70)
        for explanation in part["explanations"]:
            self.assertEqual(explanation["body"], "\n\n".join(explanation["explanation"]))

    def test_cross_part_ids_and_semantic_propositions_are_unique(self):
        parts = self.existing_parts()
        combined = self.combined_part()
        id_groups = [
            combined["modules"],
            combined["lessons"],
            [objective for lesson in combined["lessons"] for objective in lesson["learningObjectives"]],
            [section for lesson in combined["lessons"] for section in lesson["materialSections"]],
            combined["questions"],
            combined["explanations"],
        ]
        for records in id_groups:
            ids = [record["id"] for record in records]
            self.assertEqual(len(ids), len(set(ids)))

        semantic_signatures = []
        for question in combined["questions"]:
            answer = (
                question["options"][question["correctAnswer"]]
                if question["type"] == "mcq"
                else question["correctedStatement"] or str(question["correctAnswer"])
            )
            semantic_signatures.append(self.normalized_prompt(
                " ".join((question["prompt"], question["rationale"], answer))
            ))
        self.assertEqual(len(semantic_signatures), len(set(semantic_signatures)))

        old_questions = parts[0]["questions"]
        new_questions = parts[1]["questions"]
        for old_question in old_questions:
            old_tokens = self.proposition_tokens(old_question)
            for new_question in new_questions:
                new_tokens = self.proposition_tokens(new_question)
                overlap = len(old_tokens & new_tokens) / min(len(old_tokens), len(new_tokens))
                self.assertLess(overlap, 0.58, f"cross-part semantic near-duplicate: {old_question['id']} / {new_question['id']}")

    def test_generated_guidance_is_arabic_and_prohibited_official_claims_are_absent(self):
        part = self.combined_part()
        for lesson in part["lessons"]:
            for section in lesson["materialSections"]:
                if section["origin"] == "generated":
                    self.assertTrue(ARABIC_RE.search(section["summary"]))
                    self.assertTrue(all(ARABIC_RE.search(paragraph) for paragraph in section["explanation"]))
        serialized = json.dumps(part, ensure_ascii=False).casefold()
        for prohibited in ("official exam question", "official question", "from the exam", "past-paper question", "certified", "guaranteed to appear"):
            self.assertNotIn(prohibited, serialized)


if __name__ == "__main__":
    unittest.main()
