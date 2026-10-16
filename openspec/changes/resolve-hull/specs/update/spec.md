# Spec Delta

## ADDED Requirements

### Requirement: Report the hull diff

After the per-**Source** lines, `update` SHALL print the **Hull** diff between the current `ref`s and the new
tips: the legend `hull (+ added, - removed, ~ changed):`, then `+ <skill id>`, `- <skill id>` or `~ <skill id>`
(hash changed) per **Skill**, sorted by **Skill ID**; or `hull unchanged`. When the current `ref`s do not
resolve, it SHALL say so instead. `--dry-run` SHALL print the same.

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

## MODIFIED Requirements

### Requirement: Resolve before writing

`update` SHALL resolve the **Hull** as `build` does, with each selected **Source** at its new tip and every other
at its current `ref`, and SHALL write `skill-graft.toml` and `skill-graft.lock` only when that succeeds. On
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

#### Scenario: No deploy

- **WHEN** `update` succeeds
- **THEN** `.apm/skills/` is unchanged and `apm` is not run
