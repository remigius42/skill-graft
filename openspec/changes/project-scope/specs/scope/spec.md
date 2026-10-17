# Spec Delta

## Purpose

Decides which **Package**, and so which **Scope**, a command acts on, and makes the commands that write name it.

## ADDED Requirements

### Requirement: Nearest package

Every command except `init` SHALL act on `<d>/.apm/skill-graft/` for the first folder `d` holding one, checking
the working folder, then each ancestor, and stopping after the home folder or the filesystem root. If `d` is the
home folder, or no folder holds one, the **Scope** SHALL be user scope with `~/.apm/skill-graft/`; otherwise
project scope with project root `d`. Paths are compared resolved.

#### Scenario: Inside a project

- **WHEN** `~/repo/.apm/skill-graft/` exists and the user runs `skill-graft build` in `~/repo/src`
- **THEN** `build` reads `~/repo/.apm/skill-graft/skill-graft.toml`, not the user scope's

#### Scenario: Project without a package

- **WHEN** `~/repo` holds no `.apm/skill-graft/` and the user runs a command in `~/repo`
- **THEN** it acts on `~/.apm/skill-graft/`

#### Scenario: Nested projects

- **WHEN** both `~/a/.apm/skill-graft/` and `~/a/b/.apm/skill-graft/` exist and the user runs a command in
  `~/a/b/c`
- **THEN** it acts on `~/a/b/.apm/skill-graft/`

#### Scenario: Package above the home folder

- **WHEN** the home folder is `/x/home`, `/x/.apm/skill-graft/` exists, and the user runs a command in
  `/x/home/repo`
- **THEN** it acts on `/x/home/.apm/skill-graft/`

#### Scenario: Working folder outside home

- **WHEN** `/srv/repo/.apm/skill-graft/` exists outside the home folder and the user runs a command in
  `/srv/repo`
- **THEN** it acts on `/srv/repo/.apm/skill-graft/` in project scope

### Requirement: Package paths follow the scope

Where another capability names a file or folder under `~/.apm/skill-graft/`, it SHALL mean the same path under
the **Package** in effect, unless it names the user scope's **Package**. Git **Sources** stay cached per user,
whatever the **Scope**.

#### Scenario: Project build

- **WHEN** the user runs `skill-graft build --no-install` in a project with a **Package**
- **THEN** the **Hull** is vendored into `<project>/.apm/skill-graft/.apm/skills/` and the lock written to
  `<project>/.apm/skill-graft/skill-graft.lock`, and `~/.apm/skill-graft/` is neither created nor changed

#### Scenario: Not initialized

- **WHEN** the user runs `skill-graft resolve` with no **Package** in effect
- **THEN** it exits non-zero naming `~/.apm/skill-graft/skill-graft.toml` and telling the user to run
  `skill-graft init`

### Requirement: Missing config in a project

In project scope, a missing `skill-graft.toml` SHALL be an error naming the file and saying to restore it, or to
delete the **Package** folder and run `skill-graft init --project` in the project root. It SHALL NOT suggest
plain `skill-graft init`.

#### Scenario: Project package without config

- **WHEN** `~/repo/.apm/skill-graft/` exists without `skill-graft.toml` and the user runs `build` in `~/repo`
- **THEN** it exits non-zero naming `~/repo/.apm/skill-graft/skill-graft.toml` and `skill-graft init --project`

### Requirement: Working folder is gone

When the working folder no longer exists, every command except `help` SHALL exit 1 with a `skill-graft:` error
saying so, not a traceback.

#### Scenario: Deleted working folder

- **WHEN** the user runs `skill-graft tree` in a folder another process deleted
- **THEN** it exits 1 with an error naming the missing working folder

### Requirement: Commands that write name the package

`init`, `resolve`, `build`, `update`, `add`, `remove` and `rename` SHALL print
`skill-graft: package: <absolute path of the Package>` on stderr before the command's own output, in either
**Scope**, including when the command fails after its arguments parsed. `tree`, `why` and `help` SHALL NOT print
it, and neither SHALL a usage error.

#### Scenario: Build names the package

- **WHEN** the user runs `skill-graft build` in a project with a **Package**
- **THEN** stderr starts with `skill-graft: package: <project>/.apm/skill-graft`

#### Scenario: Read-only command

- **WHEN** the user runs `skill-graft tree`
- **THEN** no `package:` line is printed
