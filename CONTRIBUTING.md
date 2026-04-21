# Contributing

Thanks for improving the results-db skill.

## What to change

- Keep the core skill focused on empirical results ledgers
- Prefer portable paths and project-relative defaults
- Keep the schema stable unless a change is clearly worth the migration cost
- Add or update documentation when behavior changes

## Before you submit a change

- Run a syntax check on any edited Python files
- Verify that README examples still match the scripts
- Keep new examples generic unless they are explicitly labeled as project-specific
- Make sure generated files are not committed unless they are meant to ship

## Release policy

- Update `VERSION` and `CHANGELOG.md` together for any release
- Use semantic version tags in the form `vX.Y.Z`
- Do not cut a release tag unless the tag matches the contents of `VERSION`
- Keep `CITATION.cff` and `.claude-plugin/plugin.json` aligned with the released version

## Good contribution areas

- Better examples for `populate_example.py`
- Additional validation checks in `results_db.py`
- More concise documentation and onboarding material
- Small portability improvements

## Style

- Be concise
- Prefer plain language over jargon
- Keep examples copyable
- Avoid hardcoding local machine paths
