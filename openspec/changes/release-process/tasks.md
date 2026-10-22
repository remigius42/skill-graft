# Tasks

## 1. CI

- [ ] 1.1 In `.github/workflows/ci.yml`, add `release/**` to the push branches, and in the commitlint step set `FROM`
  to `git merge-base origin/main "$TO"` when `git cat-file -e "$FROM^{commit}"` fails; verify, in a scratch clone with
  `origin/main` behind a branch, that the step's shell lints the branch's commits for an all-zero `FROM` and for one
  the clone lacks, and keeps a valid `FROM`, and that pre-commit is green

## 2. Documentation

- [ ] 2.1 Add `## Releasing` to `CONTRIBUTING.md` as design.md decides: picking the version from the changelog's
  sections, the `release/v<version>` branch, the release commit's edits, pushing the branch and waiting for its CI
  run before `main` is fast-forwarded and pushed, what to do when CI fails or `main` moved, the annotated tag, the
  GitHub release with that version's section as notes, and deleting the branch; verify `gh release create --help`
  lists every flag used, that the notes-extraction command, run on a scratch changelog holding two versions with link
  definitions, prints exactly the asked section for both the newer and the oldest version, and that pre-commit is
  green; add new words to `.cspell.yaml`
- [ ] 2.2 Add to `AGENTS.md` (Git) that a release is the one branch outside OpenSpec, `release/v<version>`, following
  `CONTRIBUTING.md`'s Releasing; verify the link resolves and pre-commit is green
- [ ] 2.3 Add to `README.md` Installation one sentence on installing a release by appending `@v<version>` to the git
  URL, linking the repository's releases page; verify the link resolves and pre-commit is green

## 3. Release 0.1.0

- [ ] 3.1 Make the release commit `chore(release): 0.1.0` by the documented steps (on this change's branch in place of
  `release/v0.1.0`): `## [Unreleased]` becomes `## [0.1.0] - <today>` under a new empty `## [Unreleased]`, with the
  `[Unreleased]` compare and `[0.1.0]` tag link definitions; verify `pyproject.toml` and `uv.lock` already say
  `0.1.0` (`uv lock --check`), that no entry changed, and that pre-commit is green
- [ ] 3.2 Once the user confirms each push: push this branch as `release/v0.1.0`, wait for its CI run to be green,
  fast-forward `main` to the release commit and push it, tag the release commit `v0.1.0` (annotated), push the tag,
  publish the GitHub release by the documented command, and delete the remote `release/v0.1.0`; verify the branch's
  CI run passed both jobs, `git ls-remote origin 'refs/tags/v0.1.0^{}'` names the release commit,
  `gh release view v0.1.0` shows the `[0.1.0]` section as notes without link definitions, both changelog links
  resolve, and the README's install line with `@v0.1.0` installs into a temporary `UV_TOOL_DIR` and `UV_TOOL_BIN_DIR`
  whose `skill-graft --help` runs
