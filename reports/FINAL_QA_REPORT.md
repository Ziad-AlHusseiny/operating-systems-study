# Final browser QA report — Operating Systems Study

## Scope and environment

- Tested revision: Task 8 fix-round candidate based on `30a435b`, 2026-08-24.
- Environment: Windows, Python static server, Node with the bundled Codex dependency runtime, and a clean temporary Playwright browser context.
- Browser classification: the in-app Browser invocation previously failed before initialization with `failed to write kernel assets: The system cannot find the path specified. (os error 3)`. Per the recorded fallback, QA used direct Playwright loaded through `createRequire()` and `NODE_PATH`.
- The bundled Playwright Chromium executable was absent (`chromium_headless_shell-1234`); no browser was downloaded or installed. The runner used the already-installed `C:\Program Files\Google\Chrome\Application\chrome.exe` in an incognito Playwright context.
- Test URL: `http://127.0.0.1:8000/`; the runner started and stopped only its own `python -m http.server 8000 --directory study-website` child.
- Workflow verification: the Pages YAML was manually reviewed and its exact parser-install command/order is covered by `scripts/test_pages_workflow.py`. The locally available parser is `pypdf 6.9.2`, matching the pinned Actions command.

## Content measurements

| Measure | Result |
| --- | ---: |
| PDFs / sources | 21 |
| Extracted pages | 517 |
| Teaching pages | 454 |
| Teaching-page coverage | 454/454 |
| Modules / lessons | 7 / 21 |
| Questions / Arabic explanations | 210 / 210 |
| Module lesson/question distribution | 4/40, 3/30, 3/30, 4/40, 2/20, 3/30, 2/20 |

## Fresh command record

| Command | Result |
| --- | --- |
| `python -B scripts/extract_os_material.py --check --pdf-root "D:\UNI - EELU\0\PREVIOUS CONTENT\S-5\OS\Lectures"` | Pass (exit 0): 21 sources, 517 pages; non-writing comparison of extraction, manifest, and audit artifacts |
| `python -B -c "import pypdf; print(pypdf.__version__)"` | Pass (exit 0): `6.9.2`, matching the Pages workflow pin |
| `python -B scripts/build_os_site_data.py --check` | Pass (exit 0): 7 modules, 21 lessons, 210 questions, 210 Arabic explanations |
| `python -B scripts/validate_os_site.py` | Pass (exit 0): 21 sources, 517 pages, 454 teaching pages, 210 practice and 210 Mock Exam eligible records |
| `python -B -m unittest discover -s scripts -p "test_*.py" -v` | Pass (exit 0): 216 tests |
| `node --check study-website/js/app.js` | Pass (exit 0) |
| `node --check study-website/tests/browser-check.mjs` | Pass (exit 0) |
| `node --test study-website/tests/*.test.mjs` | Pass (exit 0): 42 tests |
| `NODE_PATH=C:\Users\dark0\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules; node study-website/tests/browser-check.mjs` | Pass twice after browser-check changes (exit 0): all flows; page/console/warning/request/data failures 0/0/0/0/0 |
| `git diff --check` | Pass (exit 0): no whitespace errors (Git emitted only repository line-ending conversion warnings) |

## Browser-flow evidence

Desktop was tested at 1440×1000; mobile was tested at 390×844. The runner verified Dashboard measurements/loading/overlay absence; Material filtering and a long lesson; source English and generated Arabic guidance; lesson completion/bookmarks; MCQ no-leak, Arabic feedback, answer locking, and finish; True/False controls; Question Bank from 210 results/page 1 of 21 to a typed exact search with 1 result/page 1 of 1; real Arabic-guidance link navigation to a filtered explanation with full Arabic paragraphs and citations; active-exam answer-only non-leakage through final review; Revision/Mistakes/Bookmarks focused actions; and Settings export, immediate reload persistence, Cancel focus trap, UI reset, import, and byte-for-byte export restoration.

Mobile verification found no horizontal overflow, a fixed unclipped bottom navigation, rendered RTL guidance (286px visible region), and 44px visible controls. The active Mock Exam surface had no feedback/guidance/rationale fields until submission. Every console warning is now a blocking browser-health failure; there are no benign-warning exemptions. Final browser totals were page errors 0, console errors 0, console warnings 0, failed requests 0, and non-2xx essential data requests 0.

## Screenshot evidence

Temporary directory (not committed): `C:\Users\dark0\AppData\Local\Temp\os-study-qa-IDFVKx`

