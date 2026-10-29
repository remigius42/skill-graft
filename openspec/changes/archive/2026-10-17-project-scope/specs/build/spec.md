# Spec Delta

## MODIFIED Requirements

### Requirement: Deploy through APM

After vendoring, `build` SHALL run `apm install -g <absolute path of ~/.apm/skill-graft>`, which also registers the
package, and succeed only if APM exits 0 and `~/.apm/apm.yml` lists the package: as `- x` or `- path: x`, with `~` or an
absolute path, compared resolved. In project scope it SHALL instead run `apm install ./.apm/skill-graft` in the project
root and check the project root's `apm.yml`, where a relative path is relative to the project root. APM's output SHALL
reach the user.

#### Scenario: APM succeeds

- **WHEN** APM exits 0 and `~/.apm/apm.yml` lists the package
- **THEN** `build` exits 0

#### Scenario: Registration removed by hand

- **WHEN** the user deleted the package's line from `~/.apm/apm.yml` and runs `build`
- **THEN** APM re-adds it and `build` exits 0

#### Scenario: Symlinked home

- **WHEN** `HOME` is a symlink and `~/.apm/apm.yml` lists the package by its resolved path
- **THEN** `build` treats the package as registered

#### Scenario: APM exits non-zero

- **WHEN** `apm install -g` exits non-zero
- **THEN** `build` exits non-zero reporting APM's exit code

#### Scenario: Package not registered

- **WHEN** APM exits 0 but `~/.apm/apm.yml` is missing or does not list the package
- **THEN** `build` exits non-zero naming `~/.apm/apm.yml` and the expected path

#### Scenario: APM missing

- **WHEN** `apm` is not on `PATH`
- **THEN** `build` exits non-zero saying APM is not installed, after vendoring

#### Scenario: Project build from a subfolder

- **WHEN** the user runs `skill-graft build` in `~/repo/src`, `~/repo/.apm/skill-graft/` exists, and APM exits 0 leaving
  `- ./.apm/skill-graft` in `~/repo/apm.yml`
- **THEN** APM ran in `~/repo` with `install ./.apm/skill-graft` and no `-g`, and `build` exits 0

#### Scenario: Project package not registered

- **WHEN** in project scope APM exits 0 but `<project>/apm.yml` does not list the package
- **THEN** `build` exits non-zero naming `<project>/apm.yml` and the expected path

### Requirement: Build without installing

`build --no-install` SHALL vendor as above and SHALL NOT run `apm` or read the scope's `apm.yml`.

#### Scenario: No install

- **WHEN** the user runs `skill-graft build --no-install`
- **THEN** `.apm/skills/` is written, `apm` is not run, and `build` exits 0
