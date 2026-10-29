# Design

## Context

`compute_hull` opens its temporary folder, reads every **Source** (`_folders`: `check_refs`, then a checkout that may
fetch), and only then calls `rename.check_unique` on the **Entries**' **Deployed names**. `update` reaches
`compute_hull` only after `check_refs`, `_check_branch`, `_tip` (an `ls-remote`) and a fetch per selected **Source**.
`rename` and `bind` call `compute.known()`, which reads every **Source**, before `_finish` reaches `compute_hull`.

## Goals / Non-Goals

**Goals:**

- `build`, `resolve` and `update` report a clash between **Entries** without reading a **Source** or contacting a
  remote.

**Non-Goals:**

- `rename` and `bind`: `known()` reads a **Source** to check the **Skill ID** it is given, which it must do anyway. That
  it reads every **Source**, not only that one, is a separate issue.
- Making an **Entry** clash win over every other config error: the order among config-only checks (`check_refs`,
  `_check_branch`, selection errors) stays as it is.

## Decisions

- **One config-only function, `compute.check_entries(config)`**, wrapping
  `rename.check_unique(config, {entry: deployed(config, entry) ...})`. `compute_hull` calls it after `check_refs` (still
  also `_folders`'s first step, for `known()`, so a missing `ref` still wins, as in `update`) and before the
  `TemporaryDirectory`; `_update` calls it after its own config checks and before the first `_tip`. The check then runs
  again inside each `compute_hull` of `update`; it reads only the config, so that costs nothing. Alternative: put it in
  `_folders` or `known()`. Rejected: `known()` runs before an edit is applied, so `rename own/tdd own-tdd` would refuse
  to run because of the very clash it fixes.
- **Tests at the CLI**, next to the existing clash tests: `build` in `tests/cli/test_build.py` beside
  `test_clash_is_reported_before_searching`, `update` in `tests/commands/test_update.py`. "Fetched nothing" is shown by
  `~/.cache` not existing, as `test_git_source_without_ref` does.

## Risks / Trade-offs

- \[`update` with clashing **Entries** no longer fetches, so the user fixes the clash before seeing the new tips\] →
  intended: the clash fails `update` either way, after the fetch today.
