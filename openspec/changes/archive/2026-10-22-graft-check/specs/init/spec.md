## MODIFIED Requirements

### Requirement: Init creates the package folder

`skill-graft init` SHALL create `~/.apm/skill-graft/`, and `skill-graft init --project` SHALL create
`<working folder>/.apm/skill-graft/`, each holding a `skill-graft.toml` whose content is only comments explaining
`entries` and `[sources.<alias>]`, both with `path` and with `git`, `branch` and `ref`, and showing how to install
the `graft-check` skill, and an `apm.yml` of exactly two lines: `name: skill-graft` and `version: 0.1.0`.

#### Scenario: Fresh home

- **WHEN** `~/.apm/skill-graft/` does not exist and the user runs `skill-graft init`
- **THEN** the folder exists with `skill-graft.toml` and the two-line `apm.yml`
- **AND** `skill-graft.toml` parses as TOML with no keys

#### Scenario: Template shows a git source

- **WHEN** the user runs `skill-graft init`
- **THEN** `skill-graft.toml` mentions `git`, `branch`, `ref` and `skill-graft update`

#### Scenario: Template shows graft-check

- **WHEN** the user runs `skill-graft init`
- **THEN** `skill-graft.toml` holds, commented out, a **Source** `skill-graft` of
  `https://github.com/remigius42/skill-graft.git` with `subdirectory = "skills"`, followed by
  `skill-graft update skill-graft`, `skill-graft add skill-graft/graft-check` and `skill-graft build`, with a note that
  every `build` fails until that `update` has set the `ref`, and uncommenting the **Source** alone gives a config that
  loads

#### Scenario: Project package

- **WHEN** the user runs `skill-graft init --project` in `~/repo`, which has a `.claude/` folder
- **THEN** `~/repo/.apm/skill-graft/` exists with the same two files, and `~/.apm/skill-graft/` is not created
