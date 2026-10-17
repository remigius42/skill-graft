# Spec Delta

## Purpose

`skill-graft add`, `remove` and `rename` change the **Entries** and **Renames** in `skill-graft.toml` for the
user, checking that the result resolves before anything is written.

## ADDED Requirements

### Requirement: Resolve before writing

`add`, `remove` and `rename` SHALL compute the **Hull** of the edited config, as `resolve` does, before writing
anything. Only if that succeeds SHALL they write `skill-graft.toml`, then `skill-graft.lock`, and print what
`resolve` prints. A failure SHALL leave both files unchanged. They SHALL NOT write `.apm/skills/` or run `apm`.

#### Scenario: Edit succeeds

- **WHEN** the user runs `skill-graft add mp/notes` and the edited config resolves
- **THEN** `entries` holds `mp/notes`, the lock is rewritten, the tree is printed, and `.apm/skills/` is unchanged

#### Scenario: Edit fails to resolve

- **WHEN** the user runs `skill-graft add mp/notes` and `mp/notes` calls `/x`, which matches several other
  **Sources** and no **Bind**
- **THEN** it exits non-zero, and `skill-graft.toml` and `skill-graft.lock` keep their bytes

### Requirement: Edit the TOML in place

An edit SHALL change only the values it is about, keeping every other comment, blank line, key order and other
formatting, and SHALL replace the file atomically. A symlinked `skill-graft.toml` SHALL stay a symlink: its
target is what changes, and relative paths in it resolve as `load` resolves them. A command that changes no value
SHALL NOT rewrite the file. A removed value's own trailing comment goes with it.

#### Scenario: Comments survive

- **WHEN** `skill-graft.toml` has comments, one trailing an existing `[rename]` line, and the user runs
  `skill-graft rename mp/tdd mp-tdd2` over that line's value
- **THEN** the new file equals the old one with only that value replaced

#### Scenario: Symlinked config

- **WHEN** `skill-graft.toml` is a symlink and the user runs `skill-graft add mp/notes`
- **THEN** it is still that symlink, and the file it points to holds `mp/notes`

### Requirement: Notices

Notices SHALL go to standard error with the warnings and SHALL NOT change the exit code.

#### Scenario: Notice stream

- **WHEN** `skill-graft add mp/tdd` finds `mp/tdd` already an **Entry**
- **THEN** standard error names `mp/tdd` as already an **Entry**, and standard output holds no notice

### Requirement: Add entries

`add <skill-id>…` SHALL append each **Skill ID** to `entries` in the order given, keeping the array's style, and
SHALL create `entries` before the first table when it is absent. A **Skill ID** given twice SHALL be added once.

#### Scenario: Appended

- **WHEN** `entries = ["mp/tdd"]` and the user runs `skill-graft add own/chisel mp/notes`
- **THEN** `entries` is `["mp/tdd", "own/chisel", "mp/notes"]`

#### Scenario: Multi-line array

- **WHEN** `entries` is written one **Skill ID** per line with a trailing comma, and the user runs
  `skill-graft add mp/notes`
- **THEN** `mp/notes` is on a new line after the last one, with a trailing comma

#### Scenario: No entries key

- **WHEN** `skill-graft.toml` has `[sources.mp]` and no `entries`, and the user runs `skill-graft add mp/tdd`
- **THEN** `entries = ["mp/tdd"]` stands before `[sources.mp]`

### Requirement: Add checks the skill

`add` SHALL refuse a **Skill ID** that is malformed, has an undeclared alias, or names no **Skill** in its
**Source**, writing nothing. A **Skill ID** already an **Entry** SHALL be a notice and left alone. A **Skill**
already in the **Hull** before the edit SHALL be added, with a notice naming a **Skill** whose slash or Skill tool
**Reference** reached it then.

#### Scenario: Unknown skill

- **WHEN** **Source** `mp` has no **Skill** `nope` and the user runs `skill-graft add mp/notes mp/nope`
- **THEN** it exits non-zero naming `mp/nope`, and `skill-graft.toml` is unchanged

#### Scenario: Undeclared alias

- **WHEN** no **Source** `zz` is declared and the user runs `skill-graft add zz/tdd`
- **THEN** it exits non-zero naming the alias `zz`

#### Scenario: Already an entry

- **WHEN** `mp/tdd` is an **Entry** and the user runs `skill-graft add mp/tdd`
- **THEN** it exits 0 with a notice, and `skill-graft.toml` keeps its bytes and modification time

#### Scenario: Already reachable

- **WHEN** **Entry** `mp/tdd` calls `/grilling` and the user runs `skill-graft add mp/grilling`
- **THEN** `entries` holds `mp/grilling`, and a notice says it was already in the **Hull** via `mp/tdd`

#### Scenario: Reached only through itself

