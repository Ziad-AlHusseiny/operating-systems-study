# UX and system-flow contract

This contract fixes the route structure, interactions, responsive navigation,
and safety boundaries for every study-site project. Project-specific wording,
branding, language, quotas, and policies come only from
[01-PROJECT-INPUT-TEMPLATE.md](01-PROJECT-INPUT-TEMPLATE.md).

## Route map

| Route | Purpose | Primary action |
| --- | --- | --- |
| Dashboard | Show learning position and entry points. | Open a material, practice, or revision path. |
| Material | Browse the material index by module or lesson. | Open a Lesson. |
| Lesson | Read source-backed learning content and linked questions. | Start linked Practice. |
| Practice | Choose a pool and answer with immediate feedback. | Continue to results or revision. |
| Mock Exam | Configure, sit, submit, and review a timed assessment. | Start or resume an exam. |
| Question Bank | Find a question by topic, type, origin, or state. | Open a question. |
| Question Explanations | Separate the marked/source answer from study guidance. | Return to its question or source. |
| Revision Summary | View scoreable progress and weak areas. | Start focused Practice. |
| Mistakes | Revisit previously incorrect scoreable attempts. | Start focused Practice. |
| Bookmarks | Revisit saved lessons or questions. | Open an item or start focused Practice. |

## Core journeys

```text
Dashboard -> Material -> Lesson -> linked Practice
Dashboard -> Practice setup -> question -> feedback -> results
Dashboard -> Mock Exam setup -> active exam -> submit -> answer review
Question Bank -> opened question -> marked/source answer -> generated guidance
Material lesson -> linked official/generated questions
Revision/Mistakes/Bookmarks -> focused Practice
```

Practice setup exposes official, generated, and mixed pools only when allowed
by the configured content mode. The learner sees one of these fixed labels at
the item boundary:

- `Official source content`
- `Generated study guidance`
- `Generated practice question`
- `Needs review — unscored`

## Navigation and responsiveness

Desktop navigation order is Dashboard, Material, Practice, Mock Exam, Question
Bank, Revision Summary, Mistakes, and Bookmarks. Question Explanations is a
contextual route reached from a question rather than a top-level destination.

Mobile primary navigation contains Dashboard, Material, Practice, and Mock
Exam. A More menu contains Question Bank, Revision Summary, Mistakes,
Bookmarks, preferences, and any contextual return path. The current route is
identified programmatically and visually; opening and closing the More menu is
keyboard accessible and preserves focus predictably.

## Route-level states

Every route defines these states without blocking navigation:

| State | Required behavior |
| --- | --- |
| Loading | Use a labeled progress indicator; retain the page heading and never present placeholder content as a question or answer. |
| Empty | Explain what is unavailable, why it may be empty, and provide one valid next action. |
| Error | Give a concise failure message, preserve safe data, offer retry or return navigation, and never invent missing source content. |

Dashboard shows an empty onboarding path when no materials are available.
Material and Lesson distinguish no matching content from unavailable source
media. Practice and Mock Exam block a start when no eligible questions exist.
Question Bank, Question Explanations, Revision Summary, Mistakes, and
Bookmarks explain zero results and keep their filters or saved data intact.

## Question interactions and exam safety

Practice reveals feedback only after an answer is submitted. Feedback includes
the answer state, scoreability, origin label, and an available route to the
Question Explanations view.

Mock Exam setup confirms scope, eligible count, question count, and time. In
an active exam, the UI exposes only the prompt, permitted choices, progress,
timer, bookmark control, and submit control. It must not reveal explanations,
rationales, marked answers, source answers, generated guidance, correctness,
or score until submit or expiry. Answer review starts after the result is
finalized and clearly identifies items excluded from scoring.

## Accessibility and language

- Interactive targets are at least 44px in both touch dimensions, with space
  sufficient to avoid accidental activation.
- Every keyboard-reachable control has a visible focus indicator; route
  changes move focus to the page heading or announced main content.
- Use semantic landmarks, a single page-level heading, ordered heading levels,
  native labels, and accessible names for icons and controls.
- Set `lang` and `dir` at document and route boundaries. Source excerpts or
  translations with a different language or direction receive their own
  explicit `lang` and `dir` boundary.
- Dark mode preserves readable contrast and does not rely on color alone for
  correctness, origin, review state, or current navigation.

## System state rules

- Route parameters use stable IDs and reject malformed or unavailable IDs with
  the route error state.
- Filters, search, pagination, and selected practice scope are reflected in
  the route state where practical and restored from validated local progress.
- Versioned local progress may restore an unfinished active Mock Exam without
  exposing answer feedback. Import, export, and reset are reachable from the
  More menu or preferences.
- A reviewed result updates Revision Summary and Mistakes only for scoreable
  questions. Bookmarks remain independent of scoring.
