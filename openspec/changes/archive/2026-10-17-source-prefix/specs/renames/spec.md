## ADDED Requirements

### Requirement: A prefix covers its source's hull skills

A **Source**'s **Prefix** SHALL apply to every **Hull** **Skill** of it without a `[rename]` key, whether an **Entry**
or reached through a **Reference**, and its **Deployed name** SHALL be carried into its folder, `name:` and every
**Reference** as a **Rename**'s is. **Skill IDs**, **Binds** and **Patches** SHALL keep upstream names.

#### Scenario: Dependency prefixed

- **WHEN** `[sources.mp]` has `prefix = "mp-"`, **Entry** `mp/tdd` calls `/grilling`, and no `[rename]` key names either
- **THEN** `build` vendors `.apm/skills/mp-tdd/` and `.apm/skills/mp-grilling/`, their `name:` lines are `mp-tdd` and
  `mp-grilling`, and the vendored `mp-tdd/SKILL.md` holds `/mp-grilling` where it held `/grilling`

#### Scenario: Prose follows the prefix

- **WHEN** `[sources.mp]` has `prefix = "mp-"`, and `mp/tdd` holds `` `grilling` `` with `mp/grilling` in the **Hull**
- **THEN** the vendored copy holds `` `mp-grilling` ``

#### Scenario: Bound to a prefixed skill

- **WHEN** `[sources.own]` has `prefix = "own-"`, `[bind]` has `"mp/grilling" = "own/grill"`, and `mp/tdd` calls
  `/grilling`
- **THEN** the vendored `tdd/SKILL.md` holds `/own-grill`

#### Scenario: Other sources untouched

- **WHEN** `[sources.mp]` has `prefix = "mp-"`, and `own/notes` is in the **Hull** with no `[rename]` key
- **THEN** its **Deployed name** is `notes`

## MODIFIED Requirements

### Requirement: Deployed name

A **Skill**'s **Deployed name** SHALL be its `[rename]` value when one names its **Skill ID**, else its **Source**'s
`prefix` followed by its name when the **Source** has one, else its name.

#### Scenario: Renamed

- **WHEN** `[rename]` has `"mp/grilling" = "mp-grilling"` and `mp/grilling` is in the **Hull**
- **THEN** its **Deployed name** is `mp-grilling`

#### Scenario: Not renamed

- **WHEN** no `[rename]` key names `own/notes` and `[sources.own]` has no `prefix`
- **THEN** its **Deployed name** is `notes`

#### Scenario: Prefixed

- **WHEN** `[sources.mp]` has `prefix = "mp-"` and no `[rename]` key names `mp/tdd`
- **THEN** its **Deployed name** is `mp-tdd`

#### Scenario: Prefix used as written

- **WHEN** `[sources.mp]` has `prefix = "mp"` and no `[rename]` key names `mp/tdd`
- **THEN** its **Deployed name** is `mptdd`

#### Scenario: Rename wins over the prefix

- **WHEN** `[sources.mp]` has `prefix = "mp-"` and `[rename]` has `"mp/tdd" = "tdd"`
- **THEN** its **Deployed name** is `tdd`

### Requirement: Renamed folder and name

`build` SHALL vendor each **Hull** **Skill** to `.apm/skills/<deployed name>/`. The `SKILL.md` of a **Skill** whose
**Deployed name** differs from its name SHALL carry `name: <deployed name>`, quoted when YAML would read the bare name
as anything but that string (`true`, `null`, `123`): an existing `name:` line replaced, else inserted as the front
matter's first line, else a front matter of just that line prepended. Any other **Skill**'s `name:` SHALL be unchanged.

#### Scenario: Name line replaced

- **WHEN** `mp/grilling`'s `SKILL.md` has `name: grilling # upstream` and is renamed to `mp-grilling`
- **THEN** `.apm/skills/mp-grilling/SKILL.md` has `name: mp-grilling` and is otherwise unchanged

#### Scenario: Name YAML would misread

- **WHEN** `mp/tdd` is renamed to `true`
- **THEN** the vendored `SKILL.md` has `name: "true"`

#### Scenario: Front matter without a name

- **WHEN** a renamed **Skill**'s `SKILL.md` has front matter holding only `description: x`
- **THEN** the vendored front matter is `name: <deployed name>` then `description: x`

#### Scenario: No front matter

- **WHEN** a renamed **Skill**'s `SKILL.md` has no front matter
- **THEN** the vendored `SKILL.md` starts with `---`, `name: <deployed name>`, `---`, then the upstream text

#### Scenario: Prefixed name line

- **WHEN** `mp/grilling`'s `SKILL.md` has `name: grilling`, and `[sources.mp]` has `prefix = "mp-"`
- **THEN** `.apm/skills/mp-grilling/SKILL.md` has `name: mp-grilling`

