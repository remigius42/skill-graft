# Mutation testing

Two harnesses, both opt-in, so no hook or CI job runs either: `mutation/` mutates the tokens of the security-relevant
regexes and fails on a survivor; mutmut mutates the rest of `src/skill_graft/` and only reports.

## The regex harness

`uv run python -m mutation [target…]`, from the repository root, mutates each security-relevant regex: the **Vet**'s,
**Reference** finding, the `name:` comment, `skill-graft.toml` names and URLs, the URLs `tree` links to, the **Hidden
character** classes ([mutation/targets.py](../mutation/targets.py)). For each mutant, one token changed, it runs the
tests of the modules holding the pattern, on one process per CPU, and exits 1 on a mutant no test kills, unless
[mutation/equivalent.toml](../mutation/equivalent.toml) lists it with the reason it cannot change behavior, and on a
listed one that no longer survives or exists. It takes minutes; run it after changing a target pattern, then kill each
survivor with a test in its module's test file, or list it. With no target it runs them all; a target is named as in
`targets.py`, such as `config.NAME` or `vet._PATTERNS:send.url`.

## mutmut

`nice -n 19 ionice -c 3 uv run mutmut run`, from the repository root, mutates every function in `src/skill_graft/`
(`[tool.mutmut]` in `pyproject.toml`) and runs the tests that reach each mutant, in a copy of the repository in
`mutants/`; `nice` and `ionice` keep its one process per CPU from freezing the machine. A full run takes about an hour
on 8 CPUs; `uv run mutmut run "skill_graft.pipeline.lock*"` runs one module's mutants in a few minutes, and a rerun
skips functions that did not change. Run one at a time per checkout: two share `mutants/`. It forks, so it runs on Linux
and macOS only. `uv run mutmut results` lists the survivors, `uv run mutmut show <mutant>` prints one's diff. Read the
survivors after changing a module, and kill each with a test in the module's test file. Three kinds are known noise, not
gaps: a message's wording (`cli.py`'s help texts sit in the module-level `_TEXT`, which mutmut never mutates), a change
mypy would refuse, which the hooks keep from landing, and code that runs only at import, such as `vet._commands`, which
no test reaches with a mutant switched on. A mutant that cannot change behavior: first remove what it shows redundant,
or restructure so none exists, or name the value in a module-level constant; else put the equivalent expression alone on
a line of its own with a bare `# pragma: no mutate`, and `# Equivalent mutants: <reason>` in a comment above. A pragma
silences every mutant on its line, killed ones too, so never on a line holding anything else, and no `start` … `end`
regions. On an argument's line it also silences the call's mutants, each argument dropped or `None`, though not the
other lines' own: name the argument's value first, and mark that line instead. The `linear_time` tests are left out:
their wall-clock limit misses under load, and the regex harness times them.

The baseline to beat, 8097 mutants with the change `mutmut-src` (2026-11-07): 7532 killed, 5 timed out, 560 survived;
202 survive since the change `mutmut-cli`. `pipeline` is from its rerun after the change `mutmut-src`; `infra` from its
rerun with the change `mutmut-infra`; `commands` from its rerun, 2261 mutants, with the change `mutmut-commands`; `cli`
from its rerun, 845 mutants, with the change `mutmut-cli`. Survivors per layer:

| Layer      | Survivors | Of which                                                                       |
| ---------- | --------: | ------------------------------------------------------------------------------ |
| `cli`      |        48 | all known noise: 34 usage wording in `_parser`, message wording, mypy refusals |
| `commands` |        65 | all known noise: message wording, mypy refusals, import-time code              |
| `infra`    |        38 | all known noise: message wording, mypy refusals                                |
| `pipeline` |        51 | all known noise: message wording, mypy refusals, import-time code              |
