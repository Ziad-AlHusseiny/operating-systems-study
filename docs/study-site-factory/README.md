# Study-site documentation factory kit

## Purpose

This kit provides the reusable instructions and data contracts for building a
source-backed static study and exam website from a new course's materials.

## Use this kit when

Use this kit for a new course that needs traceable lessons, official questions,
generated practice content, and a static study website with a stable flow.

## Do not use it for

Do not use this kit for a backend, account system, automatic publishing, or a
project that must present generated content as official source material.

## Reading order

Read the numbered documents in filename order. Start with the project input and
configuration, then read only the stage-specific documents needed for the work.

- [00 — Quick start](00-QUICK-START.md)
- [01 — Project input template](01-PROJECT-INPUT-TEMPLATE.md)
- [02 — PRD template](02-PRD-TEMPLATE.md)
- [03 — Source ingestion specification](03-SOURCE-INGESTION-SPEC.md)
- [04 — Content and data contracts](04-CONTENT-AND-DATA-CONTRACTS.md)
- [05 — Material lessons specification](05-MATERIAL-LESSONS-SPEC.md)
- [06 — Question generation specification](06-QUESTION-GENERATION-SPEC.md)
- [07 — UX and system flow](07-UX-AND-SYSTEM-FLOW.md)
- [08 — Build workflow](08-BUILD-WORKFLOW.md)
- [09 — QA gates](09-QA-GATES.md)
- [10 — Master build prompt](10-MASTER-BUILD-PROMPT.md)
- [11 — Handoff and deployment](11-HANDOFF-AND-DEPLOYMENT.md)

Reference JSON examples:

- [Project configuration](examples/project-config.example.json)
- [Source manifest](examples/source-manifest.example.json)
- [Lesson](examples/lesson.example.json)
- [Official question](examples/official-question.example.json)
- [Generated question](examples/generated-question.example.json)
- [Explanation](examples/explanation.example.json)

## Fixed system

The static architecture, source references, stable IDs, review-item handling,
official/generated separation, core study flow, quality gates, and deployment
checks stay fixed unless the product itself changes.

## Configurable inputs

Each course supplies its title, description, languages, branding, source
collection, question quotas, review policy, exam defaults, and deployment
destination through the project input and configuration files.

## Official versus generated content

Official questions and marked answers stay faithful to supplied sources.
Generated lessons, explanations, and questions remain separate, visibly
labeled, and traceable to their supporting source references. Missing or
uncertain official answers are review-only and unscored.

## Validation

Run the kit validator before handoff:

```powershell
python -B scripts/validate_factory_kit.py
```

It reports missing required files, invalid JSON and contracts, missing required
headings, undeclared template variables, broken relative links, and unfinished
delivery markers.