- **WHEN** `mp/x` calls `/y`, `mp/y` calls `/x`, no **Entry** reaches either, an **Entry** mentions `x` in prose,
  and the user runs `skill-graft add mp/x`
- **THEN** `entries` holds `mp/x` and no notice is printed

### Requirement: Remove entries

`remove <skill-id>…` SHALL delete each **Skill ID** from `entries`, keeping the array's style. A **Skill ID** that
is no **Entry** SHALL be an error, writing nothing. A removed **Skill** still in the **Hull** SHALL be a notice
naming a **Skill** whose slash or Skill tool **Reference** reaches it.

#### Scenario: Removed

- **WHEN** `entries = ["mp/tdd", "mp/notes"]`, no **Skill** reaches `mp/notes`, and the user runs
  `skill-graft remove mp/notes`
- **THEN** `entries` is `["mp/tdd"]` and the printed tree has no `mp/notes`

#### Scenario: Not an entry

- **WHEN** `mp/grilling` is no **Entry** and the user runs `skill-graft remove mp/grilling`
- **THEN** it exits non-zero naming `mp/grilling`, and `skill-graft.toml` is unchanged

#### Scenario: Still reachable

- **WHEN** **Entries** `mp/tdd` and `mp/grilling`, `mp/tdd` calling `/grilling`, and the user runs
  `skill-graft remove mp/grilling`
- **THEN** `entries` is `["mp/tdd"]`, and a notice says `mp/grilling` stays in the **Hull** via `mp/tdd`

### Requirement: Rename a skill

`rename <skill-id> <name>` SHALL set the **Skill**'s value in `[rename]`, replacing an existing value in place or
appending a key, and SHALL append a `[rename]` table at the end of the file when it is absent. `<name>` SHALL be
a valid **Skill** name. A `<name>` equal to the current **Deployed name** SHALL be a notice and change nothing.

#### Scenario: New rename

- **WHEN** there is no `[rename]` table and the user runs `skill-graft rename mp/code-review mp-code-review`
- **THEN** the file ends with a `[rename]` table holding `"mp/code-review" = "mp-code-review"`, and the tree shows
  `mp/code-review as mp-code-review`

#### Scenario: Already that name

- **WHEN** `mp/tdd` is renamed to `mp-tdd` and the user runs `skill-graft rename mp/tdd mp-tdd`
- **THEN** it exits 0 with a notice, and `skill-graft.toml` keeps its bytes

#### Scenario: Invalid name

- **WHEN** the user runs `skill-graft rename mp/tdd a/b`
- **THEN** it exits non-zero naming `a/b`, and `skill-graft.toml` is unchanged

### Requirement: Undo a rename

`rename <skill-id> <name>` with `<name>` equal to the **Skill**'s upstream name SHALL remove its `[rename]` key,
leaving the table in place even if empty.

#### Scenario: Undone

- **WHEN** **Entry** `mp/code-review` is renamed to `mp-code-review` and the user runs
  `skill-graft rename mp/code-review code-review`
- **THEN** `[rename]` no longer holds `mp/code-review`, and the shipped reserved-name warning for `code-review`
  is printed

### Requirement: Rename checks the skill

`rename` SHALL refuse a malformed **Skill ID**, an undeclared alias, or a **Skill** missing from its **Source**,
writing nothing. A **Skill** outside the **Hull** SHALL be renamed, with the unused-rename warning. A **Deployed
name** that clashes with another **Hull** **Skill** or the user's `reserved` SHALL be the usual error, writing
nothing; one in the shipped reserved list SHALL be written, with the usual warning.

#### Scenario: Unknown skill to rename

- **WHEN** **Source** `mp` has no **Skill** `nope` and the user runs `skill-graft rename mp/nope x`
- **THEN** it exits non-zero naming `mp/nope`, and `skill-graft.toml` is unchanged

#### Scenario: Outside the hull

- **WHEN** `mp/notes` exists but is not in the **Hull**, and the user runs `skill-graft rename mp/notes n`
- **THEN** `[rename]` holds `"mp/notes" = "n"`, and the unused-rename warning names `mp/notes`

#### Scenario: Clash

- **WHEN** `mp/tdd` and `own/x` are in the **Hull** and the user runs `skill-graft rename own/x tdd`
- **THEN** it exits non-zero naming both **Skills**, and `skill-graft.toml` is unchanged

#### Scenario: User's reserved name

- **WHEN** `reserved = ["review"]`, `mp/check` is in the **Hull**, and the user runs
  `skill-graft rename mp/check review`
- **THEN** it exits non-zero naming `review`, and `skill-graft.toml` is unchanged

#### Scenario: Shipped reserved name

- **WHEN** `mp/check` is in the **Hull** and the user runs `skill-graft rename mp/check code-review`
- **THEN** `[rename]` holds `"mp/check" = "code-review"`, and the shipped reserved-name warning names it
