# Tasks

## 1. Report an Entry clash before reading Sources

- [ ] 1.1 Red: in `tests/cli/test_build.py`, beside `test_clash_is_reported_before_searching`, add the "Entries
  clash before any fetch" scenario: an `Upstream` with `tdd/SKILL.md`, `own/tdd` in a path **Source**,
  `[sources.mp]` at that commit's `ref`, uncached; assert `build` exits 1, `err` names `mp/tdd` and `own/tdd`, and
  `home / ".cache"` does not exist; verify it fails today (the fetch creates the cache). Green: add
  `compute.check_entries(config)` and call it first in `compute_hull`, before the `TemporaryDirectory`, updating
  the docstring; verify the new test and the existing clash tests pass and `pre-commit run --all-files` is green
- [ ] 1.2 Red: in `tests/commands/test_update.py` add the "Entries clash before update fetches" scenario: the same
  two **Entries**, `mp` with a `ref`, `update mp`; assert it exits 1 naming both, `home / ".cache"` does not exist
  and `skill-graft.toml` is unchanged; verify it fails today. Green: call `compute.check_entries` in `_update`
  before the first `_tip`; verify the test passes and `pre-commit run --all-files` is green
