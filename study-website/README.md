# ITS Device Configuration and Management Study Website

This is a lightweight static study website built with plain HTML, CSS, JavaScript, JSON, and browser LocalStorage. It has no framework, backend, database, account, build step, or runtime package dependency.

## Official content

- 175 official source entries: 105 from the question bank and 70 from the pre-test
- 103 unique questions after merging 72 duplicate source entries
- All 175 source references preserved with collection, original question number, and PDF page
- One official answer conflict clearly marked as unscored and shown with its source-page image

No answer or explanation was invented. See `QUESTION_EXTRACTION_REPORT.md` for the measured extraction record and the exact conflict.

## Features

- Dashboard with completion, accuracy, recent sessions, and revision totals
- Searchable Question Bank with source, type, topic, status, bookmark, and review filters
- Question Explanations with the original English prompt, Arabic translation, answer reasoning, and revision notes
- Practice by source, type, topic, progress status, count, order, and optional choice shuffling
- Timed or untimed Mock Exams with question navigation, flags, hidden feedback, and complete review
- Revision Summary with source/topic filters and performance-based weak topics
- Mistake and bookmark collections with focused practice
- Light and dark themes
- Keyboard controls: `1`–`4`, `T`, `F`, arrow keys, `Enter`, and `B`
- Progress import, export, reset, and in-progress session recovery

## Start

From the project folder, run:

```powershell
python -m http.server 8000 --directory study-website
```

Then open <http://127.0.0.1:8000>.

On Windows, you can also double-click `START_WEBSITE.bat` in the parent folder.

## Project structure

```text
study-website/
├── index.html
├── css/styles.css
├── data/questions.json
├── data/explanations-ar.json
├── assets/source-pages/
├── js/
│   ├── app.js
│   ├── explanations.js
│   ├── explanations-view.js
│   ├── question-renderer.js
│   ├── questions.js
│   ├── quiz.js
│   ├── revision.js
│   ├── statistics.js
│   └── storage.js
├── tests/
├── QUESTION_EXTRACTION_REPORT.md
└── README.md
```

The canonical question records contain a stable ID, type, prompt, type-specific controls, official answer, source references, review state, and an official explanation only when one exists in the PDFs.

## Question Explanations

Open **Question Explanations** from the desktop sidebar or **More → Question Explanations** on mobile. The page starts with 15 explanations and can reveal 15 more at a time. Search matches the canonical English prompt and the Arabic translation, explanation, and revision note. Source, topic, and question-type filters can be combined with either English or Arabic search text.

Every Arabic explanation is labeled **Generated study guidance**. It supports study only: it is not an official PDF explanation, it does not replace an official answer, and it does not change canonical question data. The same guidance appears after a Practice answer is checked and inside closed Question Bank and Exam Result review disclosures. It is never shown during an active Mock Exam.

## Progress data

Progress is saved only in the current browser under `its-study-progress-v1`. Use **Progress Data → Export** to create a JSON backup and **Import** to restore a validated backup. Reset requires confirmation.

## Validate content and logic

Run from the parent project folder:

```powershell
python scripts/validate_questions.py
python scripts/build_explanations.py
node --check study-website/js/app.js
node --check study-website/js/explanations.js
node --check study-website/js/question-renderer.js
node --test study-website/tests/*.test.mjs
```

The question validator recreates the canonical data from `extraction/raw-questions.json`, verifies both collection totals, checks official-answer mappings, and regenerates the extraction report. The explanation builder merges and validates exactly 103 Arabic entries before writing `study-website/data/explanations-ar.json`.

## Maintain Arabic guidance

The editable explanation content is split into four files:

- `content/explanations-ar/q001-026.json`
- `content/explanations-ar/q027-052.json`
- `content/explanations-ar/q053-078.json`
- `content/explanations-ar/q079-103.json`

To correct an Arabic translation, explanation paragraph, or revision note, edit only the matching question ID in its content-part file and run `python scripts/build_explanations.py`. Do not edit the generated `study-website/data/explanations-ar.json` directly, and do not change the canonical prompt, answer, or source references in `questions.json` to make guidance text agree with an assumption.

When correcting official source data, update the extraction or validation logic, preserve the exact PDF source reference, and run `python scripts/validate_questions.py` before rebuilding explanations. If the official PDFs disagree, keep `needsReview: true`, leave the official answer unresolved, describe both sources without choosing one, and keep the item unscored. Do not resolve conflicts by guessing or by copying generated guidance into official question data.

## Deploy

The `study-website` folder can be published as-is to any static host:

- Netlify: deploy the folder with no build command.
- GitHub Pages: publish the folder contents from a Pages branch or `/docs` folder.
- Vercel: set the output/root directory to `study-website` and use no framework preset.

## Known limitations

- OCR preserves some grammar, capitalization, and spelling problems visible in the supplied PDFs.
- The two PDFs disagree on one backup-answer item. It remains available for revision but is excluded from mock exams by default and is never scored.
- Progress belongs to one browser profile unless exported and imported elsewhere.
