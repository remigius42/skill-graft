# update Specification

## Purpose

Moves each git **Source**'s **Ref** to the tip of its branch, on purpose, keeping the user's TOML as they wrote
it.

## Requirements

### Requirement: Move refs to branch tips

`skill-graft update [alias…]` SHALL fetch each selected git **Source** and set its `ref` to the tip of its
`branch`, or, without `branch`, of the remote's default branch as the remote reports it now. With no alias,
every git **Source** is selected and path **Sources** are skipped. A git **Source** without `ref` is updated
like any other.

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

An alias naming a path **Source** or no declared **Source**, an unselected git **Source** without `ref` (it
cannot be resolved), a `branch` that is not a valid branch name (revision syntax such as `main~3` included), a
`branch` the remote lacks (including one deleted since an earlier fetch), and a remote that reports no default
branch when `branch` is absent SHALL be errors naming the alias, and `update` SHALL then write nothing. The
first three SHALL be reported before any remote is contacted.

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

`update` SHALL resolve the **Hull** as `build` does, with each selected **Source** at its new tip and every other
at its current `ref`. Only when that succeeds SHALL it write `skill-graft.lock`, always, and `skill-graft.toml`,
when a `ref` moved. On
failure it SHALL exit non-zero with the resolution error and the shas it would have written, leaving the TOML
and the lock unchanged. `update` SHALL NOT vendor or run `apm`.

#### Scenario: Entry gone upstream

- **WHEN** `mp/tdd` is an **Entry** and the new tip of `mp` has no skill `tdd`
- **THEN** `update` exits non-zero naming `mp/tdd`, prints the new sha, and leaves `skill-graft.toml` byte for
  byte unchanged

#### Scenario: Reference turns ambiguous upstream

- **WHEN** at the new tip of `x`, a skill `notes` appears that `own` also has, and a **Hull** **Skill** in `mp`
  calls `/notes`
- **THEN** `update` exits non-zero naming `/notes` and both **Skill IDs**, and leaves the TOML and lock unchanged

#### Scenario: Lock follows the TOML

- **WHEN** `update` moves `mp`'s `ref` to B
- **THEN** `skill-graft.lock` records B

#### Scenario: Lock written though no ref moved

- **WHEN** no `ref` moves, but a path **Source**'s skill changed since the last lock
- **THEN** `skill-graft.toml` keeps its bytes, and `skill-graft.lock` holds the new hash

#### Scenario: No deploy

- **WHEN** `update` succeeds
- **THEN** `.apm/skills/` is unchanged and `apm` is not run

### Requirement: Edit the TOML in place

`update` SHALL change only the `ref` values of the updated **Sources**, adding a missing `ref` to its source
table, and SHALL keep every comment, blank line, key order and other formatting. The file SHALL be replaced
atomically, and not rewritten when no `ref` changed. A symlinked `skill-graft.toml` SHALL stay a symlink:
its target is what changes.

#### Scenario: Comments survive

- **WHEN** `skill-graft.toml` has comments, including one trailing the `ref` line, and `update` moves `mp`'s
  `ref`
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

`update --dry-run` SHALL do everything `update` does, printing the same lines and errors and exiting with the
same code, but SHALL write neither `skill-graft.toml`, `skill-graft.lock` nor the cache, nor anything outside a
temporary folder it removes before exiting. It SHALL read what the cache already holds, and contact a remote
exactly when `update` would. It SHALL say that the TOML and the lock were not written.

#### Scenario: Dry run

- **WHEN** the default branch has moved and the user runs `update --dry-run`
- **THEN** it prints the new sha and `dry run: skill-graft.toml and skill-graft.lock not written`, and
  `skill-graft.toml`, `skill-graft.lock` and the cache folder are unchanged

#### Scenario: Dry run with an unreachable unselected source

- **WHEN** `b`'s `ref` is in the cache, `b`'s remote is unreachable, and the user runs `update a --dry-run`
- **THEN** it succeeds as `update a` would, reading `b` from the cache

#### Scenario: Dry run with a failing entry

- **WHEN** an **Entry** is gone at the new tip and the user runs `update --dry-run`
- **THEN** it exits non-zero naming the **Entry**, as `update` would

