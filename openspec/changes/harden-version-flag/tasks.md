# Tasks

Apply with the `tdd` skill: each task red-green-refactor, one commit. Tests fake the installed distribution with
`monkeypatch` on `importlib.metadata`, as `add-version-flag`'s do.

## 1. Never fail

- [x] 1.1 In `_origin`, catch `OSError` and `RecursionError` beside `ValueError`; tests in `tests/cli/test_cli.py`:
  the cli spec's "Unreadable record", a `read_text` raising `OSError` with `ELOOP` and with `EIO`, and a
  `direct_url.json` nested 100 000 deep, each printing `skill-graft 0.2.0` and exiting 0; verify they fail first,
  then pass
- [ ] 1.2 In `_Version`, read the version as `distribution.metadata.get("Version")`, and let it read `unknown` when
  `metadata.distribution` raises `PackageNotFoundError`, reading the metadata raises `OSError` or `ValueError`, or
  the version is missing or not printable ASCII; keep the origin whenever a distribution was found; tests: "Not
  installed", "Unreadable metadata" (`OSError`, a METADATA holding byte `0xff`, no `Version`, a version holding a
  newline) and "Unknown version from git", each exiting 0, with `-W error::DeprecationWarning` raising nothing; verify
  they fail first, then pass

## 2. One printable line

- [ ] 2.1 Drop a `requested_revision` that is not printable ASCII, and add nothing for a `commit_id` that does not
  match `[0-9a-fA-F]{7,}`; tests: "Revision that is not printable ASCII" (`main\nfoo`, `\x1b[2J`, U+202E, `ブランチ`)
  printing `skill-graft 0.2.0 (e294a0e)`, and "Commit that is not a hash" (`abc) x`, `\x1b[2J` followed by hex)
  printing `skill-graft 0.2.0`; verify they fail first, then pass

## 3. Tests of the real installation

- [ ] 3.1 Add a helper in `tests/cli/test_cli.py` running `Path(sysconfig.get_path("scripts")) / "skill-graft"`; use
  it in `test_help_lists_commands` and `test_version_of_this_installation`, the latter comparing
  `stdout.split()[:2] == ["skill-graft", metadata.version("skill-graft")]`; verify by running the venv's pytest
  directly with a `PATH` holding no `skill-graft` (`PATH=/usr/bin .venv/bin/pytest tests/cli/test_cli.py`, not
  through `uv run`, which puts `.venv/bin` back on `PATH`): both fail before, pass after

## 4. Archive

- [ ] 4.1 In the archive commit, extend `CHANGELOG.md`'s unreleased `--version` entry under `### Added`: without an
  installation it prints `skill-graft unknown`; check the box there; verify `pre-commit run --all-files`
