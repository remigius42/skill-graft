# Proposal

## Why

`compute_hull` checks that the **Entries**' **Deployed names** are unique only after it has read every **Source**,
which may fetch an uncached **Ref**. That check needs only the config, so a clash between two **Entries** costs a
fetch to report, and a failed fetch hides it behind a network error.

## What Changes

- Check the **Entries**' **Deployed names** for clashes before any **Source** is read or fetched (and before the
  temporary folder is made), so every command computing the **Hull** reports such a clash at once, without
  contacting a remote.
- A clash between **Entries** now wins over every error from reading **Sources** (a missing `ref`, a failed fetch,
  a bad `subdirectory`). Clashes found only through **References** are unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `renames`: "Deployed names are unique" adds that a clash between **Entries** is reported before any **Source**
  is read or fetched.

## Impact

- `src/skill_graft/pipeline/compute.py` (`compute_hull`): the entries-only `rename.check_unique` call moves ahead
  of `_folders` and the `TemporaryDirectory`.
- One new test in `tests/cli/test_git_build.py`. No config, lock, output or dependency changes.
