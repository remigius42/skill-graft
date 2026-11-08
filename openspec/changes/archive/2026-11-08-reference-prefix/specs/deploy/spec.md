## ADDED Requirements

### Requirement: A reference prefix keeps deploy from APM

With a `reference-prefix`, `deploy` without `--no-apm-install` or `--into` SHALL exit 1 before reading any **Source**,
writing nothing and running no `apm`, naming `reference-prefix` and `skill-graft deploy --no-apm-install`: its
**References** resolve only where the harness puts the reference prefix before the names, as inside a plugin, never
where APM deploys. In a **Package** APM deploys, it SHALL instead refuse as "No reference prefix in a package APM
deploys" says, `--no-apm-install` or not, so it never names a command that then fails. `deploy --no-apm-install` and
`deploy --into` SHALL otherwise run as without it.

#### Scenario: Plain deploy refused

- **WHEN** a project **Package** no `apm.yml` lists has `reference-prefix = "foo:"`, a lock matches the **Hull**, and
  the user runs `skill-graft deploy`
- **THEN** it exits 1 naming `reference-prefix` and `skill-graft deploy --no-apm-install`, `apm` is not run, and
  `.apm/skills/` and the lock are unchanged

#### Scenario: Refused before any fetch

- **WHEN** a project **Package** no `apm.yml` lists has `reference-prefix = "foo:"`, `mp` is a git **Source** whose
  `ref` is not cached, and the user runs `skill-graft deploy`
- **THEN** it exits 1 as above, and fetches nothing

#### Scenario: Without APM

- **WHEN** a project **Package** no `apm.yml` lists has `reference-prefix = "foo:"`, and the user runs `resolve`, then
  `deploy --no-apm-install`
- **THEN** `deploy` vendors `.apm/skills/` with the prefixed **References**, runs no `apm`, and exits 0

#### Scenario: Into a folder

- **WHEN** a project **Package** no `apm.yml` lists has `reference-prefix = "foo:"`, and the user runs `resolve`, then
  `deploy --into <dir>`
- **THEN** `<dir>/.apm/skills/` holds the prefixed **References**, and `deploy` exits 0

### Requirement: No reference prefix in a package APM deploys

Every command that writes the **Package**'s `.apm/skills/` (`resolve`, `deploy`, `update` and the editing commands)
SHALL, with a `reference-prefix`, exit 1 before reading any **Source**, writing nothing, in user scope naming
`reference-prefix` and the **Package**, and in project scope when the project's `apm.yml` lists the **Package**, naming
`reference-prefix` and that `apm.yml`. Dry runs, `tree`, `why` and `vet` SHALL run as without it. `deploy --into` SHALL
refuse a **Hull** other than the lock's as without it, naming `skill-graft resolve`, which refuses the key there: it,
and graft-check, which runs it, serve a **Package** no `apm.yml` lists.

#### Scenario: User scope

- **WHEN** `~/.apm/skill-graft/skill-graft.toml` has `reference-prefix = "foo:"` and the user runs
  `skill-graft resolve`, `skill-graft deploy` or `skill-graft deploy --no-apm-install`
- **THEN** each exits 1 naming `reference-prefix` and `~/.apm/skill-graft`, not `skill-graft deploy --no-apm-install`,
  and writes nothing

#### Scenario: Registered project package

- **WHEN** a project's `apm.yml` lists `./.apm/skill-graft`, whose config has `reference-prefix = "foo:"`, and the user
  runs `skill-graft resolve`, `skill-graft deploy`, `skill-graft deploy --no-apm-install` or
  `skill-graft bind mp/x own/y` there
- **THEN** each exits 1 naming `reference-prefix` and the project's `apm.yml`, and writes nothing

#### Scenario: Unregistered project package

- **WHEN** a plugin folder holds `.apm/skill-graft/skill-graft.toml` with `reference-prefix = "foo:"`, made by hand, and
  no `apm.yml`
- **THEN** `skill-graft resolve` there vendors into `.apm/skill-graft/.apm/skills/` and exits 0

#### Scenario: Inspecting stays possible

- **WHEN** `~/.apm/skill-graft/skill-graft.toml` has `reference-prefix = "foo:"`, and the user runs `skill-graft tree`,
  `skill-graft why mp/tdd`, `skill-graft vet` or `skill-graft resolve --dry-run`
- **THEN** each runs as without the key, and writes nothing to `.apm/skills/`

### Requirement: A changed reference prefix is refused

`deploy` SHALL refuse a `reference-prefix` other than the lock's, a key set or removed since included, as it refuses any
other difference from the lock, for path **Sources** too, naming `reference-prefix` and `skill-graft resolve`.

#### Scenario: Reference prefix removed

- **WHEN** `own` is a path **Source**, the user runs `resolve` with `reference-prefix = "foo:"`, `own/tdd` calling
  `/grilling`, removes the key, and runs `deploy --no-apm-install`
- **THEN** `deploy` exits 1 naming `reference-prefix` and `skill-graft resolve`, and the vendored copy still holds
  `/foo:grilling`; after `resolve`, `deploy --no-apm-install` vendors `/grilling` and exits 0

#### Scenario: Reference prefix set

- **WHEN** the user runs `resolve` without `reference-prefix`, adds `reference-prefix = "foo:"`, and runs
  `deploy --no-apm-install`
- **THEN** `deploy` exits 1 naming `reference-prefix` and `skill-graft resolve`
