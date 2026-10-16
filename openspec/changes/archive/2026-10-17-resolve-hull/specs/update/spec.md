# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

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
