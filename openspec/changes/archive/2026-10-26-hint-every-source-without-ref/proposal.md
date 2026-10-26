# Proposal

## Why

With two git **Sources** `a` and `b` both without `ref`, as right after adding them to a fresh `skill-graft init`,
`update a` refuses because `b` has no `ref` and says to run `skill-graft update b`, which refuses because `a` has none
and says to run `skill-graft update a`. The hints loop. `build` and every other command reading the **Sources** name
only the first one too. The way out, `skill-graft update a b`, is never suggested. Even when the hint works, it drops
what the user asked for: `update a` with `b` lacking a `ref` suggests `update b`, leaving `a` where it was, and a
`--dry-run` becomes a write.

## What Changes

- The error names every git **Source** without `ref` that blocks the run, not just the first: for `update`, those
  not selected; for the other commands, all of them.
- `update`'s hint is the command the user ran, with those **Sources** added: `update a` suggests
  `skill-graft update a b`. It keeps `--dry-run` and `--diff <file>`; `--expect` becomes `--dry-run`, since the
  added **Sources** change the **Hull** and its **Hull digest**, which must be reviewed again.
- `build` and the other commands suggest one `skill-graft update` naming every git **Source** without `ref`.
- The refusal itself stays: `update a` still needs every other git **Source** to have a `ref`, since the **Hull**
  reads them all.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `update`: the Selection errors requirement names every unselected git **Source** without `ref` and suggests the
  command run again with them added.
- `git-sources`: the Build needs every ref requirement names every git **Source** without `ref` and one command
  updating them all.

## Impact

- `src/skill_graft/pipeline/compute.py`: `check_refs`, through `compute_hull` shared by `build`, `resolve`, `tree`,
  `explain`, the edit commands and `update`.
- `src/skill_graft/commands/update.py`: passes its flags to `check_refs`.
- `tests/commands/test_update.py`, `tests/cli/test_git_build.py`.
- `CHANGELOG.md` at archive: a `### Fixed` entry; the loop has been there since `update` was added.
