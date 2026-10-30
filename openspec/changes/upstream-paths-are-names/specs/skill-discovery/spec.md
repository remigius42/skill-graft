## ADDED Requirements

### Requirement: Skill folders use name characters

Each folder on a **Skill**'s path below the folder discovery walks, its own folder included and as reached through
symlinks, SHALL match `[A-Za-z0-9._-]+`, not only dots; a **Skill** at the walked folder itself has no such folder. A
**Skill** whose path does not match SHALL be unusable, and elsewhere in the **Source** SHALL NOT block the command.

#### Scenario: Skill at the root

- **WHEN** path source `own` is `~/own`, which holds `SKILL.md`, and `own/own` is an **Entry**
- **THEN** `build` vendors `own`, and the lock records `upstream = "."`

#### Scenario: Hidden folder

- **WHEN** a source holds `.claude/skills/tdd/SKILL.md` and `mp/tdd` is an **Entry**
- **THEN** `build` vendors `tdd`

#### Scenario: Elsewhere in the source

- **WHEN** path source `own` holds `my skills/x/SKILL.md` and `tdd/SKILL.md`, and `own/tdd` is the only **Entry**
- **THEN** `build` finishes and vendors `tdd`

### Requirement: An unusable skill path is an error where needed

A command that needs a **Skill** whose path is unusable, by an **Entry**, a `[bind]` target, or a slash or
`Skill(<name>)` **Reference** to its name, SHALL exit non-zero naming that path below the walked folder, each byte of
its file-system encoding outside `[A-Za-z0-9._/-]` written as `\` and three octal digits, and no other error about that
**Skill**. A Skill tool sentence naming it SHALL stay a word. The **Skill**'s regular-file and symlink checks SHALL run
first, so a `SKILL.md` they refuse is never opened.

#### Scenario: Space in a folder

- **WHEN** path source `own` holds `my skills/tdd/SKILL.md` and `own/tdd` is an **Entry**
- **THEN** the command exits non-zero, its error holding `my\040skills/tdd`

#### Scenario: Shell syntax in a folder

- **WHEN** git source `mp` holds `skills/$(touch x)/tdd/SKILL.md` and `mp/tdd` is an **Entry**
- **THEN** the command exits non-zero, its error holding `skills/\044\050touch\040x\051/tdd` and no `$(`, and nothing is
  vendored

#### Scenario: Line break in a folder

- **WHEN** the folder of a **Skill** whose `SKILL.md` holds `name: tdd` is `tdd\nupstream: /etc`, and `mp/tdd` is an
  **Entry**
- **THEN** the error prints the path on one line, with `\012` for the line break

#### Scenario: Non-ASCII folder

- **WHEN** path source `own` holds `ä/tdd/SKILL.md` and `own/tdd` is an **Entry**
- **THEN** the command exits non-zero, its error holding `\303\244/tdd`

#### Scenario: Bad path and a symlink out of the skill

- **WHEN** git source `mp` holds `skills/$(x)/tdd/SKILL.md` as a symlink leading outside its skill, and `mp/tdd` is an
  **Entry**
- **THEN** the command exits non-zero, its error holding `skills/\044\050x\051/tdd` and no `$(`

#### Scenario: Bind target

- **WHEN** `own/a` calls `/x`, `[bind]` has `"own/x" = "own/tdd"`, and `own`'s only `tdd` is at `my skills/tdd/`
- **THEN** the command exits non-zero naming the escaped path

#### Scenario: Called by a reference

- **WHEN** `own/a` calls `/tdd`, and `own`'s only `tdd` is at `my skills/tdd/`
- **THEN** the command exits non-zero naming the escaped path, rather than resolving `/tdd` in another **Source**

#### Scenario: Skill tool sentence

- **WHEN** `own/a` says to call the Skill tool with `"tdd"`, and `own`'s only `tdd` is at `my skills/tdd/`
- **THEN** `build` finishes, with no edge from `own/a` to a `tdd`

#### Scenario: Two skills of one name

- **WHEN** `own` holds `tdd/SKILL.md` and `my skills/tdd/SKILL.md`, and `own/tdd` is an **Entry**
- **THEN** the command exits non-zero naming both, as for an unreadable name

### Requirement: Invalid names are escaped

The error for a **Skill** whose name is no path segment SHALL write its name and its path below the walked folder with
each byte outside `[A-Za-z0-9._/-]` escaped as octal, as for an unusable path.

#### Scenario: Shell syntax in a name

- **WHEN** `own`'s `x/SKILL.md` holds `name: $(curl x)/a`, and `own/x` is an **Entry**
- **THEN** the command exits non-zero, its error holding `\044\050curl\040x\051/a` and no `$(`

#### Scenario: Bad path and a SKILL.md that is a device

- **WHEN** path source `own` holds `my skills/tdd/SKILL.md` as a symlink to `/dev/zero`, and `own/tdd` is the only
  **Entry**
- **THEN** the command exits non-zero, and `/dev/zero` is never opened