| Screenshot | Dimensions | Temporary path |
| --- | ---: | --- |
| `dashboard-desktop-light.png` | 1440×1000 | `C:\Users\dark0\AppData\Local\Temp\os-study-qa-IDFVKx\dashboard-desktop-light.png` |
| `material-desktop-light.png` | 1440×1000 | `C:\Users\dark0\AppData\Local\Temp\os-study-qa-IDFVKx\material-desktop-light.png` |
| `lesson-desktop-light.png` | 1440×6921 | `C:\Users\dark0\AppData\Local\Temp\os-study-qa-IDFVKx\lesson-desktop-light.png` |
| `practice-feedback-desktop.png` | 1440×1291 | `C:\Users\dark0\AppData\Local\Temp\os-study-qa-IDFVKx\practice-feedback-desktop.png` |
| `exam-active-desktop.png` | 1440×1000 | `C:\Users\dark0\AppData\Local\Temp\os-study-qa-IDFVKx\exam-active-desktop.png` |
| `revision-desktop-dark.png` | 1440×1000 | `C:\Users\dark0\AppData\Local\Temp\os-study-qa-IDFVKx\revision-desktop-dark.png` |
| `dashboard-mobile-light.png` | 390×844 | `C:\Users\dark0\AppData\Local\Temp\os-study-qa-IDFVKx\dashboard-mobile-light.png` |
| `practice-mobile-feedback.png` | 390×1990 | `C:\Users\dark0\AppData\Local\Temp\os-study-qa-IDFVKx\practice-mobile-feedback.png` |

## Visual mismatch ledger

| Surface | Finding | Outcome |
| --- | --- | --- |
| Sidebar/topbar/mobile navigation | Desktop geometry matches the fixed navy rail and open white workspace; mobile bottom navigation is fixed and unclipped. | Pass |
| Metric region and hierarchy | Dashboard uses an open divided metrics region rather than a card wall, with an immediately readable title and actions. | Pass |
| Answer rows, feedback, and session rail | The practice and active-exam workspace retain bordered answer rows, progress, action row, and rail. Active exam remains answer-only. | Pass |
| Arabic RTL | Arabic guidance wraps inside a clear RTL panel at both viewports. | Pass |
| Dark contrast/focus | Dark revision contrast and visible focus treatment are readable. | Pass |
| Rapid status feedback | A stacked toast sequence covered controls in the initial browser pass. The runner first failed on this case; `notify()` now retains only the latest status, and the rerun passed. | Fixed |
| 390px targets | Navigator buttons were 36px high in the initial browser pass. The runner first failed on this case; mobile CSS now makes them 44px, and the rerun passed. | Fixed |
| Revision readability | The first dark-mode capture placed each weak-area title directly beside its score metadata. A browser layout assertion first failed; the row metadata now forms a separate line. | Fixed |
| Mobile toast placement | The first 390px capture placed the status toast over the fixed navigation. A browser layout assertion now requires its bottom edge to stay above the navigation. | Fixed |
| Clean final evidence | Each of the eight final captures waited for transient toasts to disappear, returned to top-left scroll, and blurred focus. The skip link was asserted hidden before capture; inspection found no toast or focused-skip-link artifact. | Pass |

## State, policy, and deployment

- Local keys: `os-study-progress-v1` for progress and `os-study-theme-v1` for theme. Exported JSON contained `projectId: operating-systems-study`; the browser proved its activity was present immediately after reload before importing anything, confirmed Cancel left that state unchanged, reset it through the UI, imported it, and compared a new export byte-for-byte with the original. The reset dialog also trapped Tab/Shift+Tab and dark theme persisted.
- Generated questions and Arabic explanations are source-backed low-stakes study content only. The private course PDFs are not available to GitHub Actions; CI validates the checked-in source extraction corpus/manifest and generated artifacts instead.
- Deployment fields: provider `github-pages`; repository `Ziad-AlHusseiny/operating-systems-study`; branch `main`; URL `https://ziad-alhusseiny.github.io/operating-systems-study/`.
- Workflow: `main` push and manual dispatch; checkout; stable Python; a pinned `pypdf==6.9.2` installation before the extraction and Python checks; stable Node; extraction-artifact check, builder check, independent validator, Python tests, Node syntax/unit checks; then `actions/configure-pages@v5`, `actions/upload-pages-artifact@v4` for exactly `study-website`, and `actions/deploy-pages@v4`. The committed source audit omits the runtime parser version so equivalent extractions remain deterministic across supported parser versions.
- Deployment status: **Pending final review/push**. No remote repository creation, push, or public HTTP verification was performed.
