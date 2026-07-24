# Study Website Visual System

## Accepted References

- `dashboard.png`: primary dashboard composition, navigation, zero-state metrics, and light theme.
- `practice.png`: question workspace, answer rows, progress, keyboard hint, session rail, and footer actions.

The user approved a simple, modern interface and instructed implementation to continue without further approval pauses. These generated concepts translate that approved direction into the visual reference used for implementation.

## Visible Copy Lock

The first viewport may show only these supplied or approved labels:

- ITS Device Configuration and Management
- Dashboard
- Practice
- Mock Exam
- Question Bank
- Revision Summary
- Mistakes
- Bookmarks
- Completion
- Accuracy
- Source entries
- Answered
- Correct
- Wrong
- Start Practice
- Start Mock Exam
- Continue Practice
- Review Mistakes
- Review Bookmarks
- Recent Activity
- No recent activity yet.
- Revision Summary (Preview)
- Light
- Dark

Question screens may additionally use the labels and controls defined in the product specification, including question number, type, PDF source/page, Previous, Skip, Bookmark, Next, Finish Session, and keyboard hints.

## Design Tokens

- Main background: true white `#ffffff`
- Secondary background: cool gray `#f6f8fb`
- Sidebar: deep navy `#031b3d`
- Sidebar selected: blue `#0878f9`
- Primary: `#0878f9`
- Primary hover: `#0565d6`
- Text: `#0b1730`
- Muted text: `#5f6b7a`
- Border: `#d7dee8`
- Success: `#159947`
- Error: `#d82424`
- Warning: `#b77900`
- Radius: 8px for controls, 10px for primary regions
- Shadow: none by default; `0 8px 24px rgb(11 23 48 / 8%)` only for dialogs
- Spacing: 4, 8, 12, 16, 24, 32, 48px
- Motion: 150ms for hover and selected-state transitions

## Typography

- Family: Inter when locally available, then `Segoe UI`, Arial, sans-serif
- Page title: 32px / 1.15 / 700
- Section heading: 20px / 1.3 / 700
- Question text: 18px / 1.55 / 500
- Body: 15px / 1.55 / 400
- Control: 14px / 1.2 / 600
- Caption: 13px / 1.4 / 500

## Components

- Sidebar: 224px desktop, selected row uses a solid blue background, outline icons at 20px.
- Top bar: 64px, one-pixel bottom divider, course name left, theme control right.
- Metric region: one framed open container separated by thin dividers; no floating card grid.
- Buttons: solid primary, outline secondary, quiet text button, destructive confirmation variant.
- Answer row: full-width bordered row with numeric/letter marker, selected blue border, correct green state, wrong red state.
- Question rail: 264px desktop; moves below the question below 1024px.
- Mobile navigation: fixed bottom rail with the most important destinations and a More menu for the rest.
- Dialog: centered, narrow, strong focus trap, no decorative header.
- Toast: compact status message with semantic color and no blocking behavior.

## Container and Responsive Rules

- Desktop uses a fixed sidebar and an open main workspace.
- Main content width is fluid with 24-32px gutters and a readable inner maximum of 1280px.
- At 1024px, the question rail moves below the main question.
- Below 900px, the sidebar becomes a mobile bottom navigation.
- Below 600px, actions wrap into two rows, metric dividers become stacked rows, and answer text keeps a minimum 16px size.
- No horizontal scrolling at 390px.

## Icon Inventory

Use consistent inline SVG icons with `viewBox="0 0 24 24"`, `fill="none"`, `stroke="currentColor"`, `stroke-width="1.75"`, round caps, and round joins:

- Dashboard: house
- Practice: pencil
- Mock Exam: document
- Question Bank: stacked sheets
- Revision Summary: list/chart
- Mistakes: circle-x
- Bookmarks: bookmark
- Previous/Next: chevrons
- Skip: next-bar
- Theme: sun/moon
- Search: magnifier
- Filter: funnel
- Export/Import: arrow from/to tray
- Reset: rotate arrow

## Intentional Deviations

- The concepts show zero-state values because the canonical unique-question count is not known until extraction and deduplication finish. The implementation will replace source and unique totals with validated data.
- The generated Practice example contains illustrative question text that is not an official source question. It is layout-only reference and must never appear in production.
- Dark theme will reuse the same geometry with navy/near-black surfaces and accessible contrast.
