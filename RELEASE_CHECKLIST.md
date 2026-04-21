# Release Checklist

Use this before tagging a new release.

## Version

- Update `VERSION`
- Update `CHANGELOG.md`
- Confirm `CITATION.cff` and `.claude-plugin/plugin.json` still match the release version

## Validation

- Run the CI checks locally if possible
- Confirm the Python scripts still compile
- Review the README for any stale examples or paths

## Tagging

- Create the release tag as `vX.Y.Z`
- Make sure the tag matches the contents of `VERSION`
- Push the tag to trigger the release workflow

## After release

- Confirm the GitHub release was created
- Verify the release notes look correct
- Update any downstream references if needed
