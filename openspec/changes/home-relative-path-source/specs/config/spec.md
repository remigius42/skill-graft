## MODIFIED Requirements

### Requirement: Path sources

A path source's `path` SHALL name a folder, with `~` expanded and a relative path taken relative to the folder holding
`skill-graft.toml`. The alias names the **Source** and SHALL be one path segment: `[A-Za-z0-9][A-Za-z0-9._-]*`.

#### Scenario: Home-relative path

- **WHEN** `[sources.own]` has `path = "~/skills"`
- **THEN** **Source** `own` is the folder `skills` under the user's home

#### Scenario: Missing folder

- **WHEN** a source's `path` does not name an existing folder
- **THEN** the command exits non-zero naming the alias and the path

#### Scenario: Unknown user's home

- **WHEN** `[sources.own]` has `path = "~ghost/skills"`, and no user `ghost` exists
- **THEN** the command exits non-zero naming `own` and the path, with no traceback

#### Scenario: Unknown user's home in a patch

- **WHEN** `[patches]` has `"mp/tdd" = ["~ghost/tdd.patch"]`, and no user `ghost` exists
- **THEN** the command exits non-zero naming the path, with no traceback

#### Scenario: Bad alias

- **WHEN** the TOML has `[sources."a/b"]` or `[sources.".."]`
- **THEN** the command exits non-zero naming the alias

## ADDED Requirements

### Requirement: Machine-specific project path sources

In project scope, each command that writes the **Package**'s own lock, or would in its dry run, SHALL warn of each path
source the lock records as an absolute folder, naming the alias and the folder and saying that other machines need it at
the same place, and continue. `deploy --into`, commands that write no lock, and user scope SHALL give no such warning.

#### Scenario: Absolute path outside the project

- **WHEN** in project scope `[sources.own]` has `path = "/opt/skills"`, and the user runs `resolve`, `deploy`, `add` or
  `update`
- **THEN** the command prints a warning naming `own` and `/opt/skills`, and continues

#### Scenario: Dry run

- **WHEN** in project scope `[sources.own]` has `path = "/opt/skills"`, and the user runs `resolve --dry-run`
- **THEN** the command prints the warning naming `own`

#### Scenario: Relative path outside the project

- **WHEN** in project scope `[sources.own]` has `path = "../../../shared"`, a folder beside the project root, and the
  user runs `resolve`
- **THEN** the command prints a warning naming `own` and that folder, and continues

#### Scenario: Home path

- **WHEN** in project scope `[sources.own]` has `path = "~/skills"` or `path = "~/..skills"`, and the user runs
  `resolve`
- **THEN** the command prints no warning naming `own`

#### Scenario: Not portable home forms

- **WHEN** in project scope `[sources.own]` has `path` set to the home folder's absolute `skills` folder, to
  `~alice/skills` for an existing user `alice`, to `~/../shared`, or to `~/x/../skills`, and the user runs `resolve`
- **THEN** the command prints a warning naming `own`, and continues

#### Scenario: Path inside the project

- **WHEN** in project scope `[sources.own]` has `path = "../../skills"`, and the user runs `resolve`
- **THEN** the command prints no warning naming `own`

#### Scenario: Commands leaving the package's lock alone

- **WHEN** in project scope `[sources.own]` has `path = "/opt/skills"`, and the user runs `tree` or
  `deploy --into <dir>`
- **THEN** the command prints no warning naming `own`

#### Scenario: User scope

- **WHEN** in user scope `[sources.own]` has `path = "/opt/skills"`, and the user runs `resolve`
- **THEN** the command prints no warning naming `own`
