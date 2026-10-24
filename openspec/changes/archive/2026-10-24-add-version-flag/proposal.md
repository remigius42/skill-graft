# Proposal

## Why

skill-graft has no way to say which version is installed. The README installs the latest `main`, whose version stays
the last release's until the next one, so a bug report cannot name the code it ran; the bug template asks for a tag or
commit the user has to dig up.

## What Changes

- `skill-graft --version` prints `skill-graft <version>` and exits 0, without reading `skill-graft.toml`.
- Installed from git, it adds the commit installed, `skill-graft 0.2.0 (e294a0e)`, and the revision if one was asked
  for: `skill-graft 0.2.0 (main @ e294a0e)`. Installed otherwise, from a folder, an archive or editable, it prints the
  version only.
- The bug template asks for the output of `skill-graft --version` instead of a tag or commit.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cli`: a new requirement for `--version`; the help lists it.

## Impact

- `src/skill_graft/cli.py`: the option and what it prints, from `importlib.metadata` and the `direct_url.json` the
  installer writes (PEP 610). No new dependency, no `git` call.
- Tests in `tests/cli/test_cli.py`.
- `.github/ISSUE_TEMPLATE/bug_report.md`, `README.md`.
- `CHANGELOG.md` entry at archive.
