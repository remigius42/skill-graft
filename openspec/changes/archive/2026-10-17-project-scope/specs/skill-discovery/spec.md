# Spec Delta

## MODIFIED Requirements

### Requirement: Skills at any depth

Every folder under a **Source** that holds a file named `SKILL.md` SHALL be a **Skill**, at any depth,
including inside hidden folders other than `.git` and through symlinked folders, each resolved folder visited
once. A **Skill** is its whole folder, so discovery SHALL NOT look for further **Skills** inside one. Discovery
SHALL NOT enter a folder that resolves into `~/.apm/skill-graft/`, nor any folder whose path, as reached or
resolved, runs through `.apm/skill-graft`, so a build never reads its own output or another **Package**'s.

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

- **WHEN** a source holds `team -> ~/team-repo/.apm`, and `~/team-repo/.apm/skill-graft/.apm/skills/tdd/SKILL.md`
  exists
- **THEN** `tdd` is not a **Skill** of that source
