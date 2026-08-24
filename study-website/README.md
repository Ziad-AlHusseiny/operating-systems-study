# Operating Systems Study

Operating Systems Study is a static bilingual study and low-stakes Mock Exam website. It uses semantic HTML, CSS, browser-native JavaScript, checked-in JSON payloads, and browser LocalStorage—no framework, backend, bundler, external font, or runtime API.

## Coverage and policy

The published learning data covers all 21 supplied Operating Systems PDFs: 517 extracted pages, including 454 teaching pages. Every teaching page is referenced by the course data (454/454 coverage). The site contains 7 modules, 21 lessons, 210 generated practice questions, and 210 complete Arabic explanation records.

| Module | Lessons | Questions |
| --- | ---: | ---: |
| Chapter 1: Introduction | 4 | 40 |
| Chapter 2: Operating-System Structures | 3 | 30 |
| Chapter 3: Processes | 3 | 30 |
| Chapter 5: CPU Scheduling | 4 | 40 |
| Chapter 6: Synchronization Tools | 2 | 20 |
| Chapter 8: Deadlocks | 3 | 30 |
| Chapter 9: Main Memory | 2 | 20 |

Generated questions and Arabic guidance are source-backed study material for low-stakes learning only. They are not authorized for high-stakes, credentialing, admissions, employment, compliance, or externally reported assessment. Such use requires current complete human approval.

## Run locally

From the repository root:

```powershell
python -m http.server 8000 --directory study-website
```

Open [http://127.0.0.1:8000/#/dashboard](http://127.0.0.1:8000/#/dashboard). On Windows, `START_WEBSITE.bat` starts the same server. Hash routes make the site safe to host under the GitHub Pages subpath.

## Routes

- `#/dashboard` — measured coverage, completion, accuracy, sessions, and priorities.
- `#/material` and `#/lesson/:canonicalLessonId` — search/filter lessons, source material, generated Arabic guidance, citations, and linked Practice.
- `#/questions` and `#/explanations` — searchable question records, explicit non-exam answer reveal, citations, and full Arabic guidance.
- `#/questions/:gq-id` and `#/explanations/:gq-id` — canonical exact-record routes used by lesson links and Arabic-guidance links; unavailable IDs show a safe not-found state.
- `#/practice` — scoped immediate-feedback sessions.
- `#/exam` — scoped timed answer-only Mock Exam until final submission/expiry; review appears only afterwards.
- `#/revision`, `#/mistakes`, and `#/bookmarks` — scoreable performance, focused review, and separate saved lesson/question collections.
- `#/settings` — theme and local-progress controls.

`#/bank` remains a compatibility alias for `#/questions`.

## Data and correction workflow

The source PDFs are private course inputs and are intentionally not committed. Their checked-in extraction artifacts are `extraction/os-pages.json`, `content/source-manifest.json`, and `reports/SOURCE_AUDIT_REPORT.md`; the generated site payloads are under `study-website/data/`.

On a machine with the private PDFs, use the configured PDF root for a source check, then build and validate generated artifacts:

```powershell
python -B scripts/extract_os_material.py --check --pdf-root "D:\UNI - EELU\0\PREVIOUS CONTENT\S-5\OS\Lectures"
python -B scripts/build_os_site_data.py --check
python -B scripts/validate_os_site.py
```

Do not edit generated JSON directly. Correct source/content inputs, regenerate through the approved data workflow, and rerun the checks. GitHub Actions cannot read the private PDF root; it validates the checked-in extraction manifest/corpus through `test_extract_os_material.py`, then validates and checks the generated public payloads.

## Progress, imports, and exams

Progress uses `os-study-progress-v1`; the separately scoped theme key is `os-study-theme-v1`. Exported JSON is validated before import, invalid imports leave valid progress unchanged, and Reset removes only these Operating Systems Study progress/theme keys. Active Mock Exams persist only question IDs, learner responses, navigation, flags, bookmarks, and timing. Correct answers, rationales, citations, and Arabic guidance remain absent from the active exam DOM/state and are shown only after finalization.

## Verification

Run these commands from the repository root:

```powershell
python -B scripts/extract_os_material.py --check --pdf-root "D:\UNI - EELU\0\PREVIOUS CONTENT\S-5\OS\Lectures"
python -B scripts/build_os_site_data.py --check
python -B scripts/validate_os_site.py
python -B -m unittest discover -s scripts -p "test_*.py" -v
node --check study-website/js/app.js
node --check study-website/tests/browser-check.mjs
node --test study-website/tests/*.test.mjs
$env:NODE_PATH="C:\Users\dark0\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules"
node study-website/tests/browser-check.mjs
```

The browser QA script uses a clean temporary Playwright context, starts the local static server when needed, checks desktop and 390px mobile flows, and writes screenshots outside the repository. The in-app Browser fallback was unavailable in the recorded environment; Playwright is the approved fallback. The supplied Playwright runtime must be available through `NODE_PATH`; if its bundled Chromium executable is absent, the runner may use an already-installed local Chromium executable without downloading a browser.

## GitHub Pages

The deployment target is `Ziad-AlHusseiny/operating-systems-study` on `main`. The Pages workflow validates checked-in artifacts and tests before configuring Pages, uploads exactly `study-website`, then deploys with the official GitHub Pages actions.

Pending final review/push: [https://ziad-alhusseiny.github.io/operating-systems-study/](https://ziad-alhusseiny.github.io/operating-systems-study/). No repository has been created, pushed, or verified publicly by this project.
