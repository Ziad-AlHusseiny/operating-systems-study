# Arabic Question Explanations Design

## Goal

Add a professional study section that translates and explains every canonical question in clear Arabic while keeping the original English question and official PDF answer visible.

## Scope

- Cover all 103 canonical questions in `study-website/data/questions.json`.
- Give every question an Arabic translation, a medium-length Arabic explanation, and a short revision note.
- Keep the official question data unchanged and store educational content separately.
- Add a dedicated explanation page and connect explanations to Practice feedback and Exam Review.
- Preserve the existing plain HTML, CSS, vanilla JavaScript, JSON, and LocalStorage architecture.
- Publish the completed update through the existing GitHub Pages workflow.

## Content Model

Create `study-website/data/explanations-ar.json` with one entry per canonical question ID:

```json
{
  "version": 1,
  "language": "ar",
  "generatedStudyGuidance": true,
  "explanations": {
    "q-001": {
      "translation": "Arabic translation of the original question",
      "explanation": [
        "First short Arabic paragraph explaining the concept.",
        "Second short Arabic paragraph explaining why the official answer is correct."
      ],
      "note": "Short Arabic revision note."
    }
  }
}
```

The separate file prevents generated educational guidance from being mistaken for official PDF content.

## Writing Rules

- Arabic must be natural, clear, and suitable for an Egyptian university student.
- Use Modern Standard Arabic with simple technical wording; keep common Windows commands and product names in English when translation would reduce clarity.
- Each translation must cover the complete original prompt. For grouped, matching, ordering, and multi-select questions, translate every statement or item that affects the answer.
- Each explanation must contain two or three short paragraphs.
- Explain the underlying concept and why the official answer is correct.
- Mention why obvious alternatives are wrong only when that materially improves understanding.
- Do not claim that generated explanations came from the PDFs.
- Do not change or override official answers, even when wording or capitalization in the source is imperfect.
- Do not add unrelated facts, invented scenarios, or unsupported source claims.
- Keep notes short, memorable, and focused on exam revision.
- The one unresolved source-conflict item must describe the disagreement between the PDFs and must not select a correct answer.

## User Interface

Add a desktop sidebar item named `Question Explanations`. On mobile, the existing `More` action should continue to expose secondary pages, including explanations.

The explanation page contains:

1. Page title and a short notice that Arabic explanations are added study guidance.
2. Search by English or Arabic text.
3. Filters for source collection, topic, and question type.
4. A result count and a list of compact explanation cards.
5. Pagination or incremental rendering so all 103 entries do not make the first render heavy.

Each card contains:

- Question number, type, topic, and source page references.
- Original English question.
- Arabic translation in an RTL section.
- Official answer in a visually distinct answer block.
- `Why is this correct?` content shown as two or three Arabic paragraphs.
- A highlighted Arabic revision note.
- Bookmark control using the existing LocalStorage state.

The card should use the current restrained navy, blue, white, success, warning, and dark-mode design system. Arabic sections use `dir="rtl"`, right alignment, comfortable line height, and a system Arabic font stack without adding web dependencies.

## Practice and Exam Integration

- Practice feedback adds a collapsible `Arabic Explanation` panel after the official answer review.
- Exam questions continue to hide explanations before submission.
- Exam results add the same panel inside each answer-review item.
- Question Bank keeps official answers hidden until an item is opened; its explanation panel follows the same disclosure behavior.
- Missing explanation data must show a clear unavailable state without breaking the question view.

## Data Loading and Boundaries

Create `study-website/js/explanations.js` to own explanation loading, schema validation, search, filtering, and coverage checks. `app.js` will compose this module with the existing canonical question map. `question-renderer.js` will provide a safe explanation renderer that escapes all JSON content.

The application must load question and explanation data together at startup. A failure to load explanations must not prevent Practice, Exam, Question Bank, or Revision from working.

## Validation

Automated tests must verify:

- Exactly 103 explanation entries exist.
- Every canonical question ID has exactly one explanation.
- There are no unknown explanation IDs.
- Translation, two-or-three-paragraph explanation, and note are non-empty.
- Arabic characters are present in all three fields.
- The unresolved conflict item contains conflict language and does not state a selected correct answer.
- Search works across English prompt, Arabic translation, Arabic explanation, and note.
- Filtering works by source, topic, and question type.
- Rendered content is HTML-escaped.
- Missing explanation data fails softly.

Browser verification must cover the explanation list, search, filters, card expansion, bookmark interaction, Practice integration, Exam Review integration, dark mode, 1440px desktop, and 390px mobile with zero relevant console errors.

## Accessibility

- Use semantic headings and disclosure controls.
- Arabic blocks have explicit RTL direction and Arabic language metadata.
- Keyboard focus remains visible.
- Disclosure controls expose expanded state.
- Color is not the only way to distinguish official answers, explanations, and notes.

## Publishing

After local validation and browser QA, commit the feature to `master`, push to `origin`, wait for the GitHub Pages workflow, and verify the public page plus `data/explanations-ar.json` return HTTP 200.

## Success Criteria

- All 103 questions have reviewed Arabic translation, explanation, and note entries.
- Users can find explanations from a dedicated page and from answer-review flows.
- Official source content and generated study guidance are visually and structurally separated.
- The source-conflict item remains unresolved and unscored.
- Existing study modes and saved progress continue to work.
- Unit tests and live GitHub Pages browser checks pass.
