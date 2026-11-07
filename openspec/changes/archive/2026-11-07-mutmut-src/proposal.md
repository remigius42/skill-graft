# Proposal

## Why

Line coverage is about 98 %, yet a mutmut spike over `src/skill_graft/` left 1 084 of 8 380 mutants alive: no test
notices `lock.recorded`'s `or` turned `and`, or `cache` passing `--VERIFY` to git. The regex harness, `mutation/`,
covers only the security-relevant patterns; nothing measures how tightly the tests pin down the rest of the code.
`linear-regexes` left mutmut "for a later decision": this is it.

## What Changes

- mutmut, a dev dependency, mutates all of `src/skill_graft/`, configured under `[tool.mutmut]` in `pyproject.toml` and
  run as `nice -n 19 ionice -c 3 uv run mutmut run`, from the repository root, one run at a time. Opt-in: no hook or CI
  job runs it; a full run takes about an hour and forks, so it runs on Linux and macOS only. It reports and never fails
  a build.
- `mutation/` stays as it is: it mutates regex tokens, which mutmut does not; the two overlap only shallowly.
- Message wording is not tested: `cli._parser`'s help texts sit in a module-level table, `_TEXT`, which mutmut never
  mutates. Mutants of other message strings, mutants mypy would refuse and code run only at import are known noise in
  the report.
- A mutant that cannot change behavior is removed by simplifying or restructuring the code, or by naming its value in a
  module-level constant; else the equivalent expression goes alone on a line with a bare `# pragma: no mutate`, its
  reason in a comment above.
- Every surviving mutant in `pipeline/` is killed by a test in its module's test file, marked equivalent, or is known
  noise. `infra/`, `commands/` and `cli/` follow, one change each.
- `CONTRIBUTING.md`'s Mutation testing section says which harness covers what, how to run mutmut, and the survivors per
  layer as the baseline to beat; `AGENTS.md` and `docs/README.md` gain a line each.
- A survivor that turns out to be a bug is fixed in this change, with a scenario where a spec covers the behavior, and a
  `Fixed` entry in the archive commit.

## Capabilities

### New Capabilities

None: mutation testing binds the tests, not what a user sees.

### Modified Capabilities

None up front (`skip_specs: true`). A survivor that proves a bug in specified behavior adds its delta spec when found.

## Impact

- `pyproject.toml`: `mutmut` in the `dev` group, `[tool.mutmut]`, `mutants/` excluded from mypy; `uv.lock`.
- `.gitignore`: `mutants/`.
- `src/skill_graft/cli.py`: help texts in `_TEXT`; `src/skill_graft/pipeline/*.py`: code simplified or restructured, or
  a pragma, where a mutant is equivalent, and fixes for any survivor that is a bug.
- `tests/pipeline/test_*.py`, `tests/cli/test_cli.py`: tests killing the survivors of `pipeline/` and `cli._parser`.
- `CHANGELOG.md`: a `Fixed` entry per bug found, at archive.
- `CONTRIBUTING.md`, `AGENTS.md`, `docs/README.md`, `.cspell.yaml`.
- No runtime dependency; mutmut pulls in `libcst` and others, dev only.
