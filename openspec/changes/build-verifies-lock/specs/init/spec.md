## MODIFIED Requirements

### Requirement: Init registers the package with APM

Before creating the folder, `init` and `init --project` SHALL check that `apm` is on `PATH`; without it they SHALL exit
non-zero, create nothing, run no `apm`, and say to install APM and run the same `init` again. After creating the folder,
`init` SHALL run `apm install -g <absolute path of ~/.apm/skill-graft>` and succeed only if APM exits 0 and
`~/.apm/apm.yml` then lists the package. `init --project` SHALL instead run `apm install ./.apm/skill-graft` in the
working folder and succeed only if APM exits 0 and `apm.yml` there lists the package; if the package is then not listed
there, it SHALL remove what it created (`.apm/skill-graft/`, and `.apm/` if it made that too), so no unregistered
**Package** is left for commands to find. If APM fails but did list the package, the folder SHALL stay and `init` SHALL
say to fix the problem and run `skill-graft resolve`, then `skill-graft build`. skill-graft SHALL NOT write either
`apm.yml` itself.

#### Scenario: Registration succeeds

- **WHEN** `init` runs and APM exits 0
- **THEN** `~/.apm/apm.yml` lists the absolute path of `~/.apm/skill-graft` under `dependencies.apm`
- **AND** `init` exits 0

#### Scenario: Project registration succeeds

- **WHEN** `init --project` runs in `~/repo` and APM exits 0
- **THEN** `~/repo/apm.yml` lists `./.apm/skill-graft` under `dependencies.apm`, and `init` exits 0

#### Scenario: APM not installed

- **WHEN** `apm` is not on `PATH` and the user runs `skill-graft init`
- **THEN** `init` exits non-zero saying APM is not installed and to run `skill-graft init` once it is
- **AND** `~/.apm/` is not created

#### Scenario: APM not installed for a project

- **WHEN** `apm` is not on `PATH` and the user runs `skill-graft init --project` in `~/repo`
- **THEN** `init` exits non-zero saying APM is not installed and to run `skill-graft init --project` once it is
- **AND** `~/repo/.apm/` is not created

#### Scenario: Retry after installing APM

- **WHEN** `skill-graft init` failed because `apm` was not on `PATH`, APM is then installed, and the user runs
  `skill-graft init` again
- **THEN** `init` creates and registers the package and exits 0

#### Scenario: APM fails

- **WHEN** plain `init` runs, and `apm` exits non-zero, leaves `~/.apm/apm.yml` without the package, or is found on
  `PATH` by the check but is gone when `init` runs it
- **THEN** `init` exits non-zero, keeps the created folder, and prints the `apm install -g` command to retry

#### Scenario: No harness in the project

- **WHEN** `init --project` runs in a folder with no harness marker, and APM exits 2
- **THEN** APM's message reaches the user, and `init` exits non-zero, removes `.apm/skill-graft/` and the `.apm/` it
  created, and says to fix the problem and run `skill-graft init --project` again

#### Scenario: APM fails after registering

- **WHEN** `init --project` runs, and APM lists `./.apm/skill-graft` in `apm.yml` but exits non-zero
- **THEN** `init` exits non-zero, keeps the folder, and says to fix the problem and run `skill-graft resolve`, then
  `skill-graft build`
