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
  Since `build` neither creates nor deletes `<dir>`, a failed run only has to undo its own writes: the build
  runs in one `try` that catches `BaseException` (Ctrl-C included), and once vendoring has started (a flag set
  just before it; a config or **Source** error writes nothing, so nothing is removed) it removes
  `.apm/skills.new/` (left by a Ctrl-C mid-copy), `.apm/skills.old/`, `.apm/skills/`, the lock, and `.apm/` if
  then empty, then re-raises. The lock's temporary file is not listed: the atomic write removes it on any
  error. Cleanup errors are suppressed, so the build's own error is the one reported. A file another process
  put in `.apm/` meanwhile stays; guarding every path against concurrent writers into a fresh `mktemp -d`
  folder was rejected as locking for a case that does not occur. The cleanup runs after the `with` that owns
  the temporary work folder has closed, so a `TMPDIR` inside `<dir>` is gone by then and `<dir>` ends empty;
  refusing such a `TMPDIR` was rejected as one more check for a case the ordering already handles.
- **Checked before resolving.** The checks that need no config run right after the `package:` and `into:` lines,
  before the config loads, so a bad folder fails fast and writes nothing, the cache included: empty (following
  symlinks; `<dir>` is used resolved); a path through `.apm/skill-graft` in `<dir>` resolved, or as given with
  `..` normalized away (so a symlinked **Package** is caught, but a path only passing through one is not); and
  `paths.overlap` both ways between the resolved `<dir>` and `paths.cache()` resolved (a symlinked
  `XDG_CACHE_HOME` must not hide the cache, and one inside `<dir>` would put the cache there). The **Source**
  check, `<dir>` inside a path **Source**'s folder, needs the loaded config, so the `build` branch loads it
  itself and checks before resolving, rather than giving the shared resolve helper (also used by `why`, `tree`
  and `resolve`) a build-only parameter; a config error is reported first. The reverse, a **Source** inside
  `<dir>`, cannot happen: `<dir>` is empty and a path **Source** must be an existing folder.
- **Placement compared ignoring case.** All three placement checks lowercase both paths: on a case-insensitive
  filesystem `resolve` keeps a case-variant path's case, so `.APM/Skill-Graft`, `~/.Cache/skill-graft` or `~/Own`
  would otherwise slip past. On a case-sensitive filesystem this refuses a distinct lookalike such as `~/SRC/out`,
  which is harmless; probing each filesystem's case sensitivity, or `os.path.samefile` on possibly missing
  folders, was rejected as more code for no gain. `paths.in_package` stays case-sensitive for discovery and the
  config's **Source** checks; changing those is outside this change.
- **No `resolve` hint after `--into`.** `build` normally ends with "N prose suggestion(s): run skill-graft
  resolve", but `resolve` rewrites the **Package**'s lock, which a throwaway build should not lead to. With
  `--into` the hint is left out; `<dir>/skill-graft.lock` still lists the suggestions.
- **`--into` and `--no-install` are an argparse mutually exclusive group** on `build`'s parser, so the clash
  exits 2 with `build`'s usage before `paths.discover` (no `package:` line, as the scope spec requires), and the
  usage reads `[--no-install | --into DIR]`. An empty value is refused there too (an argparse `type` that raises
  `ArgumentTypeError`), since `Path("")` is the working folder.
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
