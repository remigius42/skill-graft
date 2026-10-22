# Proposal

## Why

skill-graft is public and builds agent skills from other people's repositories, but a reader finds no record of what
changed, and a person who wants to work on it finds setup only in `AGENTS.md`, written for agents. Its CI workflow
also runs with the default token permissions and takes its actions by movable tags. The sibling repositories
`chisel_skill` and `claude-usage-monitor` already keep a changelog and a contributing guide.

## What Changes

- `.github/workflows/ci.yml`: a top-level `permissions: contents: read`, and every `uses:` pinned to a full commit
  SHA with its tag in a trailing comment (`# v7.0.1`).
- `CHANGELOG.md`, hand-written in the Keep a Changelog 1.1.0 format with Semantic Versioning, as in the sibling
  repositories. No version has been released, so every entry sits under `[Unreleased]`, seeded from the archived
  OpenSpec changes: one entry per change a user can notice; refactors and internal tooling get none.
- `AGENTS.md`: archiving a change a user can notice adds its entry under `[Unreleased]` in the same commit.
- `CONTRIBUTING.md`, for people: prerequisites, `uv sync`, `pre-commit install` (both hook types), the OpenSpec
  workflow in short, that evals are opt-in and billed, and a pointer to `AGENTS.md` and `CONTEXT.md` for the rules.
- `README.md`: an `## Engagement` section, worded as in `claude-cloud-test`: a personal project with best-effort
  maintenance, slow responses, and changes off its direction unlikely to merge. `CONTRIBUTING.md` links it.

No behavior changes: same commands, output, config and lock.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None: tooling and documentation only (`skip_specs: true`).

## Impact

- `.github/workflows/ci.yml`; new `CHANGELOG.md` and `CONTRIBUTING.md`; `AGENTS.md`; `README.md`; `.cspell.yaml` for
  new words.
- No code, test, dependency or pre-commit change. Pinned SHAs move only when edited: automated updates (Dependabot)
  are out of scope, as are a release, a version tag, issue templates and `SECURITY.md`.
