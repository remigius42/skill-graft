# Design

## Context

See proposal.md for why. Today:

- `cli.main` sets the global (`paths.use(paths.discover(cwd))`, the working folder for `init --project`, nothing for
  `init`), prints `package:` for `WRITERS`, prints `into:` and runs `_check_into` for `build --into`, then dispatches.
  `resolve`, `build`, `tree` and `why` are written inline; `finally: paths.use(None)`.

- The four copies of "resolve the **Hull** and write the lock":

  - `cli` `resolve`: hull warnings after tree and suggestions; hashes the patched copies (`render`'s default); writes
    nothing before the lock, so needs no rollback.
  - `cli` `build`: hull warnings right after computing, before vendoring; hashes the vendored copies; vendors before the
    lock; `--into` runs `_undo_into` on `BaseException`.
  - `edit._finish`: hull warnings after tree and suggestions; hashes the patched copies; writes `skill-graft.toml`
    before the lock; restores the TOML on `OSError` only.
  - `update._update`: hull warnings right after computing, before the diff; hashes with `lock.skill_hashes`, once for
    digest, diff and lock; writes the diff file, then the `[sources]` refs, before the lock; removes the diff on
    `BaseException`, but leaves the TOML changed.

  Patched copies with rewrites applied hash as vendored copies do, unless the upstream folder changes during `build`:
  `test_lock_hashes_what_was_vendored` pins that `build` hashes what it vendored.

- Config warnings print when the config is loaded, before any output. `tree`, `why`, `resolve` and the edits print the
  **Hull**'s warnings after their output, `tree` and `why` also on failure (`finally`); `build` prints them before
  vendoring, so above APM's output, and `update` above its **Hull diff**: both scroll away. The new "Warnings come last"
  (cli spec) makes every command print them last, also on failure.

- Every test drives `cli.main`. Those that patch a module function do it through its module, so moving the callers keeps
  them working only if the moved code still calls that function: `tests/cli/test_build.py` (`lock.write`,
  `vendor.vendor`, `config.load`), `tests/cli/test_resolve.py` (`vendor.vendor`; both now in `tests/commands/`, task
  7.2), `tests/commands/test_update.py` (`edit.write` for the refs write, `files.atomic_write` for the diff,
  `deployed.summary`, and `lock.skill_hashes`, counting calls: its second is the old **Hull**'s, so `resolving` must not
  call `skill_hashes` when `hashes` is set).

## Goals / Non-Goals

**Goals:**

- `cli` imports `commands` and `infra.errors` only, checked by import-linter.
- One place resolves the **Hull** and writes the lock; its differences between commands are parameters with a stated
  rule, not drift.
- Byte-identical stdout, files and exit codes for every existing test, and stderr but for where the warnings stand; the
  TOML restored on a failed or interrupted lock write, and a failed restore reported as a notice beside the original
  error instead of replacing it, aside.

**Non-Goals:**

- No `pipeline` or `infra` signature takes a `Scope` yet; `config.load`, `compute.known` and the rest read the global,
  which `scope.of` keeps in step.
- `init`, the edit commands and `update` do not stop reading `paths.*` themselves; they only take the `Scope` to pass to
  the shared context manager.

## Decisions

- **`commands/scope.py`: `of(command, project)`, a context manager yielding the `Scope`.** It picks the root (`init`:
  home; `init --project`: the working folder; otherwise `paths.discover(working folder)`), calls
  `paths.use(scope.root)`, prints `package: <scope.package>` when `command` is in `WRITERS` (moved here from `cli`;
  `init` still prints its own once its checks pass), yields, and resets with `paths.use(None)` in `finally`. It is the
  only caller of `paths.use`. A context manager, not a function, because the reset must also leave `cli`, which may not
  import `paths`. It reads the working folder itself (`_working_folder` moves here), as ADR 0008 says: plain `init` must
  not read it ("Working folder is gone" exempts it). `cli` names the value `current`, since `scope` is the `commands`
  module it calls.

- **`Scope` in `infra/paths.py`: `@dataclass(frozen=True) class Scope: root: Path`**, with `package`
  (`root/.apm/skill-graft`, the **Package**), `user` (true when `root` resolves to the home folder; a `cached_property`,
  decided once per value), `lock_file` and `skills`: what the moved code reads. `paths.scope()` still returns `user` or
  `project`, from `user`. `use` keeps one module-level `Scope | None` in place of `_root` and `_scope`; `in_use()`
  returns it, or, while it is `None` (at import, after `use(None)`), a new `Scope(Path.home())` per call, so a `HOME`
  changed between tests is read as `root()` reads it today. That fallback is user scope by construction; inside a
  command the global is always set, so its scope is decided once per `use`, as today. The module functions (`package()`,
  `scope()`, `skills()`, …) and `lock.write`'s and `lock.read`'s default file read `in_use()`, so each path is derived
  once. Change 2 adds the remaining paths and deletes `in_use()` and the functions.

- **Warnings come last, collected in one place: `cli`.** `infra/errors.py` gains `warnings_last()`, a context manager
  yielding a `list[str]` and printing each distinct one with `warn` in `finally`, in the order first added. `cli.main`
  enters it inside its `try`, around `scope.of`, and passes the list to each command as its `warnings` parameter; a
  command appends `loaded.warnings` and `hull.warnings` as soon as it has them instead of calling `warn`. So the
  `package:` notice comes first, every output and notice next, the warnings after them, and `cli`'s `except` prints the
  error line last. An edit appends the edited config's warnings when it resolves; when it fails before that, the
  warnings of the config `edit.read` parsed; a no-op edit appends none, as the edit spec has it print only its notices.
  `warn` is then called only by `warnings_last`. Alternatives: each command printing its own in a `finally`, eight
  copies of one rule; `warn` buffering into a module global flushed at exit, the hidden state ADR 0008 removes. `init`
  and `help` have no warnings and take no list.

- **`commands/resolve.py`: `resolving(scope, loaded, warnings, cache=None, refs=None, lock_file=None, write=True)`, the
  one "resolve the **Hull** and write the lock".** A context manager around `compute.compute_hull` yielding a
  `Resolution` (`hull`; `hashes`, settable, `None` meaning the patched copies'; `writes`, a list of `(file, write)` the
  caller appends to: a file and the call that replaces it, run before the lock). With `write` false it does nothing
  after the caller's block. Otherwise, after the block, it renders the lock while the patched copies still exist
  (`render` may fail: before any write), leaves `compute_hull`, runs each write in order, then
  `lock.write(text, lock_file or scope.lock_file)`. On any `BaseException` it restores the files it wrote, in reverse,
  and re-raises. An error in the caller's block propagates before anything is rendered or written. It prints nothing but
  a failed restore.

  - *Warnings*: it appends the **Hull**'s warnings to `warnings` as soon as the **Hull** is computed, so a later failure
    still prints them. A `PatchError` carries no warnings (`hull.walk` clears the walked **Hull**'s, as the
    hidden-characters spec says), so there is nothing to add on that path, for `tree` and `why` neither.
    `resolve.show(hull)` prints tree and suggestions for `resolve` and the edits.
  - *Hashes*: the lock hashes what the command deploys. `build` sets `hashes` to its vendored copies' inside the block;
    `update` sets the ones it already computed for digest and diff; `resolve` and the edits leave `None`, the patched
    copies with rewrites applied, which is what `build` would vendor.
  - *Rollback*: right before calling a write it reads the file's bytes, or notes it missing, and records that, so the
    restore puts back what this write replaced, not an older snapshot (a user's edit saved during `update`'s fetch
    survives), and a Ctrl-C between the replace and its return cannot skip it; restoring a file the write never reached
    rewrites the same bytes. Restoring uses `files.atomic_write`, or removes a file that was missing, best-effort, as
    `_undo_into`: a restore failing with `OSError` prints a notice naming the file and the error, the next still runs,
    and the original error is re-raised. The writes stay the callers' own calls, so the tests patching `edit.write`,
    `files.atomic_write` and `lock.write` keep reaching them. `edit` appends
    `(the config file resolved, edit.write(document))`: a Ctrl-C during the lock write now also restores the TOML (edit
    spec delta). `update` appends `(the diff file, its atomic_write)`, then
    `(the config file resolved, _write_refs(moved))` (update spec delta). `build --into`'s `_undo_into` stays in `build`
    around the whole run, since vendoring fails inside the block, before any write. Alternative, `(do, undo)` pairs:
    each caller would capture its own snapshot, the race this rules out.
  - `update --dry-run` passes `write=False` and appends no writes: no lock is rendered or written. It writes `--diff`'s
    file itself after the block, last, as the update spec requires of a dry run, and as it does today. Alternative,
    `update` calling `compute_hull` itself in a dry run: a second path through the same steps.

- **`build` in `commands/build.py`: `build(scope, warnings, given, no_install)`,** `given` being `--into` as typed,
  `into` the resolved folder, as in `cli` before. It prints `into: <dir>` and runs `_check_into` first, before loading
  the config, as `cli` does now; with `scope.of` printing `package:` on entry, stderr keeps `package:`, `into:`, then
  any error. `_check_into_sources` and `_undo_into` move with it. Its lock goes through `resolving` with `lock_file` set
  for `--into`, so through `lock.write`.

- **`tree` and `why` in `commands/explain.py`: `show_tree(scope, warnings, as_mermaid, as_link)` and
  `show_why(scope, warnings, text)`,** not `mermaid` and `link`, which would shadow the module's functions of those
  names. `_explain` moves with them, its `finally: warn(...)` becoming an append; it loads the config with
  `config.load()` and appends its warnings itself, as `resolve.load` does, since `resolve` imports `explain`. They take
  the `Scope` per the ADR, unused until change 2, and no `Resolution`: they write nothing.
  `--link needs --format mermaid` stays a usage error in `cli`, as does `_into`.

- **`resolve` in `commands/resolve.py`: `resolve(scope, warnings)`;** `update.update(scope, warnings, aliases, …)` and
  the edits (`edit.add(scope, warnings, skills)`, …) take the `Scope` and load the config themselves, `cli._load` moving
  to `commands` as `resolve.load(warnings)`, which appends the config's warnings to the list.

- **The forbidden contract:**

  ```toml
  [[tool.importlinter.contracts]]
  name = "cli reaches pipeline and infra only through commands"
  type = "forbidden"
  source_modules = ["skill_graft.cli"]
  forbidden_modules = ["skill_graft.pipeline", "skill_graft.infra"]
  ignore_imports = ["skill_graft.cli -> skill_graft.infra.errors"]
  allow_indirect_imports = true
  ```

  Forbidding the packages covers modules added later; `ignore_imports` lets the one exception through.
  `allow_indirect_imports` because `cli → commands → pipeline` is the point.

## Risks / Trade-offs

- \[A `Resolution` with a mutable `writes` list of calls\] → Two callers append one or two entries next to the call;
  `resolving` owns the snapshot and the restore, so no caller handles rollback. `writes=` given at entry fails for
  `update`, whose diff text exists only inside the block.
- [A restore can itself fail] → The specs promise the TOML's bytes back unless restoring fails too, which a notice then
  names; the original error stays the one reported.
- \[`Scope` and the global coexist for one change, two sources of truth\] → The global is a `Scope`, every module
  function reads it, and `scope.of` is the only writer.
- \[Moving 300 lines out of `cli` can drift output silently\] → No existing test changes but the warnings task's; the
  move is one commit per command, each with the suite green.
- [Tests pinning today's warning order break] → Only the warnings task changes them, each to the new order, named in its
  commit.
- \[`Scope` parameters unused by `tree` and `why` until change 2\] → Accepted; the ADR has them take it from the start,
  so change 2 changes no `commands` signature.

## Migration Plan

Internal only. Rollback is reverting the branch.

## Open Questions

None that change the approach. Names (`scope.of`, `paths.in_use`, `resolve.resolving`, `Resolution`, `show_tree`,
`show_why`) can change at apply time.
