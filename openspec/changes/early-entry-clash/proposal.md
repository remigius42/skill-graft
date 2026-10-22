# Proposal

## Why

`build`, `resolve` and `update` check that the **Entries**' **Deployed names** are unique only after they have
read every **Source**, which may fetch an uncached **Ref** (and `update` first asks the remote for its tip). That
check needs only the config, so a clash between two **Entries** costs a fetch to report, and a failed fetch hides
it behind a network error.

## What Changes

- Every command that computes the **Hull** through `compute_hull` (`build`, `resolve`, `tree`, `why`, `add`,
  `remove`, `unbind`) checks the **Entries**' **Deployed names** for clashes before any **Source** is read or
  fetched, and before the temporary folder is made.
- `update` makes the same check before it contacts any remote.
- Clashes found only through **References** are unchanged. `rename` and `bind` still read the **Sources** first,
  to check the **Skill ID** they are given.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `renames`: "Deployed names are unique" adds that every command computing the **Hull** reports a clash between
  **Entries** before any **Source** is read or a remote contacted, except `rename` and `bind`.

## Impact

- `src/skill_graft/pipeline/compute.py`: a config-only check of the **Entries**' **Deployed names**, run first in
  `compute_hull`.
- `src/skill_graft/commands/update.py`: `_update` runs it before contacting a remote.
- Two new tests: in `tests/cli/test_build.py` and `tests/commands/test_update.py`. No config, lock, output or
  dependency changes.
