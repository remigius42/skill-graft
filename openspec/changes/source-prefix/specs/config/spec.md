## ADDED Requirements

### Requirement: Prefixes

A source's `prefix`, on a path or a git **Source**, SHALL be a name, one path segment
(`[A-Za-z0-9][A-Za-z0-9._-]*`); anything else, the empty string included, SHALL be an error naming
`sources.<alias>.prefix`.

#### Scenario: Valid prefix

- **WHEN** `[sources.mp]` has `git = "…"` and `prefix = "mp-"`, or `[sources.own]` has `path = "…"` and
  `prefix = "own."`
- **THEN** the config loads

#### Scenario: Prefix not a name

- **WHEN** `[sources.mp]` has `prefix = ""`, `prefix = "-x"`, `prefix = "a/"` or `prefix = 1`
- **THEN** the command exits non-zero naming `sources.mp.prefix`

## MODIFIED Requirements

### Requirement: Value types

`sources` SHALL be a table of tables, each source's `path`, `git`, `branch`, `ref` and `prefix` a string, and
`entries` a list of strings. A wrong type or a source table with neither `path` nor `git` SHALL be an error naming
the key, never a crash.

#### Scenario: Entries as a string

- **WHEN** `entries = "own/chisel"`
- **THEN** the command exits non-zero naming `entries` and the expected list

#### Scenario: Empty source

- **WHEN** the TOML has `[sources.own]` with no keys
- **THEN** the command exits non-zero naming `sources.own` and the expected `path` or `git`

#### Scenario: Path not a string

- **WHEN** `[sources.own]` has `path = 1`
- **THEN** the command exits non-zero naming `sources.own.path`

#### Scenario: Ref not a string

- **WHEN** `[sources.mp]` has `git = "…"` and `ref = 1`
- **THEN** the command exits non-zero naming `sources.mp.ref`

### Requirement: Unsupported keys are errors

Any top-level key other than `sources`, `entries`, `bind`, `rename`, `reserved` and `patches`, and any source key
other than `path`, `git`, `branch`, `ref` and `prefix`, SHALL be an error, so declared intent is never silently
ignored.

#### Scenario: Git source

- **WHEN** `[sources.mp]` has `git = "…"` and `tag = "v1"`
- **THEN** the command exits non-zero naming `sources.mp.tag` as unsupported

#### Scenario: Rename table

- **WHEN** the TOML has a `[rename]` table and a `reserved` list
- **THEN** neither is reported as unsupported

#### Scenario: Patches table

- **WHEN** the TOML has a `[patches]` table
- **THEN** it is not reported as unsupported

#### Scenario: Prefix key

- **WHEN** `[sources.mp]` has `git = "…"` and `prefix = "mp-"`
- **THEN** `prefix` is not reported as unsupported
