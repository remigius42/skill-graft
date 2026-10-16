# Spec Delta

## Purpose

Finds the **Skills** in a **Source** and gives each its **Skill ID**, so **Entries** can name them.

## ADDED Requirements

### Requirement: Skills at any depth

Every folder under a **Source** that holds a file named `SKILL.md` SHALL be a **Skill**, at any depth,
including inside hidden folders other than `.git`. A **Skill** is its whole folder, so discovery SHALL NOT look
for further **Skills** inside one.

#### Scenario: Nested layout

- **WHEN** a source holds `a/SKILL.md` and `x/y/z/b/SKILL.md`
- **THEN** both `a` and `b` are **Skills** of that source

#### Scenario: Skill inside a skill

- **WHEN** a source holds `a/SKILL.md` and `a/examples/c/SKILL.md`
- **THEN** `a` is a **Skill** and `c` is not

#### Scenario: Git metadata

- **WHEN** a source holds `.git/x/SKILL.md`
- **THEN** `x` is not a **Skill**

### Requirement: Skill name

A **Skill**'s name SHALL be the `name:` value of the YAML front matter opening its `SKILL.md`, with surrounding
quotes removed, else its folder name. Its **Skill ID** is `<source alias>/<name>`.

#### Scenario: Front matter name

- **WHEN** `skills/tdd-v2/SKILL.md` opens with front matter holding `name: tdd`
- **THEN** its **Skill ID** in source `mp` is `mp/tdd`

#### Scenario: No front matter name

- **WHEN** `grilling/SKILL.md` has no front matter, or front matter without `name:`
- **THEN** its name is `grilling`

### Requirement: Skill IDs are unique within a source

Two **Skills** with the same name in one **Source** SHALL be an error when an **Entry** names that **Skill ID**,
naming both folders.

#### Scenario: Duplicate name

- **WHEN** source `mp` holds `a/tdd/SKILL.md` and `b/tdd/SKILL.md` and `mp/tdd` is an **Entry**
- **THEN** the command exits non-zero naming `mp/tdd` and both folders

### Requirement: Unknown skill

An **Entry** that matches no **Skill** in its **Source** SHALL be an error.

#### Scenario: Entry not found

- **WHEN** `mp/nope` is an **Entry** and source `mp` has no skill `nope`
- **THEN** the command exits non-zero naming `mp/nope`
