# Proposal

## Why

`commands/explain.py` imports `resolve` (for `resolve.load`) and `commands/resolve.py` imports `explain` (for
`explain.show`): a cycle `scope-passed-down` introduced and two `/code-review` runs and an `openspec verify` flagged.
The layers contract only orders layers, not the modules inside one, so nothing refuses this cycle or the next. A trial
`acyclic_siblings` contract over `skill_graft` finds a second one, type-only: `pipeline/patch.py` imports `Hull` under
`TYPE_CHECKING` for `PatchError.hull`, and `pipeline/hull.py` imports `patch`.

## What Changes

- `commands/resolve.py` splits along the seam its docstring names: the shared core every command that writes the lock
  uses (`load`, `Resolution`, `resolving`, `_restore`) moves to a new `commands/transaction.py`; `resolve.py` keeps the
  `resolve` command. `explain`, `edit`, `build` and `update` import `transaction` for the core; `resolve` imports
  `transaction` and `explain`. Nothing in `commands` imports `resolve` then.
- `PatchError` moves from `pipeline/patch.py` to `pipeline/hull.py`, the only module raising it; `patch.py` drops its
  `TYPE_CHECKING` import of `Hull`. `explain` and `update` import it from `pipeline.hull` and drop their
  `pipeline.patch` import, which they use only for it.
- A new import-linter contract, `acyclic_siblings` over `skill_graft`: no import cycle between sibling modules or
  packages in any layer, at any depth, type-only imports included. The dev dependency becomes `import-linter>=2.15`, the
  version verified to ship it.
- `AGENTS.md` and the `lint-imports` hook comment name the new rule.

No user-visible change: every output, file and exit code stays byte for byte. No CHANGELOG entry.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None: a refactor (`skip_specs: true`).

## Impact

- `src/skill_graft/commands/`: new `transaction.py`; `resolve.py`, `explain.py`, `edit.py`, `build.py`, `update.py`.
- `src/skill_graft/pipeline/patch.py`, `hull.py`.
- `tests/commands/`: the tests of the core (`resolving`, its writes and restores) move from `test_resolve.py` to a new
  `test_transaction.py`; `cli`-driven tests unchanged.
- `pyproject.toml` (contract, dependency floor), `uv.lock` (the new specifier), `.pre-commit-config.yaml` (comment),
  `AGENTS.md`.
