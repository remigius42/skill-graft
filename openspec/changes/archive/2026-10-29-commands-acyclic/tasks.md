# Tasks

Apply with the `mp-tdd` skill: each task red-green-refactor, one commit. Every `main(...)`-driven test passes unchanged
at every commit. The cycles go before the contract, so every commit passes the hooks. No CHANGELOG entry.

Trial check used below: `lint-imports --config <tmp toml>` with only the contract of 3.1, its toml in a folder from
`mktemp -d`, never committed.

## 1. Break the commands cycle

- [x] 1.1 Create `commands/transaction.py` and move `load`, `Resolution`, `resolving` and `_restore` from `resolve.py`
  into it unchanged (docstring: the one place every command that writes the lock does it); `resolve.py` keeps the
  `resolve` command, importing `transaction` and `explain`, its docstring narrowed to the command; `explain._explain`
  calls `transaction.load`, `build` and `update` `transaction.load` and `transaction.resolving`, and `edit._finish`
  `transaction.resolving` only (it keeps parsing the edited, unwritten text; `load` would read the old file). Red: move
  the core's tests (`test_nothing_written_when_the_block_raises` through
  `test_hull_warnings_kept_though_the_lock_write_fails`) verbatim from `tests/commands/test_resolve.py` to a new
  `tests/commands/test_transaction.py`, calling `transaction.resolving`, with the local `scope` fixture and the
  `writing`, `recording` and `failing` helpers above them; they fail on the missing module, not on a missing fixture or
  helper. Green: they pass; `test_resolve.py` drops the imports its remaining tests no longer use (ruff) and its
  docstring's "the one place that resolves the hull and writes the lock", which `test_transaction.py`'s takes; `pytest`,
  `uv run mypy .` and `lint-imports` green; the trial check reports no cycle in `skill_graft.commands`

## 2. Break the pipeline cycle

- [x] 2.1 Move `PatchError` from `pipeline/patch.py` to `pipeline/hull.py`, below `class Hull`, unchanged but for
  `hull: Hull | None` unquoted; drop `patch.py`'s `TYPE_CHECKING` block; `hull.py` raises its own `PatchError`;
  `commands/explain.py` and `commands/update.py` import it from `skill_graft.pipeline.hull` and drop their
  `pipeline.patch` import, used only for `PatchError`. A pure move, no new test: the patch and hidden-character tests
  under `tests/cli/` already cover raising and catching it, and stay green before and after. Verify: `pytest`,
  `uv run mypy .` and `lint-imports` green; `grep -rn PatchError src/skill_graft/pipeline/patch.py` finds nothing; the
  trial check reports no cycle at all

## 3. Refuse the next cycle

- [x] 3.1 Add to `pyproject.toml` the contract `name = "No import cycle between sibling modules or packages"`,
  `type = "acyclic_siblings"`, `ancestors = ["skill_graft"]`; raise the dev dependency to `import-linter>=2.15` and
  `uv lock`, committing `uv.lock` (the version stays 2.15, but its dev requirements record the new specifier;
  `uv lock --check` passes); extend the `lint-imports` hook comment in `.pre-commit-config.yaml` (an import up a layer,
  or a cycle between siblings) and the layers bullet in `AGENTS.md` (siblings import each other one way only). Red:
  before the cycle fixes the contract fails (seen in the trial check on `main`: `.resolve -> .explain`,
  `.patch -> .hull`); here, add a temporary `from skill_graft.commands import resolve` to `explain.py` and see
  `lint-imports` refuse it, then remove it (`git diff src/` empty). Green: `pre-commit run --all-files` green (a hook
  config changed)

## 4. Before archiving

- [x] 4.1 Bring proposal, design and tasks in line with the code (module and test names, moved tests); verify
  `openspec validate commands-acyclic` passes
