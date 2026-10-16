# Tasks

Each task: failing test first, then code, one commit, `pre-commit run --all-files` green.

## 1. Packaging

- [x] 1.1 Add `[project]` (Python >=3.11, no runtime deps, `uv_build`, script `skill-graft`), dev group
  (`pytest`, `pre-commit`, `apm-cli==0.33.0`), `src/skill_graft/cli.py` with `init`/`build` stubs, `uv.lock`;
  drop `requirements-dev.txt`; update `docs/development.md` to `uv sync`/`uv run`; add the local pytest hook
  and `pytest` to mypy's additional dependencies; set `mypy_path = "src"`. Verify: a test running
  `skill-graft --help` passes under `uv run pytest`.
- [x] 1.2 Add a `HOME`-to-`tmp_path` autouse fixture and the fake `apm` fixture in `tests/conftest.py`. Verify:
  a test asserts `Path.home()` is under `tmp_path` and the fake records argv and exit code.

## 2. Config

- [x] 2.1 Load `skill-graft.toml`: path sources (`~` and relative resolution, missing folder) and entries
  (malformed, undeclared alias). Verify: tests for each `config` scenario pass.
- [x] 2.2 Reject unsupported keys (top-level and per source) and a missing or invalid file. Verify: tests for
  git source, `[rename]`, and not-initialized scenarios pass.
- [ ] 2.3 Validate value types, aliases as one path segment, and repeated entries. Verify: entries-as-string,
  empty source, path-not-a-string, bad alias and repeated-entry scenario tests pass.
- [ ] 2.4 Error on sources inside or containing `~/.apm/skill-graft/`; warn on deploy-folder overlap. Verify:
  source-is-the-package and source-is-a-deploy-folder scenario tests pass.

## 3. Skill discovery

- [ ] 3.1 Walk a source: any depth, hidden folders, symlinked folders once each, prune `.git`, stop inside a
  skill. Verify: nested, skill-in-skill, symlinked-folder, symlink-cycle and `.git` scenario tests pass.
- [ ] 3.2 Name from front matter `name:` (BOM, fence whitespace, quotes, trailing comment handled; unsupported
  forms an error) else folder. Verify: name, comment-and-quotes and unsupported-form scenario tests pass.
- [ ] 3.3 Resolve entries: unknown, duplicate and non-segment names are errors only for the skill an entry
  names. Verify: duplicate, not-found and traversal scenario tests pass.

## 4. Build

- [ ] 4.1 `build --no-install`: clash check, then copy entries into `skills.new/` (no `.git`) and swap it in.
  Verify: whole-folder, removed-entry, copy-fails, clash and no-install scenario tests pass, and `apm` is
  never called.
- [ ] 4.2 Run `apm install -g <absolute path>` and check `~/.apm/apm.yml` lists the package (`- x` or
  `- path: x`, `~` or absolute, compared resolved). Verify: fake-`apm` tests for success, registration removed
  by hand, symlinked home, non-zero exit, not registered, and `apm` missing pass.

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
