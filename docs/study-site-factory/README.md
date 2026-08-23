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

It reports missing required files and invalid JSON. Later documents extend its
validation checks as the kit is completed.
