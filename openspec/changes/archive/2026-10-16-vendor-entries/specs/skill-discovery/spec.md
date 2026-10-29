# Spec Delta

## Purpose

Finds the **Skills** in a **Source** and gives each its **Skill ID**, so **Entries** can name them.

## ADDED Requirements

### Requirement: Skills at any depth

Every folder under a **Source** that holds a file named `SKILL.md` SHALL be a **Skill**, at any depth, including inside
hidden folders other than `.git` and through symlinked folders, each resolved folder visited once. A **Skill** is its
whole folder, so discovery SHALL NOT look for further **Skills** inside one. Discovery SHALL NOT enter a folder that
resolves into `~/.apm/skill-graft/`, so a build never reads its own output.

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
