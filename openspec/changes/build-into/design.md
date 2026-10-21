# Design

## Context

`build` (in `cli.py`) resolves into a temporary work folder, calls `vendor.vendor(hull)`, hashes the vendored
copies, `lock.write(lock.render(...))`, then `apm.install()` unless `--no-install`. Both `vendor` and `lock.write`
take their destination from `paths`: `paths.skills()` (`<package>/.apm/skills`) and
`paths.package() / "skill-graft.lock"`. `lock.render` stays Package-relative on its own: `_source_path` uses
`paths.root()` and `paths.package()`, which `--into` must not change. Path **Sources** are already refused when
they overlap any **Package** (`config._source_folder`), and discovery skips `.apm/skill-graft` paths
(`paths.in_package`).

## Goals / Non-Goals

**Goals:**

- One code path for `build` and `build --into`: the same resolution, vendoring and lock rendering, only the
  destination differs, so the two can never disagree on bytes.

**Non-Goals:**

- `--into` on `resolve`, `update` or the editing commands.
- Cleaning `<dir>` up afterwards: the caller owns it (`mktemp -d`, then `rm -rf`).
- Reusing a previous `--into` output: each run needs a fresh empty folder.

## Decisions

- **Destination as a parameter, not a second `paths` root.** `vendor.vendor` takes the `skills` folder and
  `lock.write` the lock file (both defaulting to the **Package**'s). Rebinding `paths.use()` to `<dir>` was
  rejected: it would also move `paths.root()` and `paths.package()`, which `lock._source_path`, the config check
  and the scope all read, so the lock would no longer match an in-place one.
- **Layout mirrors the Package** (`<dir>/.apm/skills/`, `<dir>/skill-graft.lock`): a tool reading a **Package**
  reads `<dir>` by swapping the prefix. A flatter layout was rejected for that reason.
- **Existing, empty folder only.** The one caller makes it with `mktemp -d`. Creating a missing `<dir>` was
  rejected: a typo would quietly create a tree, and a failure would then have to delete a folder `build` made.
  Since `build` neither creates nor deletes `<dir>`, a failed run only has to empty it: `vendor` already removes
  its `skills.new/`; the `--into` path also removes the `.apm/` it created, so `<dir>` is empty again. The lock is
  written last, after vendoring succeeded, as in place.
- **Checked before resolving.** The `<dir>` checks run right after the `package:` and `into:` lines and before
  the config loads, so a bad folder fails fast and writes nothing, the cache included. Placement checks:
  `paths.in_package` on `<dir>` as given and resolved (any **Package**, as discovery treats it);
  `paths.overlap` with each path **Source**'s folder (needs the loaded config, so this one runs after loading,
  still before resolving) and with `paths.cache()` resolved. The empty check follows symlinks: `<dir>` is used
  resolved.
- **`--into` and `--no-install` together exit 2** via argparse (`parser.error`), alongside `tree`'s
  `--link` check, before `paths.discover`, so no `package:` line is printed for a usage error, as the scope spec
  requires.
- **`into:` line** printed with `notice`, right after `package:`, absolute but not resolved (as `package:`).

## Risks / Trade-offs

- \[The **Check** forgets to delete `<dir>`\] → harmless temp folder; `graft-check`'s skill text owns the cleanup.
- \[`<dir>` inside an APM deploy folder, e.g. `~/.claude/skills/x/`\] → not refused: `<dir>/.apm/skills/<name>/`
  is too deep for a harness to load as a skill, and the config already warns for **Sources** there.
- \[A **Source** added later points into an old `<dir>`\] → a `<dir>` is throwaway; nothing new to guard.

## Migration Plan

None: a new option. `graft-check` switches from `build --no-install` to `build --into "$(mktemp -d)"` in its own
change once this lands.
