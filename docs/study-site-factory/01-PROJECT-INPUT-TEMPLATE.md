# Project input template

Copy this form into the new project's input folder and complete every field.

## Copy-ready form

### Project identity

- Project title:
- Short title:
- Project slug:
- Description:
- Brand initials:
- Source language:
- Study language:

### Materials and sources

- Source files and collection labels:
- Optional syllabus, objectives, instructor notes, or answer keys:
- Outside authoritative sources allowed: Yes / No

### Content policy

Select exactly one option; these choices are mutually exclusive.

- [ ] source-only: deliver only material and official source content.
- [ ] source-plus-generated: deliver source content plus labeled generated guidance and questions.
- [ ] generated-only: deliver generated study content supported by the declared materials.

### Missing official answer keys

- Official answer key availability: Complete / Partial / Missing
- When an official answer key is missing, the user supplies: an approved answer key, or a list of items marked `needs-review` with their source references. Items without an approved official answer remain unscored and never enter Mock Exams as official questions.
- Human approval owner for generated questions in Mock Exam:

### Question and exam settings

- MCQs per lesson:
- True/False questions per lesson:
- Generated-question review policy for Mock Exam:
- Default exam question count:
- Default exam minutes:

### Deployment

- Hosting provider:
- GitHub repository:
- GitHub branch:
- Public URL:

## Variable dictionary

| Variable | Meaning |
| --- | --- |
| `PROJECT_TITLE` | Full course or project title. |
| `PROJECT_SHORT_TITLE` | Short navigation and branding title. |
| `PROJECT_SLUG` | Stable lowercase project identifier. |
| `PROJECT_DESCRIPTION` | Short source-backed site description. |
| `BRAND_INITIALS` | Brief brand mark shown by the site. |
| `SOURCE_LANGUAGE` | Language used by the supplied source materials. |
| `STUDY_LANGUAGE` | Language used by learners in the site. |
| `CONTENT_POLICY` | Exactly one of `source-only`, `source-plus-generated`, or `generated-only`. |
| `ALLOW_OUTSIDE_SOURCES` | Whether approved external authoritative sources may be used. |
| `MCQ_PER_LESSON` | Target generated multiple-choice questions per supported lesson. |
| `TRUE_FALSE_PER_LESSON` | Target generated true/false questions per supported lesson. |
| `GENERATED_EXAM_REVIEW_POLICY` | Approval rule required before generated questions enter Mock Exam. |
| `DEFAULT_EXAM_COUNT` | Default number of questions in a Mock Exam. |
| `DEFAULT_EXAM_MINUTES` | Default Mock Exam time limit in minutes. |
| `GITHUB_REPOSITORY` | Deployment repository in `OWNER/REPOSITORY` form. |
| `GITHUB_BRANCH` | Branch published by the deployment provider. |
| `PUBLIC_URL` | Expected public website URL. |
