## ADDED Requirements

### Requirement: References carry the reference prefix

With a `reference-prefix`, each **Reference** that resolves, **Binds** applied, to a **Hull** **Skill** SHALL be
vendored as the reference prefix followed by the target's **Deployed name**, in every form, a self-**Reference**
included. Folders, `name:` lines, **Skill IDs**, **Binds** and **Patches** SHALL be as without it.

#### Scenario: Slash reference

- **WHEN** `reference-prefix = "foo:"`, and `mp/tdd` calls `/grilling`, resolved to `mp/grilling`, not renamed
- **THEN** the vendored `tdd/SKILL.md` holds `/foo:grilling` where it held `/grilling`, and `mp/grilling` is vendored to
  `.apm/skills/grilling/` with its `name:` line unchanged

#### Scenario: Every form

- **WHEN** `reference-prefix = "foo:"`, and `mp/tdd` holds `Skill(skill: "grilling", args: "x")`, `` `grilling` ``, and
  `Call the Skill tool with "grilling".`, each resolved to `mp/grilling`
- **THEN** the vendored copy holds `Skill(skill: "foo:grilling", args: "x")`, `` `foo:grilling` `` and
  `Call the Skill tool with "foo:grilling".`

#### Scenario: After a rename or a prefix

- **WHEN** `reference-prefix = "foo:"`, `[sources.mp]` has `prefix = "mp-"`, and `mp/tdd` calls `/grilling`
- **THEN** the vendored `mp-tdd/SKILL.md` holds `/foo:mp-grilling`, and its `name:` line is `mp-tdd`

#### Scenario: Self-reference with a reference prefix

- **WHEN** `reference-prefix = "foo:"`, and `mp/tdd`'s `SKILL.md` holds `/tdd`
- **THEN** the vendored `tdd/SKILL.md` holds `/foo:tdd`

#### Scenario: Prefix used as written

- **WHEN** `reference-prefix = "foo-"`, and `mp/tdd` calls `/grilling`
- **THEN** the vendored copy holds `/foo-grilling`

#### Scenario: Unresolved names keep their text

- **WHEN** `reference-prefix = "foo:"`, and `mp/tdd` holds `/nope`, matching no **Skill**, and `pre-commit`, bound by
  `"mp/pre-commit" = false`
- **THEN** both are vendored unchanged

### Requirement: Prefixed prose is counted

With a `reference-prefix`, every command that writes the **Package**'s `.apm/skills/` SHALL print one notice naming
`reference-prefix`, how many prose words it vendored with the prefix, repeats and self-**References** included, and
`skill-graft tree`, which shows the **Skills** they name, when that number is above 0. Without the key, with no prose
**Reference** resolved, in a dry run or with `deploy --into`, it SHALL print none.

#### Scenario: Prose prefixed

- **WHEN** `reference-prefix = "foo:"`, and `mp/tdd` holds `` `grilling` `` twice and the bare word `follow-up` once,
  with `mp/grilling` and `mp/follow-up` in the **Hull**, and the user runs `resolve`
- **THEN** it prints `reference-prefix: 3 prose words prefixed; skill-graft tree shows the skills they name`

#### Scenario: One prose word

- **WHEN** `reference-prefix = "foo:"`, and the **Hull**'s only prose **Reference** is `mp/tdd`'s `` `grilling` ``
- **THEN** `resolve` prints `reference-prefix: 1 prose word prefixed; skill-graft tree shows the skill it names`

#### Scenario: No prose

- **WHEN** `reference-prefix = "foo:"`, and the **Hull**'s only **References** are slash ones
- **THEN** `resolve` prints no notice naming `reference-prefix`

#### Scenario: Nothing written

- **WHEN** `reference-prefix = "foo:"`, `mp/tdd` holds `` `grilling` ``, and the user runs `resolve --dry-run` or
  `deploy --into <dir>`
- **THEN** neither prints a notice naming `reference-prefix`

## MODIFIED Requirements

### Requirement: References carry the deployed name

In every UTF-8 Markdown file of every **Hull** **Skill**, `deploy` SHALL rewrite each **Reference** that resolves,
**Binds** applied, to a **Hull** **Skill** whose **Deployed name**, after the reference prefix when one is set, differs
from the name written, keeping its form (`/x`, `Skill(x)` with its quotes and arguments, `` `x` ``, bare `x`); a
self-**Reference** included. All other bytes, and files that are not UTF-8, SHALL be unchanged.

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

#### Scenario: Patched reference

- **WHEN** `reference-prefix = "foo:"`, and a **Patch** makes `mp/tdd` call `/grilling`
- **THEN** the vendored copy holds `/foo:grilling`, as for any other **Reference**
