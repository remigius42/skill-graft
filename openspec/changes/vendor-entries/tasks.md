# Tasks

Each task: failing test first, then code, one commit, `pre-commit run --all-files` green.

## 1. Packaging

- [ ] 1.1 Add `[project]` (Python >=3.11, no runtime deps, `uv_build`, script `skill-graft`), dev group
  (`pytest`, `pre-commit`, `apm-cli==0.33.0`), `src/skill_graft/cli.py` with `init`/`build` stubs, `uv.lock`;
  drop `requirements-dev.txt`; update `docs/development.md` to `uv sync`/`uv run`; add the local pytest hook
  and `pytest` to mypy's additional dependencies. Verify: a test running `skill-graft --help` passes under
  `uv run pytest`.
- [ ] 1.2 Add a `HOME`-to-`tmp_path` autouse fixture and the fake `apm` fixture in `tests/conftest.py`. Verify:
  a test asserts `Path.home()` is under `tmp_path` and the fake records argv and exit code.

## 2. Config

- [ ] 2.1 Load `skill-graft.toml`: path sources (`~` and relative resolution, missing folder) and entries
  (malformed, undeclared alias). Verify: tests for each `config` scenario pass.
- [ ] 2.2 Reject unsupported keys (top-level and per source) and a missing or invalid file. Verify: tests for
  git source, `[rename]`, and not-initialized scenarios pass.

## 3. Skill discovery

- [ ] 3.1 Walk a source: any depth, hidden folders, prune `.git`, stop inside a skill. Verify: nested,
  skill-in-skill and `.git` scenario tests pass.
- [ ] 3.2 Name from front matter `name:` (quotes stripped) else folder; resolve entries, with duplicate and
  unknown errors. Verify: name, duplicate and not-found scenario tests pass.

## 4. Build

- [ ] 4.1 `build --no-install`: clash check, then rewrite `.apm/skills/` with whole-folder copies (no `.git`).
  Verify: whole-folder, removed-entry, clash and no-install scenario tests pass, and `apm` is never called.
- [ ] 4.2 Run `apm install -g` and check `~/.apm/apm.yml` lists the package (`~` or absolute). Verify:
  fake-`apm` tests for success, non-zero exit, not registered, and `apm` missing pass.

## 5. Init

- [ ] 5.1 `init`: refuse an existing folder, write the commented TOML and two-line `apm.yml`, run
  `apm install -g <abs path>`, check registration, print the retry command on failure. Verify: every `init`
  scenario passes with the fake `apm`.

## 6. Integration

- [ ] 6.1 Real-APM test: `init`, add a fixture path source and entry, `build`; assert exit 0, `~/.apm/apm.yml`
  lists the package, the skill is deployed under the temp `HOME`. Skipped without `apm` on `PATH`. Verify:
  passes under `uv run pytest`.
- [ ] 6.2 Update `README.md` status and `docs/design.md` "Measured APM behavior" with what design.md recorded;
  add new words to `.cspell.yaml`. Verify: `pre-commit run --all-files` green.
