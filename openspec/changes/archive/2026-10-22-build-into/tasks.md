# Tasks

Apply with the `tdd` skill: each task red-green-refactor (failing test first, then code), one commit, and
`pre-commit run --all-files` green. New words go into `.cspell.yaml`. Tests set `HOME` to `tmp_path` and build synthetic
**Skills** and **Sources**; `<dir>` is a `tmp_path` subfolder.

## 1. Destination as a parameter

- [x] 1.1 `vendor.vendor` and `lock.write` take an optional destination (the `skills` folder, the lock file), defaulting
  to the **Package**'s; verify the existing build, lock and scope tests pass unchanged and a unit test vendors and
  writes a lock into a given folder without touching the **Package**

## 2. The option

- [x] 2.1 Add `--into <dir>` to `build`'s parser with help text, in a mutually exclusive group with `--no-install` (exit
  2 with `build`'s usage, before discovery, no `package:` line); verify CLI tests for "With no-install", "Without a
  value", "Empty value" and `build --help` listing `--into` pass
- [x] 2.2 Wire `build --into` to vendor into `<dir>/.apm/skills/`, hash those copies, write `<dir>/skill-graft.lock`,
  never run APM, and print the `into:` line after `package:`; verify tests for "Throwaway build", "Package untouched",
  "Package never built", "Same lock", "Project path source" and "Both lines" pass, with `apm` absent from `PATH`
- [x] 2.3 Any failure or interrupt while vendoring, hashing or writing the lock during `build --into` removes exactly
  what `build` wrote under `<dir>`, after the temporary work folder is gone; verify the "Vendoring into the folder
  fails", "Lock write fails", "Interrupted", "Foreign file kept" and "Temporary folder inside it" tests pass
- [x] 2.4 A git **Source** at an uncached `ref` is fetched into the cache by `build --into`; verify the "Uncached ref"
  test passes in `tests/test_git_build.py`

## 3. Folder checks

- [x] 3.1 Refuse a missing `<dir>`, a file, or a non-empty folder, before loading the config; verify tests for "Missing
  folder", "Not empty", "Refused folder" and "Symlink to an empty folder" pass
- [x] 3.2 Refuse a `<dir>` under a path through `.apm/skill-graft` (as given or resolved, ignoring case) and in or
  around the git cache (both resolved), before loading the config; verify tests for "Inside a package" (including
  `.APM/Skill-Graft/`), "Inside the cache" (including a symlinked `XDG_CACHE_HOME`) and "Cache inside the folder" pass
  and the cache and **Package** are unchanged
- [x] 3.3 Refuse a `<dir>` in a path **Source**'s folder, after loading the config and before resolving; verify the
  "Inside a source" test passes

## 4. Docs

- [x] 4.1 Describe `build [--no-install | --into <dir>]` in `README.md`'s commands list and `docs/design.md`'s `build`
  entry (layout, empty folder, never APM, same lock), and its file table, where `.apm/skills/<name>/` and
  `skill-graft.lock` are also written into `<dir>` by `build --into`; verify `pre-commit run --all-files` is green
