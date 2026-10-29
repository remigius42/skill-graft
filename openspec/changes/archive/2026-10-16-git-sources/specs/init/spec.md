# Spec Delta

## MODIFIED Requirements

### Requirement: Init creates the package folder

`skill-graft init` SHALL create `~/.apm/skill-graft/` holding a `skill-graft.toml` whose content is only comments
explaining `entries` and `[sources.<alias>]`, both with `path` and with `git`, `branch` and `ref`, and an `apm.yml` of
exactly two lines: `name: skill-graft` and `version: 0.1.0`.

#### Scenario: Fresh home

- **WHEN** `~/.apm/skill-graft/` does not exist and the user runs `skill-graft init`
- **THEN** the folder exists with `skill-graft.toml` and the two-line `apm.yml`
- **AND** `skill-graft.toml` parses as TOML with no keys

#### Scenario: Template shows a git source

- **WHEN** the user runs `skill-graft init`
- **THEN** `skill-graft.toml` mentions `git`, `branch`, `ref` and `skill-graft update`
