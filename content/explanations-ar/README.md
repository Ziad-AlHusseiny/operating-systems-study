# Arabic explanation authoring schema

Each part file is a UTF-8 JSON object keyed by canonical question ID. Every
entry must use this shape:

```json
{
  "q-001": {
    "translation": "ترجمة عربية كاملة للسؤال والعناصر المؤثرة في الإجابة.",
    "explanation": [
      "فقرة قصيرة تشرح الفكرة الأساسية بلغة واضحة.",
      "فقرة قصيرة تربط الفكرة بالإجابة الرسمية وتوضح سبب صحتها."
    ],
    "note": "ملاحظة مراجعة قصيرة وسهلة التذكر."
  }
}
```

Every entry must be an object with exactly the `translation`, `explanation`,
and `note` fields. Keys must be within the assigned range named by the part
file. `translation`, every `explanation` paragraph, and `note` must be
non-empty strings containing Arabic text. `explanation` must contain exactly
two or three paragraphs.

`q-103` must remain unresolved: mention the source conflict, `Differential`,
and `Incremental` without using an answer-selection phrase.
