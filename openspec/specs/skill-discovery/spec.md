# skill-discovery Specification

## Purpose

Finds the **Skills** in a **Source** and gives each its **Skill ID**, so **Entries** can name them.

## Requirements

### Requirement: Skills at any depth

Every folder under a **Source** that holds a file named `SKILL.md` SHALL be a **Skill**, at any depth, including inside
hidden folders other than `.git` and through symlinked folders, each resolved folder visited once. A **Skill** is its
whole folder, so discovery SHALL NOT look for further **Skills** inside one. Discovery SHALL NOT enter a folder that
resolves into `~/.apm/skill-graft/`, nor any folder whose path, as reached or resolved, runs through `.apm/skill-graft`,
so a build never reads its own output or another **Package**'s.

#### Scenario: Nested layout

- **WHEN** a source holds `a/SKILL.md` and `x/y/z/b/SKILL.md`
- **THEN** both `a` and `b` are **Skills** of that source

#### Scenario: Skill inside a skill

- **WHEN** a source holds `a/SKILL.md` and `a/examples/c/SKILL.md`
- **THEN** `a` is a **Skill** and `c` is not

#### Scenario: Symlinked skill folder

- **WHEN** a source holds `tdd` as a symlink to a folder holding `SKILL.md`
- **THEN** `tdd` is a **Skill** of that source

#### Scenario: Symlink cycle

- **WHEN** a source holds `loop` as a symlink to the source folder itself
- **THEN** discovery terminates and finds each skill once

#### Scenario: Git metadata

- **WHEN** a source holds `.git/x/SKILL.md`
- **THEN** `x` is not a **Skill**

#### Scenario: Symlink into the package

- **WHEN** a source holds a symlink to `~/.apm`, and a previous build vendored skills there
- **THEN** discovery does not look inside `~/.apm/skill-graft/`, so the vendored copies are not **Skills**

#### Scenario: Another project's package

- **WHEN** a source holds `repo/.apm/skill-graft/.apm/skills/tdd/SKILL.md`, a project **Package** committed there
- **THEN** `tdd` is not a **Skill** of that source

#### Scenario: Symlink into another package's skills

- **WHEN** a source holds `team -> ~/team-repo/.apm/skill-graft/.apm/skills`, which holds `tdd/SKILL.md`
- **THEN** `tdd` is not a **Skill** of that source

#### Scenario: Symlink to another project's package

- **WHEN** a source holds `team -> ~/team-repo/.apm`, and `~/team-repo/.apm/skill-graft/.apm/skills/tdd/SKILL.md` exists
- **THEN** `tdd` is not a **Skill** of that source

### Requirement: Skill name

A **Skill**'s name SHALL be the `name:` value of the YAML front matter opening its `SKILL.md`, else its folder name. Its
**Skill ID** is `<source alias>/<name>`. A leading BOM, trailing whitespace on the `---` fences, surrounding quotes, and
a trailing comment (whitespace then `#`) SHALL NOT change the name.

#### Scenario: Front matter name

- **WHEN** `skills/tdd-v2/SKILL.md` opens with front matter holding `name: tdd`
- **THEN** its **Skill ID** in source `mp` is `mp/tdd`

#### Scenario: No front matter name

- **WHEN** `grilling/SKILL.md` has no front matter, or front matter without `name:`
- **THEN** its name is `grilling`

#### Scenario: Comment and quotes

- **WHEN** the front matter holds `name: "tdd" # renamed` and the file starts with a UTF-8 BOM
- **THEN** the name is `tdd`

#### Scenario: Unsupported YAML form

- **WHEN** the front matter holds `name: >-` followed by an indented value
- **THEN** a command that needs that skill exits non-zero naming the `SKILL.md`, rather than using the folder name

### Requirement: Skill names are one path segment

A name SHALL match `[A-Za-z0-9][A-Za-z0-9._-]*`. An **Entry** naming a **Skill** whose name does not SHALL be an error
naming the `SKILL.md`; such a **Skill** elsewhere in the source SHALL NOT block the command.

#### Scenario: Traversal in name

- **WHEN** the **Skill** an **Entry** names has `name: ../../x`
- **THEN** the command exits non-zero naming its `SKILL.md`, and nothing is written outside `.apm/skills/`

### Requirement: Skill IDs are unique within a source

Two **Skills** with the same name in one **Source** SHALL be an error when an **Entry** names that **Skill ID**, naming
both folders.

#### Scenario: Duplicate name

- **WHEN** source `mp` holds `a/tdd/SKILL.md` and `b/tdd/SKILL.md` and `mp/tdd` is an **Entry**
- **THEN** the command exits non-zero naming `mp/tdd` and both folders

### Requirement: Unknown skill

An **Entry** that matches no **Skill** in its **Source** SHALL be an error.

#### Scenario: Entry not found

- **WHEN** `mp/nope` is an **Entry** and source `mp` has no skill `nope`
- **THEN** the command exits non-zero naming `mp/nope`

### Requirement: SKILL.md is a regular file

A `SKILL.md` that is not a regular file once its symlinks are followed, such as a FIFO or a device, or a link to one,
SHALL NOT be read: its **Skill**'s name SHALL be unreadable, its error naming that `SKILL.md` by its full path. This
holds in every **Source**, path **Sources** included, and when the file is replaced by such a one while being read.

#### Scenario: SKILL.md linked to a device

- **WHEN** path source `own` holds `x/SKILL.md` as a symlink to `/dev/zero`, and `own/tdd`, another **Skill** of `own`,
  is the only **Entry**
- **THEN** `build` finishes and vendors `tdd`

#### Scenario: Entry names it

- **WHEN** path source `own` holds `x/SKILL.md` as a FIFO, and `own/x` is an **Entry**
- **THEN** the command exits non-zero naming `x/SKILL.md` as not a regular file, without blocking

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

#### Scenario: Bad path and a SKILL.md that is a device

- **WHEN** path source `own` holds `my skills/tdd/SKILL.md` as a symlink to `/dev/zero`, and `own/tdd` is the only
  **Entry**
- **THEN** the command exits non-zero, and `/dev/zero` is never opened

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

#### Scenario: Bad path and a name that is no path segment

- **WHEN** `own` holds `good/SKILL.md` with `name: tdd` and `my skills/tdd/SKILL.md` with `name: a b`, and `own/tdd` is
  an **Entry**
- **THEN** `build` vendors `own/tdd` from `good/`; with only the second, the command exits non-zero naming
  `my\040skills/tdd`, as for an invalid name

### Requirement: Invalid names are escaped

The error for a **Skill** whose name is no path segment SHALL write its name and its path below the walked folder with
each byte outside `[A-Za-z0-9._/-]` escaped as octal, as for an unusable path.

#### Scenario: Shell syntax in a name

- **WHEN** `own`'s `x/SKILL.md` holds `name: $(curl x)/a`, and `own/x` is an **Entry**
- **THEN** the command exits non-zero, its error holding `\044\050curl\040x\051/a` and no `$(`
