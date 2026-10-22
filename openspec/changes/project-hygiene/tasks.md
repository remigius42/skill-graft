# Tasks

## 1. CI

- [ ] 1.1 In `.github/workflows/ci.yml`, add a top-level `permissions: contents: read` and pin each `uses:` to the
  full commit SHA its tag names, the tag in a trailing comment; verify each SHA equals
  `gh api repos/<owner>/<repo>/commits/<tag> --jq .sha`, that no `uses:` is left on a tag, and that pre-commit is
  green

## 2. Changelog

- [ ] 2.1 Write `CHANGELOG.md` in Keep a Changelog 1.1.0 form with Semantic Versioning, all entries under
  `[Unreleased]`, seeded from the archived OpenSpec changes as design.md decides; verify each entry against the
  README and `openspec/specs/`, that no entry names an OpenSpec change, and that pre-commit is green
- [ ] 2.2 Add to `AGENTS.md` (Workflow) that archiving a change a user can notice adds its `CHANGELOG.md` entry
  under `[Unreleased]` in the archive commit; verify pre-commit is green

## 3. README and contributing

- [ ] 3.1 `git mv docs/development.md CONTRIBUTING.md`; add the OpenSpec loop, the links to `AGENTS.md` and
  `CONTEXT.md`, and `lint-imports` to its hook list; fix its relative links for the new location, and point the
  README's `## Development` link at it; verify its setup
  steps in a fresh clone (`git clone` of this repository into a temporary folder, `uv sync`, both
  `pre-commit install` lines, `uv run pre-commit run --all-files`), that no file outside `openspec/changes/archive/`
  names `docs/development.md`, and that pre-commit is green
- [ ] 3.2 Restructure `README.md` as design.md orders it: copyright line, `## Installation` moved up, a new
  `## Usage`, `## Contributing` replacing `## Development`, lines 17 and 18 rejoined; verify the Usage scenario runs
  as written with `HOME` at a temporary folder and `apm` 0.33.0 from the dev group, that every link resolves, and
  that pre-commit is green; add new words to `.cspell.yaml`
