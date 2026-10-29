# update

## MODIFIED Requirements

### Requirement: Report the hull diff

After the per-**Source** lines, `update` SHALL print the **Hull diff** between the current `ref`s and the new tips: the
legend `hull (+ added, - removed, ~ changed):`, then `+ <skill id>`, `- <skill id>` or `~ <skill id>` (hash changed) per
**Skill**, sorted by **Skill ID**; or `hull unchanged`.

Under each `+` and `~` line it SHALL print one line per file whose deployed bytes or executable bit differ, sorted by
path: `<path> (new, <n> bytes)`, `<path> (removed)` or `<path> (changed, <old> -> <new> bytes)`, then `(now executable)`
or `(no longer executable)` where they apply; at most 20 such lines per **Skill**, then `… <n> more`. Each path SHALL be
printed whole and quoted as git's `core.quotePath` quotes it, a name holding a space quoted too, so it is printable
ASCII and two names never print alike. No **Skill** text SHALL be printed, and no diff SHALL be computed for this
summary.

After the **Hull diff**, `update` SHALL read the lock's **Skills** and their hashes, and name each **Skill** that the
old **Hull** and the lock do not hold alike, held by one only or with another hash, in a line
`edited since skill-graft.lock was written, not shown: <skill id>`. A missing or unreadable lock SHALL name every
**Skill** of the old **Hull**.

The diff SHALL never fetch a commit: when a current `ref` is missing or not cached, or the current `ref`s do not
resolve, it SHALL say so instead. Of a current `ref` whose commit is cached, it SHALL fetch only the files it reads and
the cache lacks; when that fails, it SHALL say so, as for `ref`s that do not resolve, and `update` SHALL go on. A
current `ref` not in the cache SHALL be named with its likely causes: a branch fetched since, history rewritten
upstream, or a `ref` set to a commit on no branch. A dry run without `--diff` whose **Hull diff** marks a **Skill** `+`
or `~`, or that has no previous **Hull**, SHALL print, before its `dry run:` line, the hint
`review: skill-graft update --dry-run --diff <file>` with the **Sources** it was given. Warnings SHALL come from the new
tips only. `--dry-run` SHALL print the same.

#### Scenario: Warnings once

- **WHEN** `mp/tdd` calls `/foo` at both the current `ref` and the new tip, and no **Source** has `foo`
- **THEN** `update` prints the `/foo` warning once

#### Scenario: Legend

- **WHEN** `update` adds `mp/grilling` to the **Hull**
- **THEN** the line before `+ mp/grilling` is `hull (+ added, - removed, ~ changed):`

#### Scenario: Nothing changed

- **WHEN** every skill in the **Hull** keeps its hash at the new tips
- **THEN** `update` prints `hull unchanged`, and no hint

#### Scenario: Skill added upstream

- **WHEN** the new tip of `mp` makes `mp/tdd` call `/grilling`, and `mp` has `grilling`
- **THEN** `update` prints `+ mp/grilling` and `~ mp/tdd`

#### Scenario: Skill dropped upstream

- **WHEN** at the current `ref` `mp/tdd` calls `/grilling`, and at the new tip it does not
- **THEN** `update` prints `- mp/grilling`, with no file lines under it

#### Scenario: Old refs unresolvable

- **WHEN** a selected git **Source** had no `ref`
- **THEN** `update` says there is no previous **Hull** to compare, and succeeds

#### Scenario: Old ref not cached

- **WHEN** `mp`'s `ref` A is not in the cache and its new tip B is
- **THEN** `update` says there is no previous **Hull** to compare: `mp`'s `ref` A is not in the cache, with its likely
  causes; and it fetches nothing

#### Scenario: Old ref cached, its files not

- **WHEN** a project **Package**'s lock was written on another machine, `mp`'s `ref` A has never been read on this one,
  and the user runs `update`
- **THEN** `update` fetches the tip, then A's files, and prints the **Hull diff** from A to the tip

#### Scenario: Old ref's files unreachable

- **WHEN** `mp`'s `ref` A is in the cache but its files are not, its new tip B is in the cache with its files, and
  `mp`'s remote is unreachable
- **THEN** `update` says there is no previous **Hull** to compare, naming the failed fetch, and succeeds

#### Scenario: File lines

- **WHEN** at the new tip `mp/tdd`'s `SKILL.md` grows from 120 to 180 bytes, and it gains an executable `run.sh` of 40
  bytes
- **THEN** under `~ mp/tdd` it prints `SKILL.md (changed, 120 -> 180 bytes)` and
  `run.sh (new, 40 bytes) (now executable)`

#### Scenario: Made executable

- **WHEN** at the new tip only `mp/tdd`'s `run.sh` of 40 bytes turns executable
- **THEN** under `~ mp/tdd` it prints `run.sh (changed, 40 -> 40 bytes) (now executable)`

#### Scenario: Many files

- **WHEN** `mp/big` joins the **Hull** with 50 files
- **THEN** under `+ mp/big` it prints 20 file lines, then `… 30 more`

#### Scenario: Lookalike names

- **WHEN** at the new tip `mp/tdd` gains `SKILL.md` followed by a zero-width space, beside its `SKILL.md`
- **THEN** the two lines name `SKILL.md` and `"SKILL.md\342\200\213"`

#### Scenario: Trailing space

- **WHEN** at the new tip `mp/tdd` gains `run.sh` followed by a space, beside its `run.sh`
- **THEN** the two lines name `run.sh` and `"run.sh "`

#### Scenario: Path source edited since the lock

- **WHEN** after the lock was written, `own/notes`' `SKILL.md`, of a path **Source**, changed, and the user runs
  `update --dry-run`
- **THEN** it prints `edited since skill-graft.lock was written, not shown: own/notes`

#### Scenario: Skill left since the lock

- **WHEN** after the lock was written, an **Entry** `mp/x` was removed from the config, and the user runs
  `update --dry-run`
- **THEN** it names `mp/x` as edited since the lock was written

#### Scenario: Nothing edited since the lock

- **WHEN** nothing changed since `update` last wrote the lock, and the user runs `update --dry-run`
- **THEN** it names no **Skill** as edited since the lock was written

#### Scenario: Hint

- **WHEN** `mp/tdd` changes at the new tip and the user runs `update mp --dry-run` without `--diff`
- **THEN** it prints `review: skill-graft update mp --dry-run --diff <file>`, then its `dry run:` line

#### Scenario: No hint after a real update

- **WHEN** `mp/tdd` changes at the new tip and the user runs `update` without `--dry-run`
- **THEN** it prints no hint

## ADDED Requirements

### Requirement: Dry run on a remote refusing files by name

When `update --dry-run` needs files at a tip or a current `ref` from a remote that refuses files asked by name, it SHALL
exit non-zero, its error naming the alias and saying to run `update` without `--dry-run`, and SHALL write nothing to the
cache, as any dry run.

#### Scenario: Dry run, remote refusing files by name

- **WHEN** `mp`'s remote accepts a partial clone but refuses files asked by name, the cache holds `mp`'s repository
  without the files of its new tip, and the user runs `update --dry-run`
- **THEN** it exits non-zero naming `mp` and saying to run `update` without `--dry-run`, and the cache folder is
  unchanged
