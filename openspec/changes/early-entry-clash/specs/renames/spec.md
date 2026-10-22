# Spec Delta

## MODIFIED Requirements

### Requirement: Deployed names are unique

Two **Hull** **Skills** with the same **Deployed name**, compared ignoring case, SHALL be an error naming both
and a change that would separate them, and the command SHALL then write nothing. `build`, `resolve` and `update` SHALL
report a clash between **Entries** before any **Source** is read or a remote contacted. The hint SHALL name a
`[rename]` line for a clashing **Skill** with neither a `[rename]` key nor a **Prefix**; else the `[rename]` value of a
renamed one to change; else, for a prefixed one, that a `[rename]` key for it would, or its **Source**'s `prefix`
unless another clashing **Skill** is of that **Source**.

#### Scenario: Clash across sources

- **WHEN** `mp/tdd` and `own/tdd` are both **Entries**, neither renamed
- **THEN** `build` exits non-zero naming both and `[rename]`, and leaves `.apm/skills/` and the lock unchanged

#### Scenario: Entries clash before any fetch

- **WHEN** **Entries** `mp/tdd` and `own/tdd` have no `[rename]` key, and `mp` is a git **Source** whose `ref` is
  not cached
- **THEN** `build` exits non-zero naming both, and fetches nothing

#### Scenario: Entries clash before update fetches

- **WHEN** **Entries** `mp/tdd` and `own/tdd` have no `[rename]` key, `mp` is a git **Source**, and the user runs
  `update mp`
- **THEN** `update` exits non-zero naming both, contacts no remote, and writes nothing

#### Scenario: Clash through a reference

- **WHEN** **Entry** `own/grilling` exists, and **Entry** `mp/tdd` calls `/grilling`, resolved to `mp/grilling`
- **THEN** `build` exits non-zero naming `mp/grilling` and `own/grilling`

#### Scenario: Rename settles a clash

- **WHEN** `mp/tdd` and `own/tdd` are both **Entries**, and `[rename]` has `"own/tdd" = "own-tdd"`
- **THEN** `build` vendors `tdd/` and `own-tdd/`, and exits 0

#### Scenario: Rename onto another skill's name

- **WHEN** `[rename]` has `"mp/grilling" = "Notes"`, and `own/notes` is in the **Hull**
- **THEN** the command exits non-zero naming `mp/grilling` and `own/notes`, and suggests
  `"own/notes" = "own-notes"`

#### Scenario: Clash of two renames

- **WHEN** `[rename]` has `"mp/a" = "x"` and `"own/b" = "x"`
- **THEN** the command exits non-zero saying to change `[rename] "own/b" = "x"`

#### Scenario: Prefix onto another skill's name

- **WHEN** `[sources.mp]` has `prefix = "mp-"`, and **Entries** `mp/tdd` and `own/mp-tdd` have no `[rename]` key
- **THEN** the command exits non-zero naming both and suggests `"own/mp-tdd" = "own-mp-tdd"`, never
  `"mp/tdd" = "mp-tdd"`

#### Scenario: Two sources, one prefix

- **WHEN** `[sources.a]` and `[sources.b]` both have `prefix = "x-"`, and **Entries** `a/tdd` and `b/tdd` have no
  `[rename]` key
- **THEN** the command exits non-zero naming `a/tdd` and `b/tdd`, and says to add a `[rename]` key for one of
  them or change its **Source**'s `prefix = "x-"`

#### Scenario: Clash within one prefixed source

- **WHEN** `[sources.mp]` has `prefix = "mp-"`, and **Entries** `mp/Tdd` and `mp/tdd` have no `[rename]` key
- **THEN** the command exits non-zero saying to add a `[rename]` key for one of them, and names no `prefix`
