## MODIFIED Requirements

### Requirement: A prefix covers its source's hull skills

A **Source**'s **Prefix** SHALL apply to every **Hull** **Skill** of it without a `[rename]` key, whether an **Entry**
or reached through a **Reference**, and its **Deployed name** SHALL be carried into its folder, `name:` and every
**Reference** as a **Rename**'s is. **Skill IDs**, **Binds** and **Patches** SHALL keep upstream names.

#### Scenario: Dependency prefixed

- **WHEN** `[sources.mp]` has `prefix = "mp-"`, **Entry** `mp/tdd` calls `/grilling`, and no `[rename]` key names either
- **THEN** `deploy` vendors `.apm/skills/mp-tdd/` and `.apm/skills/mp-grilling/`, their `name:` lines are `mp-tdd` and
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

### Requirement: Renamed folder and name

`deploy` SHALL vendor each **Hull** **Skill** to `.apm/skills/<deployed name>/`. The `SKILL.md` of a **Skill** whose
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

### Requirement: References carry the deployed name

In every UTF-8 Markdown file of every **Hull** **Skill**, `deploy` SHALL rewrite each **Reference** that resolves,
**Binds** applied, to a **Hull** **Skill** whose **Deployed name** differs from the name written, keeping its form
(`/x`, `Skill(x)` with its quotes and arguments, `` `x` ``, bare `x`); a self-**Reference** included. All other bytes,
and files that are not UTF-8, SHALL be unchanged.

#### Scenario: Slash reference to a renamed skill

- **WHEN** `mp/tdd` calls `/grilling`, and `mp/grilling` is renamed to `mp-grilling`
- **THEN** the vendored `tdd/SKILL.md` holds `/mp-grilling` where it held `/grilling`

#### Scenario: Sentence end kept

- **WHEN** `mp/tdd` holds `Run /grilling.`, and `mp/grilling` is renamed to `mp-grilling`
- **THEN** the vendored copy holds `Run /mp-grilling.`

#### Scenario: Skill tool and prose forms

- **WHEN** `mp/tdd` holds `Skill(skill: "grilling", args: "x")` and `` `grilling` ``, and `mp/grilling` is renamed to
  `mp-grilling`
- **THEN** the vendored copy holds `Skill(skill: "mp-grilling", args: "x")` and `` `mp-grilling` ``

#### Scenario: Bound to another name

- **WHEN** `mp/tdd` calls `/grilling`, `[bind]` has `"mp/grilling" = "own/grill"`, and no rename names `own/grill`
- **THEN** the vendored `tdd/SKILL.md` holds `/grill`

#### Scenario: Self-reference

- **WHEN** `mp/tdd`'s `SKILL.md` holds `/tdd`, and `mp/tdd` is renamed to `mp-tdd`
- **THEN** the vendored `mp-tdd/SKILL.md` holds `/mp-tdd`

#### Scenario: Sibling file

- **WHEN** `mp/tdd`'s `refs/loop.md` holds `/grilling`, and `mp/grilling` is renamed to `mp-grilling`
- **THEN** the vendored `refs/loop.md` holds `/mp-grilling`

#### Scenario: Unresolved names untouched

- **WHEN** `mp/tdd` holds `/foo`, matching no **Skill**, and `pre-commit`, bound by `"mp/pre-commit" = false`
- **THEN** both are vendored unchanged

### Requirement: Deployed names are unique

Two **Hull** **Skills** with the same **Deployed name**, compared ignoring case, SHALL be an error naming both and a
change that would separate them, and the command SHALL then write nothing. Every command that computes the **Hull**
SHALL report a clash between **Entries** before any **Source** is read or a remote contacted, except `rename` and
`bind`, which first read the **Source** of the **Skill ID** they are given, and no other, to check it. The hint SHALL
name a `[rename]` line for a clashing **Skill** with neither a `[rename]` key nor a **Prefix**; else the `[rename]`
value of a renamed one to change; else, for a prefixed one, that a `[rename]` key for it would, or its **Source**'s
`prefix` unless another clashing **Skill** is of that **Source**.

#### Scenario: Clash across sources

- **WHEN** `mp/tdd` and `own/tdd` are both **Entries**, neither renamed
- **THEN** `deploy` exits non-zero naming both and `[rename]`, and leaves `.apm/skills/` and the lock unchanged

#### Scenario: Entries clash before any fetch

- **WHEN** **Entries** `mp/tdd` and `own/tdd` have no `[rename]` key, and `mp` is a git **Source** whose `ref` is not
  cached
- **THEN** `deploy` exits non-zero naming both, and fetches nothing

#### Scenario: Entries clash before update fetches

- **WHEN** **Entries** `mp/tdd` and `own/tdd` have no `[rename]` key, `mp` is a git **Source**, and the user runs
  `update mp`
- **THEN** `update` exits non-zero naming both, contacts no remote, and writes nothing

#### Scenario: Entries clash after rename reads only its source

- **WHEN** **Entries** `mp/tdd` and `own/tdd` have no `[rename]` key, `other` is a git **Source** whose `ref` is not
  cached, and the user runs `skill-graft rename mp/notes n`
- **THEN** it exits non-zero naming `mp/tdd` and `own/tdd`, fetches nothing for `other`, and `skill-graft.toml` is
  unchanged

#### Scenario: Clash through a reference

- **WHEN** **Entry** `own/grilling` exists, and **Entry** `mp/tdd` calls `/grilling`, resolved to `mp/grilling`
- **THEN** `deploy` exits non-zero naming `mp/grilling` and `own/grilling`

#### Scenario: Rename settles a clash

- **WHEN** `mp/tdd` and `own/tdd` are both **Entries**, and `[rename]` has `"own/tdd" = "own-tdd"`
- **THEN** `deploy` vendors `tdd/` and `own-tdd/`, and exits 0

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
- **THEN** `resolve` and `deploy` exit non-zero naming `mp/review`, `review` and `"mp/review" = "mp-review"`

#### Scenario: Renamed out of the way

- **WHEN** `reserved = ["review"]` and `[rename]` has `"mp/review" = "mp-review"`
- **THEN** the command succeeds

#### Scenario: Prefixed onto a reserved name

- **WHEN** `reserved = ["mp-review"]`, `[sources.mp]` has `prefix = "mp-"`, and `mp/review` is in the **Hull** with no
  `[rename]` key
- **THEN** the command exits non-zero naming `mp/review` and `mp-review`, and says to add a `[rename]` key for it or
  change `[sources.mp] prefix = "mp-"`
