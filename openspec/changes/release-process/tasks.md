# Tasks

## 1. Documentation

- [ ] 1.1 Add `## Releasing` to `CONTRIBUTING.md` as design.md decides: picking the version from the changelog's
  sections, the `release/v<version>` branch, the release commit's edits, fast-forward and push, the annotated tag once
  CI is green, and the GitHub release with that version's section as notes; verify `gh release create --help` lists
  every flag used, that the notes-extraction command, run on a scratch changelog holding two versions, prints exactly
  the asked version's section, and that pre-commit is green; add new words to `.cspell.yaml`
- [ ] 1.2 Add to `README.md` Installation one sentence on installing a release by appending `@v<version>` to the git
  URL, linking the repository's releases page; verify the link resolves and pre-commit is green

## 2. Release 0.1.0

- [ ] 2.1 Make the release commit `chore(release): 0.1.0` by the documented steps (on this change's branch in place of
  `release/v0.1.0`): `## [Unreleased]` becomes `## [0.1.0] - <today>` under a new empty `## [Unreleased]`, with the
  `[Unreleased]` compare and `[0.1.0]` tag link definitions; verify `pyproject.toml` and `uv.lock` already say
  `0.1.0` (`uv lock --check`), that no entry changed, and that pre-commit is green
- [ ] 2.2 Once the user confirms each push: fast-forward `main` and push it, wait for its CI run to be green, tag the
  release commit `v0.1.0` (annotated), push the tag, and publish the GitHub release by the documented command; verify
  the tag peels to the release commit (`git ls-remote --tags origin v0.1.0`), `gh release view v0.1.0` shows the
  `[0.1.0]` section as notes, both changelog links resolve, and the README's install line with `@v0.1.0` installs into
  a temporary `UV_TOOL_DIR` and `UV_TOOL_BIN_DIR` whose `skill-graft --help` runs
