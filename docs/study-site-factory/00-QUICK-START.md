# Quick start

Follow these seven steps in order:

1. Copy kit: copy this factory kit into the new project workspace.
2. Add materials: place all course sources and available answer keys in the project input area.
3. Complete input: fill in `01-PROJECT-INPUT-TEMPLATE.md` and record all missing-answer decisions.
4. Edit config: copy and update `examples/project-config.example.json` as the project's configuration.
5. Run the master prompt: use the master build prompt with the completed input, configuration, and materials.
6. Review gate reports: resolve or explicitly retain every reported review item before continuing.
7. Deploy only after approval: deploy only when the human approval and final QA gate both pass.

## Start a new project

Use docs/study-site-factory/10-MASTER-BUILD-PROMPT.md.
Project input: input/PROJECT_INPUT.md
Configuration: input/project-config.json
Materials: input/materials/

Validate the completed kit with:

```powershell
python -B scripts/validate_factory_kit.py
```
