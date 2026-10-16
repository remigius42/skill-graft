# Spec Delta

## Purpose

Finds the slash and Skill tool **References** in each **Skill**, resolves them to **Skills**, and spans the
**Hull**: the **Entries** plus every **Skill** they reach.

## ADDED Requirements

### Requirement: Slash references

A slash **Reference** SHALL be `/` then a name (`[A-Za-z0-9][A-Za-z0-9._-]*`, trailing `.` dropped) standing as
its own token: not preceded by a letter, digit, `/`, `.`, `-`, `~`, `:`, `\` or `<`, and not followed by `/`, a
letter, a digit, or `:` and a letter or digit. It SHALL count anywhere in the file, code blocks included.

#### Scenario: Standalone token

- **WHEN** a **Skill**'s Markdown holds `run /grilling.`, `` `/grilling` ``, `(/grilling)` or `**/grilling**`
- **THEN** each is a slash **Reference** to `grilling`

#### Scenario: Paths and URLs

- **WHEN** it holds `/usr/bin`, `src/grilling`, `https://x.org/grilling`, `~/grilling`, `</grilling>` or
  `/plugin:grilling`
- **THEN** none is a **Reference**

### Requirement: Skill tool references

A Skill tool **Reference** SHALL be the call form `Skill(<name>)`: the name optionally quoted with `"` or `'`,
optionally given as `skill=<name>` or `skill: <name>`, with optional whitespace inside the parentheses.

#### Scenario: Call forms

- **WHEN** a **Skill**'s Markdown holds `Skill(grilling)`, `Skill("grilling")` or `Skill(skill: "grilling")`
- **THEN** each is a Skill tool **Reference** to `grilling`

### Requirement: Every Markdown file

**References** SHALL be read from every file ending in `.md` (any case) in the **Skill**'s folder, at any depth,
`.git` excepted. A Markdown file that is not UTF-8 SHALL be an error naming it. A **Skill**'s **Reference** to
its own name SHALL be ignored.

#### Scenario: Reference in a sibling file

- **WHEN** `mp/tdd`'s `refs/loop.md` holds `/grilling`, and its `SKILL.md` does not
- **THEN** `mp/grilling` is in the **Hull**

#### Scenario: Not UTF-8

- **WHEN** a **Hull** **Skill**'s `notes.md` holds invalid UTF-8
- **THEN** the command exits non-zero naming `notes.md`

### Requirement: Resolve in the own source first

A slash or Skill tool **Reference** from a **Skill** in **Source** `a` SHALL resolve to `a/<name>` when `a` has
a **Skill** of that name, whatever other **Sources** hold.

#### Scenario: Own source wins

- **WHEN** `mp/tdd` calls `/grilling`, and both `mp` and `own` have a **Skill** `grilling`
- **THEN** `mp/grilling` is in the **Hull** and `own/grilling` is not

### Requirement: Else exactly one other source

When the own **Source** lacks the name, the **Reference** SHALL resolve in the one other declared **Source**
having it. Several SHALL be an error naming the referencing **Skill**, the **Reference**, the matching **Skill
IDs**, and the `[bind]` key that would settle it.

#### Scenario: One other source

- **WHEN** `mp/tdd` calls `/notes`, `mp` has no `notes`, and only `own` has one
- **THEN** `own/notes` is in the **Hull**

#### Scenario: Several other sources

- **WHEN** `mp/tdd` calls `/notes`, `mp` has no `notes`, and both `own` and `x` have one
- **THEN** the command exits non-zero naming `mp/tdd`, `/notes`, `own/notes`, `x/notes` and `"mp/notes"` under
  `[bind]`, and writes nothing

### Requirement: Unmatched references warn

A slash or Skill tool **Reference** matching no **Skill** in any declared **Source**, and no **Bind**, SHALL be a
warning `` `<skill id>` calls `/<name>`: no declared source has a skill `<name>` ``, ending with the `[bind]`
line that would ignore it, once per referencing **Skill** and name, and the command SHALL proceed.

#### Scenario: No such skill

