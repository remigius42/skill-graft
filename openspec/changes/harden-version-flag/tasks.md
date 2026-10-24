# Tasks

Apply with the `tdd` skill: each task red-green-refactor, one commit. Tests fake the installed distribution with
`monkeypatch` on `importlib.metadata`, as `add-version-flag`'s do.

## 1. Never fail

- [ ] 1.1 In `_origin`, catch `OSError` and `RecursionError` beside `ValueError`; tests in `tests/cli/test_cli.py`:
  the cli spec's "Unreadable record", a `read_text` raising `OSError` with `ELOOP` and with `EIO`, and a
  `direct_url.json` nested 100 000 deep, each printing `skill-graft 0.2.0` and exiting 0; verify they fail first,
  then pass
- [ ] 1.2 In `_Version`, print `skill-graft unknown` when `metadata.distribution` raises `PackageNotFoundError`, or
  reading the version raises `OSError`, or the version is not a printable, non-empty string; tests: "Not installed"
  and "Unreadable metadata" (a version of `None` and one holding a newline), each exiting 0; verify they fail first,
  then pass

## 2. One printable line

- [ ] 2.1 Drop a `requested_revision` that is not printable, and add nothing for a `commit_id` that is not; tests:
  "Revision that is not printable" (`main\nfoo`, `\x1b[2J`, U+202E) printing `skill-graft 0.2.0 (e294a0e)`, and
  "Commit that is not printable" printing `skill-graft 0.2.0`; verify they fail first, then pass

## 3. Tests of the real installation

- [ ] 3.1 Add a helper in `tests/cli/test_cli.py` running `Path(sys.executable).parent / "skill-graft"`; use it in
  `test_help_lists_commands` and `test_version_of_this_installation`, the latter comparing
  `stdout.split()[:2] == ["skill-graft", metadata.version("skill-graft")]`; verify both pass with a `PATH` holding no
  `skill-graft` (`PATH=/usr/bin uv run --no-sync pytest tests/cli/test_cli.py`), where they failed before

## 4. Archive

- [ ] 4.1 In the archive commit, extend `CHANGELOG.md`'s unreleased `--version` entry under `### Added`: without an
  installation it prints `skill-graft unknown`; check the box there; verify `pre-commit run --all-files`
