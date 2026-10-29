# Spec Delta

## Purpose

Moves each git **Source**'s **Ref** to the tip of its branch, on purpose, keeping the user's TOML as they wrote it.

## ADDED Requirements

### Requirement: Move refs to branch tips

`skill-graft update [alias…]` SHALL fetch each selected git **Source** and set its `ref` to the tip of its `branch`, or,
without `branch`, of the remote's default branch as the remote reports it now. With no alias, every git **Source** is
selected and path **Sources** are skipped. A git **Source** without `ref` is updated like any other.

#### Scenario: New commit upstream

- **WHEN** `ref` names commit A and the default branch's tip is commit B
- **THEN** after `update`, `ref` is B

#### Scenario: Named branch

- **WHEN** `[sources.mp]` has `branch = "dev"` and `dev`'s tip differs from the default branch's
- **THEN** `ref` becomes `dev`'s tip

#### Scenario: Default branch renamed

- **WHEN** the remote's default branch changes from `master` to `main` between two `update`s
- **THEN** the second `update` sets `ref` to `main`'s tip

#### Scenario: Source without a ref

- **WHEN** `[sources.mp]` has `git` and no `ref`
- **THEN** `update` adds `ref` with the default branch's tip, and `build` then succeeds

#### Scenario: Only the named sources

- **WHEN** sources `a` and `b` both have new commits and the user runs `update a`
- **THEN** only `a`'s `ref` changes

### Requirement: Selection errors

An alias naming a path **Source** or no declared **Source**, an unselected git **Source** without `ref` (it cannot be
resolved), a `branch` that is not a valid branch name (revision syntax such as `main~3` included), a `branch` the remote
lacks (including one deleted since an earlier fetch), and a remote that reports no default branch when `branch` is
absent SHALL be errors naming the alias, and `update` SHALL then write nothing. The first three SHALL be reported before
any remote is contacted.

#### Scenario: Path source named

- **WHEN** `own` is a path source and the user runs `update own`
- **THEN** `update` exits non-zero saying `own` is a path source, and writes nothing

#### Scenario: Unknown alias

- **WHEN** the user runs `update nope` and no `[sources.nope]` exists
- **THEN** `update` exits non-zero naming `nope`

#### Scenario: Missing branch

- **WHEN** `[sources.mp]` has `branch = "gone"` and the remote has no such branch
- **THEN** `update` exits non-zero naming `mp` and `gone`, and writes nothing

#### Scenario: Revision syntax as branch

- **WHEN** `[sources.mp]` has `branch = "main~3"` or `branch = "main@{1}"`
- **THEN** `update` exits non-zero naming `sources.mp.branch`, before contacting the remote

#### Scenario: Branch deleted upstream

- **WHEN** an earlier `update` fetched branch `dev` of `mp`, `dev` was then deleted upstream, and `mp` has
  `branch = "dev"`
- **THEN** `update` exits non-zero naming `mp` and `dev`, and writes nothing

#### Scenario: Other source without a ref

- **WHEN** `a` has a `ref`, git source `b` has none, and the user runs `update a`
- **THEN** `update` exits non-zero naming `b` and `skill-graft update b`, before fetching

#### Scenario: No default branch

- **WHEN** `mp` has no `branch` and the remote's `HEAD` names no existing branch
- **THEN** `update` exits non-zero naming `mp` and suggesting a `branch` key

#### Scenario: Tip already cached

- **WHEN** the tip of `mp`'s branch is already in the cache
- **THEN** `update` asks the remote only for its branches' tips, and fetches nothing

### Requirement: Resolve before writing

`update` SHALL resolve every **Entry** as `build` does, with each selected **Source** at its new tip and every other at
its current `ref`, and SHALL write `skill-graft.toml` only when that succeeds. On failure it SHALL exit non-zero with
the resolution error and the shas it would have written, leaving the TOML unchanged. `update` SHALL NOT vendor or run
`apm`.

#### Scenario: Entry gone upstream

- **WHEN** `mp/tdd` is an **Entry** and the new tip of `mp` has no skill `tdd`
- **THEN** `update` exits non-zero naming `mp/tdd`, prints the new sha, and leaves `skill-graft.toml` byte for byte
  unchanged

#### Scenario: No deploy

- **WHEN** `update` succeeds
- **THEN** `.apm/skills/` is unchanged and `apm` is not run

### Requirement: Edit the TOML in place

`update` SHALL change only the `ref` values of the updated **Sources**, adding a missing `ref` to its source table, and
SHALL keep every comment, blank line, key order and other formatting. The file SHALL be replaced atomically, and not
rewritten when no `ref` changed. A symlinked `skill-graft.toml` SHALL stay a symlink: its target is what changes.

#### Scenario: Comments survive

- **WHEN** `skill-graft.toml` has comments, including one trailing the `ref` line, and `update` moves `mp`'s `ref`
- **THEN** the new file equals the old one with only that sha replaced

#### Scenario: Symlinked config

- **WHEN** `skill-graft.toml` is a symlink to a file elsewhere and `update` moves a `ref`
- **THEN** `skill-graft.toml` is still that symlink, and the file it points to holds the new sha

#### Scenario: Nothing new

- **WHEN** every selected source's tip equals its `ref`
- **THEN** `skill-graft.toml` keeps its bytes and modification time

### Requirement: Report each source

`update` SHALL print one line per selected git **Source**: its alias and the sha its `ref` now names, marked
`(unchanged)` when it did not move.

#### Scenario: Output

- **WHEN** `update` moves `a` to sha B and `b` stays at sha C
- **THEN** it prints `a B` and `b C (unchanged)`

### Requirement: Dry run writes nothing

`update --dry-run` SHALL do everything `update` does, printing the same lines and errors and exiting with the same code,
but SHALL write neither `skill-graft.toml` nor the cache, nor anything outside a temporary folder it removes before
exiting. It SHALL read what the cache already holds, and contact a remote exactly when `update` would. It SHALL say that
the TOML was not written.

#### Scenario: Dry run

- **WHEN** the default branch has moved and the user runs `update --dry-run`
- **THEN** it prints the new sha and that it wrote nothing, and `skill-graft.toml` and the cache folder are unchanged

#### Scenario: Dry run with an unreachable unselected source

- **WHEN** `b`'s `ref` is in the cache, `b`'s remote is unreachable, and the user runs `update a --dry-run`
- **THEN** it succeeds as `update a` would, reading `b` from the cache

#### Scenario: Dry run with a failing entry

- **WHEN** an **Entry** is gone at the new tip and the user runs `update --dry-run`
- **THEN** it exits non-zero naming the **Entry**, as `update` would
