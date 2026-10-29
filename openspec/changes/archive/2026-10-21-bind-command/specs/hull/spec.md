## MODIFIED Requirements

### Requirement: Else exactly one other source

When the own **Source** lacks the name, the **Reference** SHALL resolve in the one other declared **Source** having it.
Several SHALL be an error naming the referencing **Skill**, the **Reference**, the matching **Skill IDs**, and the
`skill-graft bind` command that would settle it. A **Source** has a name when a **Skill** there is named so, or one
whose name cannot be read sits in a folder so named; a name read but invalid never counts.

#### Scenario: One other source

- **WHEN** `mp/tdd` calls `/notes`, `mp` has no `notes`, and only `own` has one
- **THEN** `own/notes` is in the **Hull**

#### Scenario: Invalid name does not count

- **WHEN** `mp/tdd` calls `/grilling`, `mp`'s folder `grilling/` has `name: "Grilling Tool"`, and `own` has `grilling`
- **THEN** `own/grilling` is in the **Hull**

#### Scenario: Several other sources

- **WHEN** `mp/tdd` calls `/notes`, `mp` has no `notes`, and both `own` and `x` have one
- **THEN** the command exits non-zero naming `mp/tdd`, `/notes`, `own/notes`, `x/notes` and
  `skill-graft bind mp/notes <source>/<name>`, and writes nothing

### Requirement: Unmatched references warn

A slash or Skill tool **Reference** matching no **Skill** in any declared **Source**, and no **Bind**, SHALL be a
warning `` `<skill id>` calls `<reference>`: no declared source has a skill `<name>` ``, the **Reference** as first
written (`/<name>` or `Skill(<name>)`), ending with the `skill-graft bind` command that would ignore it, once per
referencing **Skill** and name, and the command SHALL proceed.

#### Scenario: No such skill

- **WHEN** `mp/tdd` calls `/foo` twice, and no **Source** has a **Skill** `foo`
- **THEN** the command prints `` `mp/tdd` calls `/foo`: no declared source has a skill `foo` `` and
  `skill-graft bind mp/foo false` once, and succeeds

#### Scenario: Skill tool form named

- **WHEN** `mp/tdd` holds only `Skill(foo)`, and no **Source** has `foo`
- **THEN** the warning says `` `mp/tdd` calls `Skill(foo)` ``

### Requirement: Binds override resolution

A **Bind** `"<a>/<name>" = "<b>/<target>"` SHALL make every slash, Skill tool and prose **Reference** to `<name>` from a
**Skill** in **Source** `a` resolve to `b/<target>`, whatever the default would give, error or no match included. The
target of every **Bind**, whether a **Reference** uses it or not, SHALL be found as an **Entry** is; a missing or
ambiguous one is an error naming the **Bind**. A bound prose **Reference** still never extends the **Hull**.

#### Scenario: Bind across sources

- **WHEN** `mp/tdd` calls `/grilling`, `mp` has `grilling`, and `[bind]` has `"mp/grilling" = "own/grill"`
- **THEN** `own/grill` is in the **Hull** and `mp/grilling` is not

#### Scenario: Bind settles ambiguity

- **WHEN** `/notes` from `mp` would match `own/notes` and `x/notes`, and `[bind]` has `"mp/notes" = "x/notes"`
- **THEN** `x/notes` is in the **Hull**, and the command succeeds

#### Scenario: Bind to a missing skill

- **WHEN** `[bind]` has `"mp/grilling" = "own/nope"`, a **Hull** **Skill** in `mp` calls `/grilling`, and `own` has no
  `nope`
- **THEN** the command exits non-zero naming `mp/grilling` and `own/nope`

#### Scenario: Unused bind to a missing skill

- **WHEN** `[bind]` has `"mp/grill" = "own/nope"`, no **Hull** **Skill** in `mp` calls `/grill`, and `own` has no `nope`
- **THEN** the command exits non-zero naming `mp/grill` and `own/nope`, and writes nothing

#### Scenario: Bound prose

- **WHEN** `mp/tdd` mentions `` `notes` ``, `mp` has no `notes`, `[bind]` has `"mp/notes" = "own/notes"`, and
  `own/notes` is in the **Hull**
- **THEN** the **Hull** has a `prose` edge `mp/tdd` → `own/notes` with `bind = true`

#### Scenario: Bound prose outside the hull

- **WHEN** `mp/tdd` only mentions `` `notes` ``, and `[bind]` has `"mp/notes" = "own/notes"`
- **THEN** `own/notes` is not in the **Hull**, and is suggested

#### Scenario: Prose bound to nothing

- **WHEN** `mp/tdd` holds `pre-commit run`, `mp` has `pre-commit`, and `[bind]` has `"mp/pre-commit" = false`
- **THEN** it is no **Reference**: no edge and no suggestion

### Requirement: Unused binds warn

A **Bind** that no **Reference** from a **Hull** **Skill** uses, prose included, SHALL be a warning naming its key.

#### Scenario: Typo in a bind

- **WHEN** `[bind]` has `"mp/grill" = "own/grilling"`, `own` has `grilling`, and no **Hull** **Skill** in `mp` calls
  `/grill`
- **THEN** the command warns that `mp/grill` binds no **Reference**, and succeeds

#### Scenario: Used by prose only

- **WHEN** `[bind]` has `"mp/notes" = "own/notes"` and a **Hull** **Skill** in `mp` only mentions `` `notes` ``
- **THEN** the command gives no warning about that **Bind**
