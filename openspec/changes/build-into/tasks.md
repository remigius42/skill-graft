# Tasks

Apply with the `tdd` skill: each task red-green-refactor (failing test first, then code), one commit, and
`pre-commit run --all-files` green. New words go into `.cspell.yaml`. Tests set `HOME` to `tmp_path` and build
synthetic **Skills** and **Sources**; `<dir>` is a `tmp_path` subfolder.

## 1. Destination as a parameter

- [ ] 1.1 `vendor.vendor` and `lock.write` take an optional destination (the `skills` folder, the lock file),
  defaulting to the **Package**'s; verify the existing build, lock and scope tests pass unchanged and a unit test
  vendors and writes a lock into a given folder without touching the **Package**

## 2. The option

- [ ] 2.1 Add `--into <dir>` to `build`'s parser with help text, and refuse it with `--no-install` (exit 2,
  before discovery, no `package:` line); verify CLI tests for "With no-install", "Without a value" and
  `build --help` listing `--into` pass
- [ ] 2.2 Wire `build --into` to vendor into `<dir>/.apm/skills/`, hash those copies, write
  `<dir>/skill-graft.lock`, never run APM, and print the `into:` line after `package:`; verify tests for "Throwaway
  build", "Package untouched", "Package never built", "Same lock", "Project path source" and "Both lines" pass,
  with `apm` absent from `PATH`
- [ ] 2.3 A failed copy during `build --into` leaves `<dir>` empty; verify the "Vendoring fails" test passes
- [ ] 2.4 A git **Source** at an uncached `ref` is fetched into the cache by `build --into`; verify the "Uncached
  ref" test passes in `tests/test_git_build.py`

## 3. Folder checks

- [ ] 3.1 Refuse a missing `<dir>`, a file, or a non-empty folder, before loading the config; verify tests for
  "Missing folder", "Not empty", "Refused folder" and "Symlink to an empty folder" pass
- [ ] 3.2 Refuse a `<dir>` in a **Package** (as given or resolved), in or around a path **Source**'s folder, or in
  the git cache, before resolving; verify tests for "Inside a package", "Inside a source" and "Inside the cache"
  pass and the cache and **Package** are unchanged

## 4. Docs

- [ ] 4.1 Describe `build [--no-install | --into <dir>]` in `README.md`'s commands list and `docs/design.md`'s
  `build` entry (layout, empty folder, never APM, same lock); verify `pre-commit run --all-files` is green