### Requirement: Deployed names are unique

Two **Hull** **Skills** with the same **Deployed name**, compared ignoring case, SHALL be an error naming both and a
change that would separate them, and the command SHALL then write nothing. The hint SHALL name a `[rename]` line for a
clashing **Skill** with neither a `[rename]` key nor a **Prefix**; else the `[rename]` value of a renamed one to change;
else, for a prefixed one, that a `[rename]` key for it would, or its **Source**'s `prefix` unless another clashing
**Skill** is of that **Source**.

#### Scenario: Clash across sources

- **WHEN** `mp/tdd` and `own/tdd` are both **Entries**, neither renamed
- **THEN** `build` exits non-zero naming both and `[rename]`, and leaves `.apm/skills/` and the lock unchanged

#### Scenario: Clash through a reference

- **WHEN** **Entry** `own/grilling` exists, and **Entry** `mp/tdd` calls `/grilling`, resolved to `mp/grilling`
- **THEN** `build` exits non-zero naming `mp/grilling` and `own/grilling`

#### Scenario: Rename settles a clash

- **WHEN** `mp/tdd` and `own/tdd` are both **Entries**, and `[rename]` has `"own/tdd" = "own-tdd"`
- **THEN** `build` vendors `tdd/` and `own-tdd/`, and exits 0

#### Scenario: Rename onto another skill's name

- **WHEN** `[rename]` has `"mp/grilling" = "Notes"`, and `own/notes` is in the **Hull**
- **THEN** the command exits non-zero naming `mp/grilling` and `own/notes`, and suggests `"own/notes" = "own-notes"`

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
- **THEN** the command exits non-zero naming `a/tdd` and `b/tdd`, and says to add a `[rename]` key for one of them or
  change its **Source**'s `prefix = "x-"`

#### Scenario: Clash within one prefixed source

- **WHEN** `[sources.mp]` has `prefix = "mp-"`, and **Entries** `mp/Tdd` and `mp/tdd` have no `[rename]` key
- **THEN** the command exits non-zero saying to add a `[rename]` key for one of them, and names no `prefix`

### Requirement: The user's reserved names are errors

A **Deployed name** equal, ignoring case, to a name in the user's `reserved` list SHALL be an error naming the
**Skill**, the name, and the change that would avoid it, chosen as the uniqueness hint chooses it for that one
**Skill**, and the command SHALL then write nothing.

#### Scenario: Reserved by the user

- **WHEN** `reserved = ["review"]` and `mp/review` is in the **Hull**, not renamed
- **THEN** `resolve` and `build` exit non-zero naming `mp/review`, `review` and `"mp/review" = "mp-review"`

#### Scenario: Renamed out of the way

- **WHEN** `reserved = ["review"]` and `[rename]` has `"mp/review" = "mp-review"`
- **THEN** the command succeeds

#### Scenario: Prefixed onto a reserved name

- **WHEN** `reserved = ["mp-review"]`, `[sources.mp]` has `prefix = "mp-"`, and `mp/review` is in the **Hull** with no
  `[rename]` key
- **THEN** the command exits non-zero naming `mp/review` and `mp-review`, and says to add a `[rename]` key for it or
  change `[sources.mp] prefix = "mp-"`

### Requirement: Shipped reserved names warn

skill-graft SHALL ship a list of **Reserved names**: the built-in commands and bundled skills of Claude Code and Codex,
`code-review` among them. A **Deployed name** equal to one, ignoring case, SHALL be a warning naming the **Skill** and
the name; the warning of a **Skill** with neither a `[rename]` key nor a **Prefix** SHALL end with
`"<alias>/<name>" = "<alias>-<name>"` under `[rename]`. The command SHALL proceed.

#### Scenario: Shipped clash

- **WHEN** `mp/code-review` is in the **Hull**, not renamed
- **THEN** the command warns naming `mp/code-review`, `code-review` and `"mp/code-review" = "mp-code-review"`, and
  succeeds

#### Scenario: Renamed onto a shipped name

- **WHEN** `[rename]` has `"mp/check" = "review"`
- **THEN** the command warns naming `mp/check` and `review`, suggests no rename, and succeeds

#### Scenario: Both lists

- **WHEN** `reserved = ["code-review"]` and `mp/code-review` is in the **Hull**, not renamed
- **THEN** the command exits non-zero, as the user's list decides

#### Scenario: Prefixed onto a shipped name

- **WHEN** `[sources.own]` has `prefix = "re"` and `own/view` is in the **Hull** with no `[rename]` key
- **THEN** the command warns naming `own/view` and `review`, suggests no rename, and succeeds
