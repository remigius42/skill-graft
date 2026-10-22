# Tasks

## 1. CI

- [ ] 1.1 In `.github/workflows/ci.yml`, add a top-level `permissions: contents: read` and pin each `uses:` to the
  full commit SHA its tag names, the tag in a trailing comment; verify each SHA equals
  `gh api repos/<owner>/<repo>/commits/<tag> --jq .sha`, that no `uses:` is left on a tag, and that pre-commit is
  green

## 2. Changelog

- [ ] 2.1 Write `CHANGELOG.md` in Keep a Changelog 1.1.0 form with Semantic Versioning, all entries under
  `[Unreleased]`, seeded from the archived OpenSpec changes as design.md decides; verify each entry against the
  README and `openspec/specs/`, that each says what a user sees rather than which change brought it, and that
  pre-commit is green; add new words to `.cspell.yaml`
- [ ] 2.2 Add to `AGENTS.md` (Workflow) that a commit changing what a user sees adds its `CHANGELOG.md` entry under
  `[Unreleased]`, for an OpenSpec change in its archive commit; verify pre-commit is green

## 3. README and contributing

- [ ] 3.1 `git mv docs/development.md CONTRIBUTING.md`; add the OpenSpec loop and the links to `AGENTS.md` and
  `CONTEXT.md`; replace its hook list with a summary by purpose naming `.pre-commit-config.yaml`; fix its relative
  links for the new location, and point the README's `## Development` link at it; add new words to `.cspell.yaml`;
  commit, then verify the setup steps in a fresh clone of that commit (`git clone --branch feat/opsx-project-hygiene`
  of this repository into a temporary folder, `uv sync`, both `pre-commit install` lines,
  `uv run pre-commit run --all-files`), amending the commit if they fail; verify that no file outside
  `openspec/changes/` names `docs/development.md`, and that pre-commit is green
- [ ] 3.2 Restructure `README.md` as design.md orders it: copyright line, `## Installation` moved up, a new
  `## Usage`, `## Contributing` replacing `## Development`, lines 17 and 18 rejoined; verify the Usage scenario runs
  as written with `HOME` at a temporary folder holding an empty `.claude/` and `apm` 0.33.0 from the dev group,
  that every link resolves, and that pre-commit is green; add new words to `.cspell.yaml`
