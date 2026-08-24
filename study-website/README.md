# Operating Systems Study

Operating Systems Study is a static, bilingual study and Mock Exam website. It uses plain HTML, CSS, browser-native JavaScript, public JSON payloads, and browser LocalStorage. It has no framework, backend, build step, external font, or runtime dependency.

## Run locally

From the repository root:

```powershell
python -m http.server 8000 --directory study-website
```

Open [http://127.0.0.1:8000/#/dashboard](http://127.0.0.1:8000/#/dashboard). On Windows, `START_WEBSITE.bat` starts the same static server.

The site uses hash routes, so it works unchanged from a GitHub Pages subpath or another static-host directory.

## Study routes

- Dashboard: measured course coverage, completion, accuracy, recent sessions, and priorities.
- Material and Lesson: searchable source-backed learning objectives, sections, terms, examples, recap, citations, and linked Practice.
- Question Bank and Explanations: searchable questions with an explicit answer reveal and complete Arabic generated study guidance.
- Practice: scoped question sessions with immediate feedback after answer submission.
- Mock Exam: scoped, timed answer-only session until submit or expiry; review appears only after finalization.
- Revision, Mistakes, and Bookmarks: scoreable performance, focused review, and separate saved lesson/question collections.
- Settings: theme preference plus validated local progress export, import, and reset.

## Progress and safety

Progress uses the versioned `os-study-progress-v1` browser key. Exported JSON is validated before it can replace the current state; an invalid import does not overwrite valid progress. Reset removes only documented Operating Systems Study progress and theme keys.

Active Mock Exams persist only question IDs, learner responses, navigation, flags, bookmarks, and timing. Correct answers, rationales, citations, and Arabic guidance are not present in the active exam surface or serialized active-exam state. They become available only in the finalized review.

## Checks

Run these from the repository root:

```powershell
node --check study-website/js/app.js
node --test study-website/tests/*.test.mjs
python -B scripts/build_os_site_data.py --check
python -B scripts/validate_os_site.py
```

The data files are generated project artifacts; do not edit them directly.