### Requirement: Report the hull diff

After the per-**Source** lines, `update` SHALL print the **Hull** diff between the current `ref`s and the new
tips: the legend `hull (+ added, - removed, ~ changed):`, then `+ <skill id>`, `- <skill id>` or `~ <skill id>`
(hash changed) per **Skill**, sorted by **Skill ID**; or `hull unchanged`. The diff SHALL never fetch: when a
current `ref` is missing or not cached, or the current `ref`s do not resolve, it SHALL say so instead. Warnings
SHALL come from the new tips only. `--dry-run` SHALL print the same.

#### Scenario: Warnings once

- **WHEN** `mp/tdd` calls `/foo` at both the current `ref` and the new tip, and no **Source** has `foo`
- **THEN** `update` prints the `/foo` warning once

#### Scenario: Legend

- **WHEN** `update` adds `mp/grilling` to the **Hull**
- **THEN** the line before `+ mp/grilling` is `hull (+ added, - removed, ~ changed):`

#### Scenario: Nothing changed

- **WHEN** every skill in the **Hull** keeps its hash at the new tips
- **THEN** `update` prints `hull unchanged`

#### Scenario: Skill added upstream

- **WHEN** the new tip of `mp` makes `mp/tdd` call `/grilling`, and `mp` has `grilling`
- **THEN** `update` prints `+ mp/grilling` and `~ mp/tdd`

#### Scenario: Skill dropped upstream

- **WHEN** at the current `ref` `mp/tdd` calls `/grilling`, and at the new tip it does not
- **THEN** `update` prints `- mp/grilling`

#### Scenario: Old refs unresolvable

- **WHEN** a selected git **Source** had no `ref`
- **THEN** `update` says there is no previous **Hull** to compare, and succeeds

#### Scenario: Old ref not cached

- **WHEN** `mp`'s `ref` A is not in the cache and its new tip B is
- **THEN** `update` says there is no previous **Hull** to compare (`mp` `ref` not cached), and fetches nothing

### Requirement: Patches at the new tips

A patch failing at the new tips SHALL fail `update` as any resolution error does, leaving the TOML and the lock
unchanged, and the error SHALL name each failing **Skill**'s **Upstream** folder at the tip, to redo the patch
against. When that folder is in a dry run's temporary cache, it SHALL say instead to run `update` without
`--dry-run` to fetch the tip.

#### Scenario: Patch fails at the tip

- **WHEN** the new tip of `mp` changes the lines a patch to `mp/tdd` replaces
- **THEN** `update` exits non-zero naming the hunk and `mp/tdd`'s folder in the cache export of the new tip, and
  `skill-graft.toml` and `skill-graft.lock` keep their bytes

#### Scenario: Patch redone

- **WHEN** after that failure the user rewrites the patch against the named folder and runs `update` again
- **THEN** `update` moves `mp`'s `ref` to the tip and writes the lock

#### Scenario: Dry run with a failing patch

- **WHEN** the new tip was not cached before, a patch fails there, and the user runs `update --dry-run`
- **THEN** it exits non-zero naming the hunk and saying to run `update` without `--dry-run` to fetch the tip

### Requirement: Hull diff when patches fail at the current refs

When today's **Patches** fail at the current `ref`s, the hull diff SHALL say only
`no previous hull to compare (patches fail at the current refs)`, without the failing hunks, and `update` SHALL
go on as when the current `ref`s do not resolve. When another error stops the walk there as well, it SHALL say
that the current `ref`s do not resolve, that patches fail there, and the other error.

#### Scenario: Patch already rewritten for the tip

- **WHEN** the user rewrote a patch against the new tip of `mp` and runs `update`
- **THEN** it prints `no previous hull to compare (patches fail at the current refs)`, moves `mp`'s `ref` and
  writes the lock

#### Scenario: Another error at the current refs

- **WHEN** at the current `ref`s a patch to **Entry** `mp/tdd` fails, and **Entry** `mp/notes` calls `/y`, bound
  to `mp/x`, which only the new tip has
- **THEN** `update` prints that the current `ref`s do not resolve, that patches fail there, and names `mp/x`;
  it moves `mp`'s `ref`
