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

Keys must be within the assigned range for the part file. `translation`, every
`explanation` paragraph, and `note` must contain Arabic text. `explanation`
must contain exactly two or three paragraphs.

`q-103` must remain unresolved: explain the source conflict without choosing an
answer as correct.
