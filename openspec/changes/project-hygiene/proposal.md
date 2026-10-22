# Proposal

## Why

skill-graft is public and builds agent skills from other people's repositories, but a reader finds no record of what
changed. The README explains why the tool exists and documents every command, yet shows no single path from install
to a deployed skill, names no copyright holder, and says nothing about reporting a bug or what response to expect;
its setup guide sits in `docs/development.md`, where GitHub does not point contributors. The CI workflow runs with
the default token permissions and takes its actions by movable tags. The sibling repositories `chisel_skill` and
`claude-usage-monitor` already keep a changelog and a contributing guide.

## What Changes

- `.github/workflows/ci.yml`: a top-level `permissions: contents: read`, and every `uses:` pinned to a full commit
  SHA with its tag in a trailing comment (`# v7.0.1`).
- `CHANGELOG.md`, hand-written in the Keep a Changelog 1.1.0 format with Semantic Versioning, as in the sibling
  repositories. No version has been released, so every entry sits under `[Unreleased]`, seeded from the archived
  OpenSpec changes: one entry per change a user can notice; refactors and internal tooling get none.
- `AGENTS.md`: a commit that changes what a user sees adds its entry under `[Unreleased]`; for an OpenSpec change,
  the archive commit.
- `docs/development.md` moves to `CONTRIBUTING.md`, keeping its setup, checks and evals, and gains the OpenSpec
  workflow in short, a pointer to `AGENTS.md` and `CONTEXT.md` for the rules, and a hook summary that names
  `.pre-commit-config.yaml` as the full list instead of its partial one.
- `README.md`, toward the four parts of a README (identification, evaluation, usage, engagement):
  - a copyright line under the title, as in `claude-cloud-test`;
  - `## Installation` moved up, followed by a new `## Usage`: one scenario from a fresh install to deployed skills,
    with its prerequisites, before the command and config reference;
  - `## Development` replaced by `## Contributing` at the end: GitHub issues for bugs and ideas, `CONTRIBUTING.md`
    for code, and `claude-cloud-test`'s note on best-effort maintenance;
  - the sentence broken across lines 17 and 18 rejoined.

No behavior changes: same commands, output, config and lock.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None: tooling and documentation only (`skip_specs: true`).

## Impact

- `.github/workflows/ci.yml`; new `CHANGELOG.md`; `docs/development.md` moved to `CONTRIBUTING.md`; `AGENTS.md`;
  `README.md`; `.cspell.yaml` for new words. Archived changes that name `docs/development.md` stay as written.
- No code, test, dependency or pre-commit change. Pinned SHAs move only when edited: automated updates (Dependabot)
  are out of scope, as are a release, a version tag, issue templates and `SECURITY.md`.
