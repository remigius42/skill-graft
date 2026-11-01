# Proposal

## Why

skill-graft is built and documented against APM 0.33.0: the README requires it, the deploy folders and the **Hidden
character** classes are copied from it, and `docs/design.md` records its measured behavior. APM 0.35.0 is out
(Dependabot PR #6), and a user installing the current APM runs a version skill-graft has not been checked against.
Compared on 2026-11-01, 0.35.0 differs in one thing skill-graft copies: a new target, `grok-bot`, deploys skills to
`agent-data/workflows/`, a folder the overlap warning does not know.

## What Changes

- skill-graft requires APM 0.35.0: the README's requirement and install line, and the dev group's `apm-cli` pin, name
  it.
- A path **Source** inside or containing `agent-data/workflows`, under the home folder or, in project scope, under the
  project root, gets the warning that it overlaps a folder where APM deploys skills, as the other harness folders do.
- Every APM behavior `docs/design.md` records as measured is measured again with 0.35.0; the document, ADR 0003,
  `docs/security.md` and the code comments that cite 0.33.0 say 0.35.0. A measured behavior that changed is named in
  `design.md`, and becomes a task of this change if skill-graft relies on it.
- `check-pins` pairs the README's APM version with the dev group's `apm-cli` pin, so a Dependabot bump of one fails
  until the other follows.
- Dependabot PR #6 closes by itself once main carries 0.35.0; until then it is left alone. Main never holds the pair
  without the bump, so #6 does not turn red on it.

Not in scope: `openclaw`, which deployed nothing in either version without an existing `~/.openclaw`; its folder stays
as it is.

## Capabilities

### New Capabilities

### Modified Capabilities

- `config`: **Sources stay clear of the package and deploy folders** names `agent-data/workflows` among the deploy
  folders, under the home folder and the project root.

## Impact

- `src/skill_graft/infra/paths.py`: `agent-data/workflows` in `DEPLOY_FOLDERS` and `PROJECT_DEPLOY_FOLDERS`; the
  comments say 0.35.0.
- `src/skill_graft/pipeline/hidden.py`: the comment says 0.35.0 (`content_scanner.py` is identical).
- `pyproject.toml` and `uv.lock`: `apm-cli==0.35.0`.
- `scripts/check_pins.py`, `tests/test_check_pins.py`, `.pre-commit-config.yaml` (`check-pins` reads `README.md`),
  `CONTRIBUTING.md`: the README/`apm-cli` pair.
- Tests: `tests/infra/test_paths.py` (the project deploy folders), `tests/pipeline/test_config.py` (the warning for
  `agent-data/workflows`); the APM comments in `tests/conftest.py` and `tests/cli/test_integration.py`.
- `README.md`, `docs/design.md`, `docs/security.md`, `docs/adr/0003-drive-apm-never-edit-its-manifest.md`;
  `CHANGELOG.md` at archive.
