# ITS Device Configuration and Management Study Website

## Purpose

Build a complete, lightweight study website from the two supplied official PDFs:

- `Device_Configuration_and_Management_Eng_Ali_Mohamed.pdf`
- `ITS OD 103 Pre-Test.pdf`

The first PDF contains 105 question pages after its cover. The second contains a 70-question pre-test presented mainly as slide images. Every question and official answer from both PDFs must be included. No outside questions, answers, explanations, or factual content may be added.

## Product Scope

The application is a single-page static website. It includes:

- Dashboard
- Complete Question Bank
- Practice Mode
- Mock Exam Mode
- Revision Summary
- Mistake Review
- Bookmarks
- Session and Exam Results
- Progress import, export, and reset

## Source and Extraction Rules

- Extract every question from both PDFs.
- Preserve original wording except for obvious OCR or formatting corrections.
- Validate official answers against the visible PDF pages.
- Support every existing question format, including MCQ, grouped True/False, matching, ordering, multi-select, and other source formats.
- Detect exact and near-duplicate questions.
- Merge duplicates into a canonical item while preserving every source PDF, question number, and page number.
- Allow filtering by either original PDF collection.
- Mark unclear text, choices, or answers with `needsReview: true`.
- Do not guess unclear content.
- Keep unclear items available for inspection but exclude them from scored exams by default.
- Do not generate explanations when the PDFs do not contain explanations.

## Data Model

The canonical question JSON stores:

- Stable ID
- Question type
- Original prompt
- Options, statements, pairs, or ordered items as required by the source format
- Official correct answer or answer set
- Source collection references
- Original question numbers and PDF page numbers
- Topic/category when it can be determined from the source without inventing content
- Official explanation only when present
- Duplicate references
- Review status and review notes

Progress data is stored separately in LocalStorage and never changes the canonical question data.

## Technical Architecture

Use only:

- HTML
- CSS
- Vanilla JavaScript
- JSON
- LocalStorage

There is no framework, TypeScript, backend, database, authentication, package installation, or build step. JavaScript is divided into small files by responsibility. The website runs from a simple static server and deploys directly to GitHub Pages, Netlify, or Vercel.

## Main Interface

### Dashboard

Show the course name, total unique questions, source totals, question-type counts, answered/correct/wrong counts, accuracy, completion, recent session, and quick actions.

### Question Bank

Search question text and filter by source, type, topic, answer status, bookmark status, and manual-review status. Correct answers stay hidden until a question is opened.

### Practice Mode

Configure source, type, topic, answer status, question count, original/random order, and optional choice shuffling. Show one question at a time with progress, source references, navigation, skipping, bookmarking, and immediate answer feedback. Choice shuffling must preserve answer mapping.

### Mock Exam

Configure question count and optional timer. Hide feedback until submission. Support navigation, answered/unanswered state, review flags, submission confirmation, scoring, time taken, source/topic performance, complete answer review, retrying wrong questions, and retaking the exam.

### Revision Summary

Provide quick-review cards made only from original question wording and official answers. Support source/topic filters, weak-topic summaries based on the user's own results, bookmarked items, and frequently missed questions. Every card links to its original source page. It must not contain generated explanations or outside information.

### Mistakes and Bookmarks

Show prior selected answers, official answers, incorrect-attempt counts, sources, and official explanations when present. Allow focused practice from either collection.

### Results

Show correct, wrong, skipped, accuracy, duration, source/topic performance, and incorrect questions. Recommendations may refer only to the user's measured performance.

## Persistence

LocalStorage saves:

- Answer history
- Correct, wrong, and unanswered status
- Incorrect-attempt counts
- Bookmarks
- Practice sessions
- Exam results
- Theme
- Last opened question
- Current in-progress session or exam
- Review flags

Export progress as JSON, validate imported JSON before applying it, and require confirmation before resetting progress.

## Interaction and Visual Design

- Clean, restrained, study-focused layout
- Responsive desktop and mobile behavior
- Desktop sidebar and mobile bottom navigation
- Light and dark themes
- Comfortable line lengths and spacing for long sessions
- Minimal animation
- Visible keyboard focus states
- Shortcuts: `1`-`4`, `T`, `F`, arrow keys, and `B`
- Shortcuts are disabled while typing in inputs or search fields

## Error Handling

- Show helpful empty states for filters with no results.
- Reject damaged or incompatible progress imports without changing existing data.
- Restore timers and in-progress state safely after refresh.
- Prevent submission mistakes with a confirmation step.
- Handle missing optional metadata without breaking question rendering.
- Clearly label manual-review items.

## Validation and Testing

Validate:

- Complete extraction from both PDFs
- Duplicate detection
- Missing prompts, choices, or answers
- Correct answer mapping
- Multi-answer and grouped-statement scoring
- Source page references
- OCR corrections
- Practice filters and ordering
- Choice shuffling
- Mock exam scoring and timer recovery
- Bookmarks and mistake review
- LocalStorage persistence
- Import, export, and reset
- Dark mode
- Mobile responsiveness
- Long content
- Keyboard shortcuts
- Browser console errors and broken controls

Create `QUESTION_EXTRACTION_REPORT.md` with page totals, raw source totals, unique totals, type totals, duplicate counts, unclear items, extraction failures, and formatting corrections.

## Project Structure

```text
study-website/
|-- index.html
|-- css/
|   `-- styles.css
|-- js/
|   |-- app.js
|   |-- quiz.js
|   |-- exam.js
|   |-- storage.js
|   |-- statistics.js
|   `-- question-renderer.js
|-- data/
|   `-- questions.json
|-- tests/
|   `-- tests.html
|-- README.md
`-- QUESTION_EXTRACTION_REPORT.md
```

Extraction helpers and temporary rendered PDF pages may live outside the final `study-website/` delivery folder.

## Completion Criteria

The work is complete when:

- All extractable official content from both PDFs is represented.
- Every scored answer is traceable to a visible official answer.
- Unclear content is reported rather than guessed.
- All requested study, exam, revision, filtering, and persistence features work.
- Automated and browser tests pass.
- The website has no known console errors or broken controls.
- Documentation explains running, editing, validating, and deploying the static site.
