import unittest

from scripts.validate_questions import build_artifacts, validate_question


class SourceKeyReviewTests(unittest.TestCase):
    def test_rejects_non_null_review_answers_without_visual_verification(self) -> None:
        question = {
            "id": "q-999",
            "type": "mcq",
            "prompt": "Prompt",
            "sources": [{"file": "source.pdf", "page": 1}],
            "needsReview": True,
            "reviewNotes": "Requires review.",
            "correctAnswer": 0,
        }

        self.assertIn(
            "review item may only retain a marked answer after visual verification",
            validate_question(question),
        )

    def test_preserves_visually_marked_answers_but_flags_contradictory_keys(self) -> None:
        payload, report = build_artifacts()
        questions = {question["id"]: question for question in payload["questions"]}
        expected_answers = {
            "q-015": {
                "item-1": "Local administrator",
                "item-2": "Local administrator",
            },
            "q-087": 3,
            "q-093": [True, True, False],
            "q-094": [1, 3],
        }

        for question_id, answer in expected_answers.items():
            with self.subTest(question_id=question_id):
                question = questions[question_id]
                self.assertTrue(question["needsReview"])
                self.assertEqual(question["correctAnswer"], answer)
                self.assertIn("marked answer", question["reviewNotes"].lower())

        self.assertIn("Questions requiring manual review: 5", report)
        self.assertIsNone(questions["q-103"]["correctAnswer"])

    def test_cleans_visible_prompt_structure_for_q015_and_q093(self) -> None:
        payload, _ = build_artifacts()
        questions = {question["id"]: question for question in payload["questions"]}

        self.assertEqual(
            questions["q-015"]["prompt"],
            "Your manager wants you to add a computer to the domain. You have already "
            "created the computer account in your Active Directory. To determine whether "
            "the computer can be added to the domain, you open the System Information "
            "window shown.",
        )
        self.assertEqual(
            questions["q-093"]["prompt"],
            "For each statement about facial recognition setup in Windows 10, select "
            "True or False. Note: You will receive partial credit for each correct selection.",
        )
        self.assertEqual(
            questions["q-093"]["statements"][0],
            "A Microsoft account is necessary to configure facial recognition for sign up",
        )


if __name__ == "__main__":
    unittest.main()
