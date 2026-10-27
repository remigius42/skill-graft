# Tasks

Apply with the `tdd` skill: each task red-green-refactor, one commit.

## 1. Check for APM before writing

- [x] 1.1 Add `apm.require()` to `infra/apm.py`, raising the `MISSING` message `install()` also uses when
  `shutil.which("apm")` finds nothing; call it in `init` after the existing-folder check and before `mkdir`, adding
  `install APM, then run: skill-graft init` (with `--project` when given); tests in
  `tests/commands/test_init_package.py`: "APM not installed" and "APM not installed for a project" (exit 1, the
  hint in stderr, no `.apm/` created), "Retry after installing APM" (empty `PATH`, then the fake `apm` back on it,
  second `init` exits 0); `test_apm_fails`'s `missing` case keeps the folder and retry hint with `apm.require`
  patched to pass, covering `apm` gone between check and run; update `docs/design.md`'s `init` entry; verify the
  new tests fail first, then pass

## 2. One quoted command line

- [x] 2.1 Add `apm.command_line()`, `shlex.join` of `_command()`, and use it for the user-scope retry hint; test:
  `test_apm_fails` with a home folder containing a space expects the quoted path; verify it fails first, then
  passes

## 3. Hint for an unregistered folder

- [x] 3.1 Check existence as `exists() or is_symlink()` before the `apm` check, and route `mkdir`'s
  `FileExistsError` through the same refusal; when `_listed()` is false and the folder holds `apm.yml`, add
  `to register it, run: <command line>`, at project scope `to register it, run in <root>: <command line>`; fix
  `_listed()`'s docstring, which names only the project's `apm.yml`; tests: the "Init refuses an existing folder"
  scenarios ("Folder exists" with a listing `~/.apm/apm.yml`, "Unregistered folder exists", "… without APM",
  "Folder without its apm.yml", "Dangling symlink", "Home folder with a space", "Project folder exists" with a
  listing `~/repo/apm.yml`, "Unregistered project folder exists" for a missing, an unreadable and a non-listing
  `apm.yml`), each asserting `fake_apm.calls` empty and contents unchanged; update `docs/design.md`'s `init`
  entry; verify they fail first, then pass

## 4. Archive

- [ ] 4.1 In the archive commit, add a `### Fixed` entry under `[Unreleased]` in `CHANGELOG.md`: without APM,
  `skill-graft init` creates nothing and says to run it again once APM is installed; refusing an existing
  **Package** APM does not list, it gives the command that registers it; the commands `init` suggests are
  shell-quoted; verify `pre-commit run --all-files`
