# init Specification

## Purpose

Creates the skill-graft APM package under `~/.apm/skill-graft/` and registers it with APM, once per machine.

## Requirements

### Requirement: Init creates the package folder

`skill-graft init` SHALL create `~/.apm/skill-graft/` holding a `skill-graft.toml` whose content is only
comments explaining `entries` and `[sources.<alias>]`, both with `path` and with `git`, `branch` and `ref`, and
an `apm.yml` of exactly two lines: `name: skill-graft` and `version: 0.1.0`.

#### Scenario: Fresh home

- **WHEN** `~/.apm/skill-graft/` does not exist and the user runs `skill-graft init`
- **THEN** the folder exists with `skill-graft.toml` and the two-line `apm.yml`
- **AND** `skill-graft.toml` parses as TOML with no keys

#### Scenario: Template shows a git source

- **WHEN** the user runs `skill-graft init`
- **THEN** `skill-graft.toml` mentions `git`, `branch`, `ref` and `skill-graft update`

### Requirement: Init registers the package with APM

After creating the folder, `init` SHALL run `apm install -g <absolute path of ~/.apm/skill-graft>` and succeed
only if APM exits 0 and `~/.apm/apm.yml` then lists the package. skill-graft SHALL NOT write `~/.apm/apm.yml`
itself.

#### Scenario: Registration succeeds

- **WHEN** `init` runs and APM exits 0
- **THEN** `~/.apm/apm.yml` lists the absolute path of `~/.apm/skill-graft` under `dependencies.apm`
- **AND** `init` exits 0

#### Scenario: APM fails

- **WHEN** `apm` exits non-zero, is not on `PATH`, or leaves `~/.apm/apm.yml` without the package
- **THEN** `init` exits non-zero, keeps the created folder, and prints the `apm install -g` command to retry

### Requirement: Init refuses an existing folder

`init` SHALL NOT modify anything when `~/.apm/skill-graft/` already exists.

#### Scenario: Folder exists

- **WHEN** `~/.apm/skill-graft/` exists and the user runs `skill-graft init`
- **THEN** `init` exits non-zero naming the folder, leaves its contents unchanged, and does not run `apm`
