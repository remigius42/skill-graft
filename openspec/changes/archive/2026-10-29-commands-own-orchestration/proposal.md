# Proposal

## Why

`cli.main` runs `resolve`, `build`, `tree` and `why` itself, so `cli` imports `pipeline` and `infra` directly,
and "resolve the **Hull** and write the lock" exists four times: in `cli`'s `resolve` and `build`, in
`edit._finish` and in `update._update`. The copies differ in when warnings print, which copies the lock hashes
(patched or vendored) and how a failed write is rolled back: `edit` restores `skill-graft.toml` when the lock
cannot be written, `update` does not. ADR 0008 has every command act on an explicit `Scope`; this is the first
of its two changes: `commands` owns the orchestration and builds the `Scope`, `cli` only parses and dispatches.

## What Changes

- `resolve`, `build`, `tree` and `why` move from `cli.main` into `commands/`, each taking a `Scope`. `cli`
  parses the arguments, refuses usage errors, dispatches, and turns a `SkillGraftError` or `OSError` into exit 1.
- One context manager in `commands` resolves the **Hull** and writes the lock, used by `resolve`, `build`, the
  edit commands and `update`. It renders the lock while the patched copies exist, runs the command's writes
  before the lock (the edited `skill-graft.toml`, `update`'s **Deployed diff** file and new **Refs**), then the
  lock, and undoes those writes in reverse if a later one fails, Ctrl-C included.
- One function in `commands` builds the `Scope` for every command (`init`: the home folder, `init --project`:
  the working folder, every other: what `discover` finds), prints the `package:` notice for the commands that
  write, and holds the only `paths.use(scope.root)` call, resetting it on exit. `cli`'s own `discover` call
  goes. `infra/paths.py` gains the frozen `Scope` dataclass the ADR names, with the paths the moved code reads.
- `build` prints the `into:` notice and checks `--into` itself, right after the `package:` line, as today.
- A new import-linter `forbidden` contract: `skill_graft.cli` may not import `skill_graft.pipeline` or any
  `skill_graft.infra` module but `infra.errors` (`allow_indirect_imports = true`).
- Every command prints its warnings last: after its output, its notices and APM's, before only its error line,
  and also when it fails. Today `build` prints them above APM's output and `update` above its **Hull diff**,
  where they scroll away; config warnings print first everywhere.
- `update`: when the lock cannot be written after the new **Refs** were, `skill-graft.toml` is restored, as the
  edit commands already do; for `update` and the edit commands, also when Ctrl-C interrupts the lock write. A
  restore that itself fails is named in a notice and the original error kept, where today the restore's error
  replaces it. Every other output and file stays byte for byte as today.

Out of scope, follow-ups:

- Passing the `Scope` into `pipeline` and `infra` and deleting `paths.use` with its globals (ADR 0008's second
  change). `init`, `edit` and `update` keep reading the global in this change wherever they do not hand the
  `Scope` to the shared function.
- `compute.known` checks out every **Source** again after the **Hull** was computed (`why`, `edit.rename`,
  `edit.bind`).
- `cli._explain` re-runs `show` on the **Hull** a `PatchError` carries; it moves with `tree` and `why` unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cli`: new "Warnings come last", for every command.
- `build`: "Build resolves first" no longer prints warnings before vendoring.
- `edit`: "Resolve before writing" also covers an interrupted lock write: it leaves both files unchanged.
- `update`: "Resolve before writing" also covers a failed or interrupted lock write: it leaves `skill-graft.toml`
  unchanged.

## Impact

- `src/skill_graft/cli.py`: only parsing and dispatch; `WRITERS`, `_check_into`, `_check_into_sources`,
  `_undo_into`, `_working_folder`, `_load`, `_hull` and `_explain` move out.
- `src/skill_graft/commands/`: new `scope.py` (`of`, building the `Scope`), `resolve.py` (the `resolve` command and
  the shared
  context manager), `build.py`; `explain.py` gains the `tree` and `why` commands; `edit.py` and `update.py` use the
  shared context manager.
- `src/skill_graft/infra/paths.py`: the `Scope` dataclass; the module functions derive from it.
- `src/skill_graft/infra/errors.py`: `warnings_last()`, collecting a command's warnings and printing them on exit.
- `pyproject.toml`: the forbidden contract.
- Tests: existing tests pass unchanged but those pinning where warnings stand; new tests for `Scope`,
  `scope.of`, warnings last, the shared context manager's rollback and `update`'s restored TOML.
- `docs/design.md`'s "Stack" entry. `CHANGELOG.md` at archive: `### Changed` for warnings last, `### Fixed` for
  the TOML restored when `update`'s lock write fails or an edit's or `update`'s is interrupted.
