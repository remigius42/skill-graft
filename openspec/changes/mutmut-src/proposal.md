# Proposal

## Why

Line coverage is about 98 %, yet a mutmut spike over `src/skill_graft/` left 1 084 of 8 380 mutants alive: no test
notices `lock.recorded`'s `or` turned `and`, or `cache` passing `--VERIFY` to git. The regex harness, `mutation/`,
covers only the security-relevant patterns; nothing measures how tightly the tests pin down the rest of the code.
`linear-regexes` left mutmut "for a later decision": this is it.

## What Changes

- mutmut, a dev dependency, mutates all of `src/skill_graft/`, configured under `[tool.mutmut]` in `pyproject.toml` and
  run as `uv run mutmut run`, from the repository root. Opt-in: no hook or CI job runs it; a full run takes about two
  hours and forks, so it runs on Linux and macOS only. It reports and never fails a build.
- `mutation/` stays as it is: it mutates regex tokens, which mutmut does not; the two overlap only shallowly.
- Message wording is not tested: `cli._parser`, the help texts, sits in a `# pragma: no mutate` region; mutants of other
  message strings are known noise in the report.
- A mutant that cannot change behavior carries `# pragma: no mutate` on its line, with the reason after it.
- Every surviving mutant in `pipeline/` is killed by a test in its module's test file, marked equivalent, or is message
  wording. `infra/`, `commands/` and `cli/` follow, one change each.
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
- `src/skill_graft/cli.py`: one pragma on `_parser`; `src/skill_graft/pipeline/*.py`: pragmas on equivalent mutants
  only, and fixes for any survivor that is a bug.
- `tests/pipeline/test_*.py`: tests killing the `pipeline/` survivors.
- `CHANGELOG.md`: a `Fixed` entry per bug found, at archive.
- `CONTRIBUTING.md`, `AGENTS.md`, `docs/README.md`, `.cspell.yaml`.
- No runtime dependency; mutmut pulls in `libcst` and others, dev only.
