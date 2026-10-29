# Design

## Context

See proposal.md for why. Today:

- `commands/resolve.py` holds two things, as its docstring says: the `resolve` command (`resolve`: resolve, write the
  lock, then `explain.show`) and the core every lock-writing command shares: `load` (config plus its warnings),
  `Resolution`, `resolving` (hull, caller's writes, lock, restore on failure) and `_restore`. Callers of the core:
  `build`, `update`, `edit._finish`, and `explain._explain` (`load` only).
- `scope-passed-down` (task 1.3) chose on purpose: `show` lives in `explain`, its natural home, and `_explain` loads the
  config through `resolve.load`, so `commands` has one way to load the config. Both stay; the cycle is a by-product of
  where they sit, not of either choice.
- `pipeline/patch.py` defines `PatchError`, whose `hull` field is typed `Hull`, imported under `TYPE_CHECKING`. Only
  `pipeline/hull.py` raises it (three places); `commands/explain.py` and `commands/update.py` catch it, and `update`
  builds a new one in `_fetch_hint`. `hull.py` imports `patch` at run time for `apply` and `PatchFailed`.
- import-linter 2.15 (locked in `uv.lock`) ships `acyclic_siblings`: fields `ancestors` (module expressions), `depth`
  (default 10), `skip_descendants`, `ignore_imports`, `broken_contract_guidance`. For each ancestor it runs grimp's
  `nominate_cycle_breakers` over `find_children`, which returns modules and subpackages alike, then recurses into each
  child. A trial run with `ancestors = ["skill_graft"]` on `main` reports exactly two cycles: `commands`
  (`.resolve -> .explain`) and `pipeline` (`.patch -> .hull`), so it does cover plain modules. grimp counts
  `TYPE_CHECKING` imports unless `exclude_type_checking_imports` is set, which this project does not.

## Goals / Non-Goals

**Goals:**

- No import cycle between siblings anywhere under `skill_graft`, and `lint-imports` refusing the next one.
- Byte-identical stdout, stderr, files and exit codes: every `main(...)`-driven test passes unchanged.

**Non-Goals:**

- No renames of public functions or of `PatchError`; no change to what `show`, `load` or `resolving` do.
- `exclude_type_checking_imports` stays unset: the layers contract keeps seeing type-only imports.

## Decisions

- **Split `resolve.py` along its own seam; the core goes to `commands/transaction.py`.** `load`, `Resolution`,
  `resolving` and `_restore` move unchanged. The graph becomes `resolve → {transaction, explain}`,
  `explain → transaction`, `edit/build/update → transaction (+ explain)`: views and commands both sit above the core,
  and the core imports no view. The module is named for what `resolving` guarantees: the caller's writes and the lock
  land together or are all restored. Not `resolution.py`: every caller binds `as resolution:`, which would shadow the
  module. `load` goes with them although the name fits it less: it is how every user of the core starts (`explain`,
  `build`, `update`), and a module of its own for one three-line function buys nothing. Alternatives:

  - Move only `load` lower, leaving the core in `resolve.py`: the smallest diff (no test moves), but `resolve.py` keeps
    being both a command and the core every other command imports, the ambiguity that let `explain` import a command
    without anyone noticing. And no home fits: `commands/scope.py` is shadowed by every caller's `scope` parameter
    (`scope.load(...)` would hit the `Scope`), and a `pipeline.config` helper taking `warnings` would be the first
    `pipeline` function to fill a caller's warnings list.
  - `explain` calls `config.load` plus `warnings.extend` instead of `resolve.load`: one file, but undoes
    `scope-passed-down`'s "one way to load the config".
  - `resolve.resolve` returns the hull and `cli` calls `explain.show`: two lines, but puts a command's output in `cli`,
    against `commands-own-orchestration`.
  - The `resolve` command moves into `explain.py` (or `edit.py`, whose `_finish` already does resolve-then-show): no new
    module, but a lock-writing command in a module of views, or of `skill-graft.toml` edits.
  - Renderers (`tree`, `suggestions`, `show` and their helpers) move to a lower module: the helpers are shared with
    `why` and `mermaid`, so most of `explain.py` would move.

- **`PatchError` moves to `pipeline/hull.py`.** It is the walk's error: raised only there, it carries the hull as
  walked, and it reports hidden characters as well as patches. `patch.py` keeps `PatchFailed` (one skill's patches),
  `apply` and `unused`, and loses its `TYPE_CHECKING` block. The class goes below `class Hull`, so `Hull | None` needs
  no quoting: Python 3.11 to 3.13 evaluate `__init__`'s annotations when its `def` runs (3.14 defers them). `explain`
  and `update` import it with `from skill_graft.pipeline.hull import ... PatchError`, as they already import `Hull`; a
  module import would clash with their many locals named `hull`. Alternatives: `ignore_imports` for the one
  `patch -> hull` import (keeps a cycle the contract exists to refuse, and an exception list starts); setting
  `exclude_type_checking_imports` (would hide type-only imports from the layers contract too).

- **One contract, `ancestors = ["skill_graft"]`, default depth.** It checks `cli/commands/pipeline/infra` (already
  ordered by the layers contract, harmless) and the modules inside each layer, and any subpackage added later. No
  `ignore_imports`. Alternative: `ancestors = ["skill_graft.commands"]` only, as asked at the least; `pipeline` would
  stay unguarded for the one-class move above.

- **Pin the floor, `import-linter>=2.15`.** The contract type is unknown to older versions, which fail to parse the
  config; 2.15 is the version verified here. Earlier releases may ship it; not worth bisecting.

## Risks / Trade-offs

- \[Moving the core's tests out of `test_resolve.py` churns a large test file\] → move them verbatim (only the module
  name changes), in the same commit as the code they test, per AGENTS.md's test layout.
- [A future mutual dependency that looks legitimate gets refused] → that is the point; the contract's error names the
  import to drop, and the fix is to move code, not to start an `ignore_imports` list.
- \[`monkeypatch.setattr` targets in tests name `resolve.<fn>`\] → none today (`grep` finds only `resolve.resolving`
  calls); any found move with their function.
