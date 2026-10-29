# Proposal

## Why

`CHANGELOG.md` collects every change a user sees under `[Unreleased]`, but nothing says how those entries become a
release, and no version is tagged: a user installing from git gets whatever `main` is, with no version to pin or compare
against. Writing the steps down before the first release makes `0.1.0` the first run of them, not an improvisation the
next release cannot repeat.

## What Changes

- `CONTRIBUTING.md` gains `## Releasing`: the version to pick (Semantic Versioning, a breaking change before 1.0 raising
  the minor version), the release commit (`chore(release): <version>`, which moves `[Unreleased]` to a dated version
  heading, opens an empty `[Unreleased]`, adds the compare and tag link definitions, and sets the version in
  `pyproject.toml` and `uv.lock`), CI on the pushed `release/v<version>` branch before `main` is fast-forwarded, the
  annotated tag `v<version>` on that commit, and a GitHub release whose notes are that version's changelog section.
- `.github/workflows/ci.yml`: CI also runs on pushes to `release/**`, and the commitlint job, given a `before` that is
  no commit in the clone (a new branch, or a branch rewritten by a rebase), lints from the merge-base with `main`.
- `AGENTS.md` (Git): a release is the one branch outside OpenSpec, `release/v<version>`, done as `CONTRIBUTING.md` says.
- `README.md` Installation: one sentence on installing a tagged release (`…/skill-graft@v<version>`), pointing to the
  repository's releases, so the README needs no edit per release.
- `0.1.0` is cut by those steps: the changelog's current `[Unreleased]` becomes `[0.1.0]`, tagged `v0.1.0` and published
  as a GitHub release. `pyproject.toml` already says `0.1.0`.

No behavior changes: same commands, output, config and lock.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None: process and documentation only (`skip_specs: true`).

## Impact

- `.github/workflows/ci.yml`, `CONTRIBUTING.md`, `AGENTS.md`, `README.md`, `CHANGELOG.md`; a branch `release/v0.1.0`, a
  tag `v0.1.0` and a GitHub release on `remigius42/skill-graft`; `.cspell.yaml` for new words.
- No code, test or dependency change. Out of scope: pull requests, publishing to PyPI, release automation
  (release-please, tag-triggered workflows), Dependabot, and a `--version` flag.
