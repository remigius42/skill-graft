# Spec Delta

## Purpose

Gives each **Hull** **Skill** its **Deployed name**, carries that name into the folder, `name:` and every
**Reference**, and keeps **Deployed names** unique and clear of **Reserved names**.

## ADDED Requirements

### Requirement: Deployed name

A **Skill**'s **Deployed name** SHALL be its `[rename]` value when one names its **Skill ID**, else its name.

#### Scenario: Renamed

- **WHEN** `[rename]` has `"mp/grilling" = "mp-grilling"` and `mp/grilling` is in the **Hull**
- **THEN** its **Deployed name** is `mp-grilling`

#### Scenario: Not renamed

- **WHEN** no `[rename]` key names `own/notes`
- **THEN** its **Deployed name** is `notes`

### Requirement: Renamed folder and name

`build` SHALL vendor each **Hull** **Skill** to `.apm/skills/<deployed name>/`. A renamed **Skill**'s `SKILL.md`
SHALL carry `name: <deployed name>`, quoted when YAML would read the bare name as anything but that string
(`true`, `null`, `123`): an existing `name:` line replaced, else inserted as the front matter's first
line, else a front matter of just that line prepended. An unrenamed **Skill**'s `name:` SHALL be unchanged.

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

### Requirement: References carry the deployed name

In every UTF-8 Markdown file of every **Hull** **Skill**, `build` SHALL rewrite each **Reference** that resolves,
**Binds** applied, to a **Hull** **Skill** whose **Deployed name** differs from the name written, keeping its
form (`/x`, `Skill(x)` with its quotes and arguments, `` `x` ``, bare `x`); a self-**Reference** included. All
other bytes, and files that are not UTF-8, SHALL be unchanged.

#### Scenario: Slash reference to a renamed skill

- **WHEN** `mp/tdd` calls `/grilling`, and `mp/grilling` is renamed to `mp-grilling`
- **THEN** the vendored `tdd/SKILL.md` holds `/mp-grilling` where it held `/grilling`

#### Scenario: Sentence end kept

- **WHEN** `mp/tdd` holds `Run /grilling.`, and `mp/grilling` is renamed to `mp-grilling`
- **THEN** the vendored copy holds `Run /mp-grilling.`

#### Scenario: Skill tool and prose forms

- **WHEN** `mp/tdd` holds `Skill(skill: "grilling", args: "x")` and `` `grilling` ``, and `mp/grilling` is
  renamed to `mp-grilling`
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

### Requirement: Unused renames warn

A `[rename]` key naming no **Hull** **Skill** SHALL be a warning naming the key, and the command SHALL proceed.

#### Scenario: Rename outside the hull

- **WHEN** `[rename]` has `"mp/review" = "mp-review"` and `mp/review` is not in the **Hull**
- **THEN** the command warns that `mp/review` renames no **Skill** in the **Hull**, and succeeds

### Requirement: Deployed names are unique

Two **Hull** **Skills** with the same **Deployed name**, compared ignoring case, SHALL be an error naming both
and a `[rename]` line that would separate them, and the command SHALL then write nothing. A hint SHALL never add
a second key for a **Skill** already renamed: it names an unrenamed one, else says which value to change.

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
- **THEN** the command exits non-zero naming `mp/grilling` and `own/notes`, and suggests
  `"own/notes" = "own-notes"`

#### Scenario: Clash of two renames

- **WHEN** `[rename]` has `"mp/a" = "x"` and `"own/b" = "x"`
- **THEN** the command exits non-zero saying to change `[rename] "own/b" = "x"`

### Requirement: The user's reserved names are errors

A **Deployed name** equal, ignoring case, to a name in the user's `reserved` list SHALL be an error naming the
**Skill**, the name, and a `[rename]` line that would avoid it, and the command SHALL then write nothing.

#### Scenario: Reserved by the user

- **WHEN** `reserved = ["review"]` and `mp/review` is in the **Hull**, not renamed
- **THEN** `resolve` and `build` exit non-zero naming `mp/review`, `review` and `"mp/review" = "mp-review"`

#### Scenario: Renamed out of the way

- **WHEN** `reserved = ["review"]` and `[rename]` has `"mp/review" = "mp-review"`
- **THEN** the command succeeds

### Requirement: Shipped reserved names warn

skill-graft SHALL ship a list of **Reserved names**: the built-in commands and bundled skills of Claude Code and
Codex, `code-review` among them. A **Deployed name** equal to one, ignoring case, SHALL be a warning naming the
**Skill** and the name; an unrenamed **Skill**'s warning SHALL end with `"<alias>/<name>" = "<alias>-<name>"`
under `[rename]`. The command SHALL proceed.

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
