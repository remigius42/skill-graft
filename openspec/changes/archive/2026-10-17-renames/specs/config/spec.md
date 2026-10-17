# Spec Delta

## ADDED Requirements

### Requirement: Renames

`[rename]` SHALL be a table whose keys are **Skill IDs**, every alias declared, and whose values are names, one
path segment each (`[A-Za-z0-9][A-Za-z0-9._-]*`). A malformed key or value, or an undeclared alias, SHALL be an
error naming the key.

#### Scenario: Valid rename

- **WHEN** `[rename]` has `"mp/code-review" = "mp-code-review"`, and `mp` is declared
- **THEN** the config loads

#### Scenario: Value not a name

- **WHEN** `[rename]` has `"mp/tdd" = "a/b"`, `"mp/tdd" = ""` or `"mp/tdd" = 1`
- **THEN** the command exits non-zero naming `rename."mp/tdd"`

#### Scenario: Undeclared alias in a rename

- **WHEN** `[rename]` has `"nope/tdd" = "tdd2"` and no `[sources.nope]` exists
- **THEN** the command exits non-zero naming `rename."nope/tdd"` and `nope`

### Requirement: Reserved names

`reserved` SHALL be a list of names, one path segment each. Anything else SHALL be an error naming `reserved`.

#### Scenario: Valid reserved list

- **WHEN** `reserved = ["review"]`
- **THEN** the config loads

#### Scenario: Reserved not a list of names

- **WHEN** `reserved = "review"` or `reserved = ["a/b"]`
- **THEN** the command exits non-zero naming `reserved`

## MODIFIED Requirements

### Requirement: Unsupported keys are errors

Any top-level key other than `sources`, `entries`, `bind`, `rename` and `reserved`, and any source key other
than `path`, `git`, `branch` and `ref`, SHALL be an error, so declared intent is never silently ignored.

#### Scenario: Git source

- **WHEN** `[sources.mp]` has `git = "…"` and `tag = "v1"`
- **THEN** the command exits non-zero naming `sources.mp.tag` as unsupported

#### Scenario: Rename table

- **WHEN** the TOML has a `[rename]` table and a `reserved` list
- **THEN** neither is reported as unsupported

#### Scenario: Patches table

- **WHEN** the TOML has a `[patches]` table
- **THEN** the command exits non-zero naming `patches` as unsupported