- **WHEN** `mp/tdd` calls `/foo` twice, and no **Source** has a **Skill** `foo`
- **THEN** the command prints `` `mp/tdd` calls `/foo`: no declared source has a skill `foo` `` and
  `"mp/foo" = false` once, and succeeds

### Requirement: Binds to nothing

A **Bind** `"<a>/<name>" = false` SHALL make `<name>` from any **Skill** in **Source** `a` no **Reference**: it
adds no **Skill** or edge and gives no warning, whether a **Skill** of that name exists or not.

#### Scenario: Path in a code block

- **WHEN** `mp/tdd` holds `cd /tmp` in a fenced block, and `[bind]` has `"mp/tmp" = false`
- **THEN** the command prints no warning about `tmp`

#### Scenario: Unwanted match

- **WHEN** `mp/tdd` calls `/tmp`, `own` has a **Skill** `tmp`, and `[bind]` has `"mp/tmp" = false`
- **THEN** `own/tmp` is not in the **Hull**

### Requirement: Binds override resolution

A **Bind** `"<a>/<name>" = "<b>/<target>"` SHALL make every slash and Skill tool **Reference** to `<name>` from
a **Skill** in **Source** `a` resolve to `b/<target>`, whatever the default would give, error or no match
included. Its target SHALL be found as an **Entry** is; a missing or ambiguous one is an error naming the
**Bind**.

#### Scenario: Bind across sources

- **WHEN** `mp/tdd` calls `/grilling`, `mp` has `grilling`, and `[bind]` has `"mp/grilling" = "own/grill"`
- **THEN** `own/grill` is in the **Hull** and `mp/grilling` is not

#### Scenario: Bind settles ambiguity

- **WHEN** `/notes` from `mp` would match `own/notes` and `x/notes`, and `[bind]` has `"mp/notes" = "x/notes"`
- **THEN** `x/notes` is in the **Hull**, and the command succeeds

#### Scenario: Bind to a missing skill

- **WHEN** `[bind]` has `"mp/grilling" = "own/nope"`, a **Hull** **Skill** in `mp` calls `/grilling`, and `own`
  has no `nope`
- **THEN** the command exits non-zero naming `mp/grilling` and `own/nope`

### Requirement: Unused binds warn

A **Bind** that no **Reference** from a **Hull** **Skill** uses SHALL be a warning naming its key.

#### Scenario: Typo in a bind

- **WHEN** `[bind]` has `"mp/grill" = "own/grilling"` and no **Hull** **Skill** in `mp` calls `/grill`
- **THEN** the command warns that `mp/grill` binds no **Reference**, and succeeds

### Requirement: The hull is transitive

The **Hull** SHALL be the **Entries** plus every **Skill** reachable from them through resolved slash and Skill
tool **References**, followed from each **Skill** reached, cycles included. A **Skill** reached SHALL be found as
an **Entry** is (unique within its **Source**, readable name, symlinks inside it), errors naming the referencing
**Skill**.

#### Scenario: Two hops

- **WHEN** `mp/tdd` calls `/grilling`, and `mp/grilling` calls `Skill(notes)`, found only in `own`
- **THEN** the **Hull** is `mp/tdd`, `mp/grilling` and `own/notes`

#### Scenario: Cycle

- **WHEN** `mp/a` calls `/b`, `mp/b` calls `/a`, and `mp/a` is the only **Entry**
- **THEN** the **Hull** is `mp/a` and `mp/b`, and the command terminates

#### Scenario: Ambiguous target

- **WHEN** `mp/tdd` calls `/grilling` and `mp` holds two **Skills** named `grilling`
- **THEN** the command exits non-zero naming `mp/tdd`, `/grilling` and both folders

### Requirement: Every declared source is read

Resolution SHALL read every declared **Source**, whether an **Entry** uses it or not: git **Sources** at their
`ref`, fetched only when that commit is missing from the cache.

#### Scenario: Source with no entry

- **WHEN** no **Entry** is in `own`, and `mp/tdd` calls `/notes`, found only in `own`
- **THEN** `own/notes` is in the **Hull**
