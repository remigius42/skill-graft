# Tasks

Apply with the `mp-tdd` skill: each task red-green-refactor, one commit. `pre-commit run --all-files` stays green.

## 1. Refuse native Windows

- [x] 1.1 Tests in `tests/cli/test_cli.py`, one per scenario of the cli spec's "Supported platforms": a subprocess runs
  `python -c` that sets `sys.modules["skill_graft.commands"] = None` and `sys.modules["fcntl"] = None`, imports
  `skill_graft.cli`, then sets `sys.platform = "win32"` and exits with `main([...])`, for `resolve`; `help`, `--help`
  and `--version`; no argument, `explain` and `--bogus`. Assert exit 1, empty stdout, stderr exactly the WSL error line,
  no `Traceback`. The Linux scenario is the existing `--version` test. Verify they fail first (on the blocked import),
  then make them pass as design.md says: `main` refuses `win32`, read through a local, before `_main`; `_main` imports
  the command modules. `uv run mypy .` and `uv run lint-imports` pass

## 2. Deletions from any diff

- [x] 2.1 Tests in `tests/pipeline/test_patch.py`, one per scenario of the patches spec's "A file a patch empties is
  deleted": the patch is `make_patch`'s with the `+++` timestamp of the deleted or emptied file rewritten to a date
  other than the epoch, so they fail on Linux as on macOS; the git-format and folder-replaced ones are written by hand.
  Verify the first two fail first (the file kept, empty; no `PatchFailed`), then make them pass as design.md says, in
  `patch.apply`. README's "Writing a patch" says a file a patch leaves empty is deleted

## 3. Test on macOS

- [x] 3.1 The `test-macos` job in `.github/workflows/ci.yml` as design.md says, actions pinned by the SHAs the other
  jobs use, `persist-credentials: false` (committed as `ci: run the tests on macOS`; the draft pull request is #1). Skip
  `test_guard_counts_a_name_holding_an_invalid_byte_in_a_utf8_locale` on macOS, where APFS refuses the name. Push, and
  verify the job passes on the pull request; fix any other test failing there test-first in this task, or stop the
  change here and raise one too large for it

## 4. State the platforms

- [x] 4.1 Once 3.1's job passes: README's Installation section says Linux and macOS, on Windows through WSL, and what
  native Windows prints; `pyproject.toml` gains `classifiers` with `Operating System :: POSIX :: Linux` and
  `Operating System :: MacOS`. Verify `uv build` succeeds and the built wheel's `METADATA` lists both classifiers
