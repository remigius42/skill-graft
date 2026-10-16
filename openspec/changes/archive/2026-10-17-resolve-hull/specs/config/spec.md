# Spec Delta

## ADDED Requirements

### Requirement: Binds

`[bind]` SHALL be a table whose keys are `<alias>/<name>` and whose values are **Skill IDs** or `false`, every
alias declared and every part one path segment (`[A-Za-z0-9][A-Za-z0-9._-]*`). A malformed key or value
(`true` included), or an undeclared alias, SHALL be an error naming the key.

#### Scenario: Valid bind

- **WHEN** `[bind]` has `"mp/grilling" = "own/grill"`, and `mp` and `own` are declared
- **THEN** the config loads

#### Scenario: Undeclared alias

- **WHEN** `[bind]` has `"mp/grilling" = "nope/grill"` and no `[sources.nope]` exists
- **THEN** the command exits non-zero naming `bind."mp/grilling"` and `nope`

#### Scenario: Bind to nothing

- **WHEN** `[bind]` has `"mp/tmp" = false`
- **THEN** the config loads

#### Scenario: Value neither a skill ID nor false

- **WHEN** `[bind]` has `"mp/grilling" = 1` or `"mp/grilling" = true`
- **THEN** the command exits non-zero naming `bind."mp/grilling"`

## MODIFIED Requirements

### Requirement: Unsupported keys are errors

Any top-level key other than `sources`, `entries` and `bind`, and any source key other than `path`, `git`,
`branch` and `ref`, SHALL be an error, so declared intent is never silently ignored.

#### Scenario: Git source

- **WHEN** `[sources.mp]` has `git = "…"` and `tag = "v1"`
- **THEN** the command exits non-zero naming `sources.mp.tag` as unsupported

#### Scenario: Rename table

- **WHEN** the TOML has a `[rename]` table
- **THEN** the command exits non-zero naming `rename` as unsupported
