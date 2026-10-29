# Spec Delta

## ADDED Requirements

### Requirement: A checked Skill ID reads only its Source

`rename` SHALL check its **Skill ID**, and `bind` its target **Skill ID**, by reading only that **Skill**'s **Source**,
fetching only a commit missing from the cache, before any other **Source** is read or its `ref` checked. A **Skill**
missing from its **Source** SHALL be reported before another **Source**'s missing `ref` or failed fetch. A no-op SHALL
read no other **Source**. A git **Source** of that **Skill** without a `ref` SHALL fail as `build` does, naming every
git **Source** without one.

#### Scenario: Unknown skill before another source's missing ref

- **WHEN** git **Source** `other` has no `ref`, **Source** `mp` has no **Skill** `nope`, and the user runs
  `skill-graft rename mp/nope x`
- **THEN** it exits non-zero naming `mp/nope` and not `other`, and `skill-graft.toml` is unchanged

#### Scenario: Unknown target before another source's missing ref

- **WHEN** git **Source** `other` has no `ref`, **Source** `own` has no **Skill** `nope`, and the user runs
  `skill-graft bind mp/grilling own/nope`
- **THEN** it exits non-zero naming `own/nope` and not `other`, and `skill-graft.toml` is unchanged

#### Scenario: Known skill, another source without a ref

- **WHEN** git **Source** `other` has no `ref`, `mp/notes` exists, and the user runs `skill-graft rename mp/notes n`
- **THEN** it exits non-zero naming `other` and `skill-graft update other`, and `skill-graft.toml` is unchanged

#### Scenario: No-op bind ignores other sources

- **WHEN** `[bind]` has `"mp/grilling" = "own/grill"`, `own` has `grill`, git **Source** `other` has no `ref`, and the
  user runs `skill-graft bind mp/grilling own/grill`
- **THEN** it exits 0 with the already-bound notice, and `skill-graft.toml` keeps its bytes

#### Scenario: No-op rename fetches no other source

- **WHEN** `mp/tdd` deploys as `tdd`, git **Source** `other`'s `ref` is not cached and its remote is unreachable, and
  the user runs `skill-graft rename mp/tdd tdd`
- **THEN** it exits 0 with the already-deploys notice, contacts no remote, and `skill-graft.toml` keeps its bytes

#### Scenario: The skill's own source without a ref

- **WHEN** git **Sources** `mp` and `other` have no `ref`, and the user runs `skill-graft rename mp/tdd t`
- **THEN** it exits non-zero naming `mp`, `other` and `skill-graft update mp other`, and contacts no remote
