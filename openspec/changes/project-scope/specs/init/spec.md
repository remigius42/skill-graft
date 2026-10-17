# Spec Delta

## MODIFIED Requirements

### Requirement: Init creates the package folder

`skill-graft init` SHALL create `~/.apm/skill-graft/`, and `skill-graft init --project` SHALL create
`<working folder>/.apm/skill-graft/`, each holding a `skill-graft.toml` whose content is only comments explaining
`entries` and `[sources.<alias>]`, both with `path` and with `git`, `branch` and `ref`, and an `apm.yml` of
exactly two lines: `name: skill-graft` and `version: 0.1.0`.

#### Scenario: Fresh home

- **WHEN** `~/.apm/skill-graft/` does not exist and the user runs `skill-graft init`
- **THEN** the folder exists with `skill-graft.toml` and the two-line `apm.yml`
- **AND** `skill-graft.toml` parses as TOML with no keys

#### Scenario: Template shows a git source

- **WHEN** the user runs `skill-graft init`
- **THEN** `skill-graft.toml` mentions `git`, `branch`, `ref` and `skill-graft update`

#### Scenario: Project package

- **WHEN** the user runs `skill-graft init --project` in `~/repo`, which has a `.claude/` folder
- **THEN** `~/repo/.apm/skill-graft/` exists with the same two files, and nothing under `~/.apm/` changes

### Requirement: Init registers the package with APM

After creating the folder, `init` SHALL run `apm install -g <absolute path of ~/.apm/skill-graft>` and succeed
only if APM exits 0 and `~/.apm/apm.yml` then lists the package. `init --project` SHALL instead run
`apm install ./.apm/skill-graft` in the working folder and succeed only if APM exits 0 and `apm.yml` there lists
the package. skill-graft SHALL NOT write either `apm.yml` itself.

#### Scenario: Registration succeeds

- **WHEN** `init` runs and APM exits 0
- **THEN** `~/.apm/apm.yml` lists the absolute path of `~/.apm/skill-graft` under `dependencies.apm`
- **AND** `init` exits 0

#### Scenario: Project registration succeeds

- **WHEN** `init --project` runs in `~/repo` and APM exits 0
- **THEN** `~/repo/apm.yml` lists `./.apm/skill-graft` under `dependencies.apm`, and `init` exits 0

#### Scenario: APM fails

- **WHEN** `apm` exits non-zero, is not on `PATH`, or leaves `~/.apm/apm.yml` without the package
- **THEN** `init` exits non-zero, keeps the created folder, and prints the `apm install -g` command to retry

#### Scenario: No harness in the project

- **WHEN** `init --project` runs in a folder with no harness marker, and APM exits 2
- **THEN** APM's message reaches the user, and `init` exits non-zero, keeps the created folder, and prints the
  folder and the `apm install ./.apm/skill-graft` command to retry there

### Requirement: Init refuses an existing folder

`init` SHALL NOT modify anything when the folder it would create already exists.

#### Scenario: Folder exists

- **WHEN** `~/.apm/skill-graft/` exists and the user runs `skill-graft init`
- **THEN** `init` exits non-zero naming the folder, leaves its contents unchanged, and does not run `apm`

#### Scenario: Project folder exists

- **WHEN** `~/repo/.apm/skill-graft/` exists and the user runs `skill-graft init --project` in `~/repo`
- **THEN** `init` exits non-zero naming the folder, leaves its contents unchanged, and does not run `apm`

## ADDED Requirements

### Requirement: No project package in the home folder

`init --project` in the home folder SHALL exit non-zero, create nothing, run no `apm`, and tell the user that
`skill-graft init` creates the user scope's **Package**.

#### Scenario: Project init at home

- **WHEN** the user runs `skill-graft init --project` in the home folder
- **THEN** it exits non-zero naming `skill-graft init`, and `~/.apm/skill-graft/` is not created

#### Scenario: Project init inside another project

- **WHEN** `~/a/.apm/skill-graft/` exists and the user runs `skill-graft init --project` in `~/a/b`
- **THEN** `~/a/b/.apm/skill-graft/` is created, and commands run in `~/a/b` act on it
