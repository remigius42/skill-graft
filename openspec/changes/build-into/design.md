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
  Since `build` neither creates nor deletes `<dir>`, a failed run only has to empty it: vendoring, hashing the
  copies and writing the lock run in one `try`, and on any error the `--into` path removes everything it wrote
  under `<dir>` (its `.apm/`, a lock or the lock's temporary file) before re-raising, so `<dir>` is empty again.
- **Checked before resolving.** The checks that need no config run right after the `package:` and `into:` lines,
  before the config loads, so a bad folder fails fast and writes nothing, the cache included: empty (following
  symlinks; `<dir>` is used resolved), `paths.in_package` on `<dir>` as given and resolved (any **Package**, as
  discovery treats it), `paths.overlap` of the resolved `<dir>` with each of `paths.packages()` resolved (on a
  case-insensitive filesystem `resolve` keeps a case-variant path's case, so the check also compares each
  ancestor of `<dir>` with the **Package** by `os.path.samefile`), and `paths.overlap` both ways with
  `paths.cache()` (an `XDG_CACHE_HOME` inside `<dir>` would put the cache there). The **Source** check,
  `<dir>` inside a path **Source**'s folder, needs the loaded config, so it runs after loading, still before
  resolving; a config error is reported first. The reverse, a **Source** inside `<dir>`, cannot happen: `<dir>`
  is empty and a path **Source** must be an existing folder.
- **`--into` and `--no-install` are an argparse mutually exclusive group** on `build`'s parser, so the clash
  exits 2 with `build`'s usage before `paths.discover` (no `package:` line, as the scope spec requires), and the
  usage reads `[--no-install | --into DIR]`.
- **`into:` line** printed with `notice`, right after `package:`, absolute but not resolved (as `package:`).

## Risks / Trade-offs

- \[The **Check** forgets to delete `<dir>`\] → harmless temp folder; `graft-check`'s skill text owns the cleanup.
- \[`<dir>` inside an APM deploy folder, e.g. `~/.claude/skills/x/`\] → not refused: `<dir>/.apm/skills/<name>/`
  is too deep for a harness to load as a skill, and the config already warns for **Sources** there.
- \[A forgotten `<dir>` inside a folder later declared as a path **Source**\] → discovery skips only
  `.apm/skill-graft` paths, so `<dir>/.apm/skills/` would be read as duplicate **Skills**. `mktemp -d` puts `<dir>`
  under the temporary folder, and `graft-check`'s skill text deletes it; a marker or a discovery change is not
  worth it for a throwaway folder.

## Migration Plan

None: a new option. `graft-check` switches from `build --no-install` to `build --into "$(mktemp -d)"` in its own
change once this lands.
