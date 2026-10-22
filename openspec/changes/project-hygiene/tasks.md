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

## 3. Contributing

- [ ] 3.1 Add the `## Engagement` section to the end of `README.md`, worded as design.md quotes; verify pre-commit is
  green
- [ ] 3.2 Write `CONTRIBUTING.md` as design.md describes, linking `AGENTS.md`, `CONTEXT.md`, `evals/` and the
  README's `## Engagement`; verify its setup steps in a fresh clone (`git clone` of this repository into a temporary
  folder, `uv sync`, the `pre-commit install` line, `uv run pre-commit run --all-files`), and that pre-commit is
  green; add new words to `.cspell.yaml`
