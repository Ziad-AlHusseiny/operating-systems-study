import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_explanations import build_payload, validate_entry


VALID_ENTRY = {
    "translation": "ترجمة عربية واضحة.",
    "explanation": [
        "فقرة عربية أولى تشرح الفكرة.",
        "فقرة عربية ثانية تربطها بالمراجعة.",
    ],
    "note": "ملاحظة عربية قصيرة.",
}


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


class ValidateEntryTests(unittest.TestCase):
    def test_rejects_non_object_entries(self) -> None:
        self.assertEqual(
            validate_entry("q-001", []),
            ["q-001: entry must be an object"],
        )

    def test_requires_exact_fields(self) -> None:
        missing = dict(VALID_ENTRY)
        missing.pop("note")
        extra = {**VALID_ENTRY, "answer": "غير مسموح"}

        self.assertIn(
            "q-001: fields must be exactly translation, explanation, note",
            validate_entry("q-001", missing),
        )
        self.assertIn(
            "q-001: fields must be exactly translation, explanation, note",
            validate_entry("q-001", extra),
        )

    def test_requires_non_empty_arabic_strings(self) -> None:
        cases = [
            ({**VALID_ENTRY, "translation": ""}, "translation"),
            ({**VALID_ENTRY, "translation": "English only"}, "translation"),
            ({**VALID_ENTRY, "note": "   "}, "note"),
            ({**VALID_ENTRY, "note": "English only"}, "note"),
            (
                {**VALID_ENTRY, "explanation": ["فقرة عربية", ""]},
                "every explanation paragraph",
            ),
            (
                {**VALID_ENTRY, "explanation": ["فقرة عربية", "English only"]},
                "every explanation paragraph",
            ),
        ]

        for entry, message_fragment in cases:
            with self.subTest(entry=entry, message=message_fragment):
                self.assertTrue(
                    any(message_fragment in error for error in validate_entry("q-001", entry))
                )

    def test_requires_two_or_three_paragraphs(self) -> None:
        for paragraphs in ([], ["واحد"], ["واحد", "اثنان", "ثلاثة", "أربعة"]):
            with self.subTest(paragraphs=paragraphs):
                self.assertIn(
                    "q-001: explanation must have 2 or 3 paragraphs",
                    validate_entry("q-001", {**VALID_ENTRY, "explanation": paragraphs}),
                )

    def test_q103_must_describe_the_unresolved_conflict(self) -> None:
        valid = {
            **VALID_ENTRY,
            "translation": "يوجد تعارض بين المصدرين.",
            "explanation": [
                "يذكر المصدر الأول Differential.",
                "بينما يذكر المصدر الثاني Incremental.",
            ],
        }
        invalid_entries = [
            {**valid, "translation": "يوجد مصدران للمراجعة."},
            {**valid, "explanation": ["يذكر المصدر الأول.", valid["explanation"][1]]},
            {**valid, "explanation": [valid["explanation"][0], "يذكر المصدر الثاني."]},
            {**valid, "note": "الإجابة الصحيحة هي Differential."},
            {**valid, "explanation": 42},
        ]

        self.assertEqual(validate_entry("q-103", valid), [])
        for entry in invalid_entries:
            with self.subTest(entry=entry):
                self.assertTrue(
                    any("q-103 must" in error for error in validate_entry("q-103", entry))
                )

    def test_q103_requires_standalone_technical_terms(self) -> None:
        entries = [
            {
                **VALID_ENTRY,
                "translation": "يوجد تعارض بين المصدرين.",
                "explanation": [
                    "يستخدم النص كلمة nondifferential فقط.",
                    "ويذكر المصدر الآخر Incremental.",
                ],
            },
            {
                **VALID_ENTRY,
                "translation": "يوجد اختلاف بين المصدرين.",
                "explanation": [
                    "يذكر المصدر الأول Differential.",
                    "ويستخدم المصدر الآخر كلمة incrementally فقط.",
                ],
            },
        ]

        for entry in entries:
            with self.subTest(entry=entry):
                self.assertIn(
                    "q-103 must mention both Differential and Incremental",
                    validate_entry("q-103", entry),
                )

    def test_q103_rejects_explicit_answer_selection_patterns(self) -> None:
        selections = [
            "الإجابة الصحيحة: Differential",
            "الإجابة: Incremental",
            "الخيار الصحيح هو Differential",
            "Answer: Differential",
            "the answer is Incremental",
            "correct answer Differential",
        ]
        base = {
            **VALID_ENTRY,
            "translation": "يوجد تعارض بين المصدرين.",
            "explanation": [
                "يذكر المصدر الأول Differential.",
                "ويذكر المصدر الثاني Incremental.",
            ],
        }

        for selection in selections:
            with self.subTest(selection=selection):
                entry = {**base, "note": f"ملاحظة للمراجعة: {selection}."}
                self.assertIn(
                    "q-103 must not select an answer",
                    validate_entry("q-103", entry),
                )

    def test_q103_accepts_neutral_conflict_text(self) -> None:
        entry = {
            **VALID_ENTRY,
            "translation": "يوجد تعارض غير محسوم بين المصدرين.",
            "explanation": [
                "المصدر الأول يذكر Differential دون ترجيح.",
                "المصدر الثاني يذكر Incremental وتبقى المسألة للمراجعة.",
            ],
        }

        self.assertEqual(validate_entry("q-103", entry), [])


class BuildPayloadTests(unittest.TestCase):
    def test_rejects_ids_outside_the_part_filename_range(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            questions_path = root / "questions.json"
            part_path = root / "q001-026.json"
            write_json(questions_path, {"questions": [{"id": "q-027"}]})
            write_json(part_path, {"q-027": VALID_ENTRY})

            with self.assertRaisesRegex(
                ValueError,
                r"q-027: ID is outside assigned range q-001\.\.q-026 for q001-026\.json",
            ):
                build_payload(questions_path, [part_path])

    def test_sorts_explanations_independently_of_input_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            questions_path = root / "questions.json"
            first_part = root / "q001-026.json"
            second_part = root / "q027-052.json"
            write_json(
                questions_path,
                {"questions": [{"id": "q-027"}, {"id": "q-001"}]},
            )
            write_json(first_part, {"q-001": VALID_ENTRY})
            write_json(second_part, {"q-027": VALID_ENTRY})

            payload = build_payload(questions_path, [second_part, first_part])

            self.assertEqual(list(payload["explanations"]), ["q-001", "q-027"])


if __name__ == "__main__":
    unittest.main()
