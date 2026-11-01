# Tasks

Apply with the `mp-tdd` skill: each task red-green-refactor where it changes code, one commit.
`pre-commit run --all-files` stays green, and every commit passes `pytest`.

## 1. Measure APM 0.35.0

- [x] 1.1 Re-run every behavior `docs/design.md` lists under "Measured APM behavior" with APM 0.35.0, at user scope
  (`apm install -g -t claude`) and project scope (`apm install ./.apm/skill-graft`), `HOME` a scratch directory, by a
  script kept out of the repository. Rewrite the section for 0.35.0, naming each behavior that differs from 0.33.0 as
  such; the **Hidden character** classes line (`content_scanner.py`, byte-identical) says 0.35.0 too. Verify: each
  bullet of the section was run and holds as written. If a behavior skill-graft relies on changed, stop: the proposal,
  specs and tasks gain it before 2.1
- [ ] 1.2 Re-run the per-target deploy measurement for all 21 targets at both scopes with 0.35.0, and record in
  `docs/design.md`'s section where each group of targets deploys, the explicit-only targets apart from `--target all`.
  Verify: the folders are `DEPLOY_FOLDERS` and `PROJECT_DEPLOY_FOLDERS` plus `agent-data/workflows`, which only
  `grok-bot` (explicit-only, not in `--target all`) deploys to; `openclaw` deploys nothing without `~/.openclaw`; the
  bullet on every target says which set of targets it means

## 2. Require APM 0.35.0

- [ ] 2.1 `scripts/check_pins.py`: the README's APM version, in its requirement and each `apm-cli==` of its install
  line, pairs with `apm-cli==` in the dev group of `pyproject.toml`; the `check-pins` hook's `files:` in
  `.pre-commit-config.yaml` gains `README.md`; CONTRIBUTING's Tooling list names the pair. Tests in
  `tests/test_check_pins.py`: the synthetic repository gains a README, and a README version that differs fails naming
  both. Verify red, then green; `check-pins` passes on the repository at 0.33.0
- [ ] 2.2 `apm-cli==0.35.0` in the dev group of `pyproject.toml`, then `uv lock`; the README's requirement and install
  line, `docs/security.md`, ADR 0003, and the comments in `infra/paths.py`, `pipeline/hidden.py`, `tests/conftest.py`
  and `tests/cli/test_integration.py` say 0.35.0. Verify: `git grep -n "0\.33" -- ':!CHANGELOG.md' ':!openspec/changes'`
  finds nothing but `docs/design.md`'s notes, of 1.1, of a behavior that differs from 0.33.0; `pytest` passes with the 3
  APM integration tests run, not skipped; `check-pins` passes

## 3. Grok Bot's deploy folder

- [ ] 3.1 `infra/paths.py`: `agent-data/workflows` last in `DEPLOY_FOLDERS` and `PROJECT_DEPLOY_FOLDERS`, its comment
  naming `grok-bot`. Tests: `("~/agent-data/workflows", "agent-data/workflows")` joins
  `test_source_overlapping_a_deploy_folder_warns` in `tests/pipeline/test_config.py`;
  `test_project_scope_warns_of_a_source_overlapping_its_deploy_folder` is parametrized over the source folder and the
  deploy folder it overlaps (`.claude` and `.claude/skills`, `agent-data/workflows` for both), the folder it creates and
  the warning it expects taken from them; a project-scope source `path = "../../agent-data/workflows"`, relative to the
  **Package**, warns naming `<project>/agent-data/workflows`; `test_project_deploy_folders_include_the_user_scopes` in
  `tests/infra/test_paths.py` lists `project / "agent-data/workflows"`. Verify red, then green
