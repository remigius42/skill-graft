# Spec Delta

## ADDED Requirements

### Requirement: Patches

`[patches]` SHALL be a table whose keys are **Skill IDs**, every alias declared, and whose values are non-empty
lists of file paths, `~` expanded and relative ones taken relative to the folder holding `skill-graft.toml`.
Every listed file SHALL be readable, used or not. A malformed key or value, an undeclared alias, a missing or
unreadable file, or one file listed twice under one key (compared resolved) SHALL be an error naming the key.

#### Scenario: Valid patches

- **WHEN** `[patches]` has `"mp/tdd" = ["patches/tdd.patch"]`, `mp` is declared, and the file exists
- **THEN** the config loads

#### Scenario: Value not a list of paths

- **WHEN** `[patches]` has `"mp/tdd" = "patches/tdd.patch"`, `"mp/tdd" = []` or `"mp/tdd" = [1]`
- **THEN** the command exits non-zero naming `patches."mp/tdd"`

#### Scenario: Undeclared alias in a patch

- **WHEN** `[patches]` has `"nope/tdd" = ["patches/tdd.patch"]` and no `[sources.nope]` exists
- **THEN** the command exits non-zero naming `patches."nope/tdd"` and `nope`

#### Scenario: Missing patch file

- **WHEN** `[patches]` has `"mp/tdd" = ["patches/gone.patch"]`, the file does not exist, and `mp/tdd` is not in
  the **Hull**
- **THEN** the command exits non-zero naming `patches."mp/tdd"` and `patches/gone.patch`

#### Scenario: Listed twice

- **WHEN** `"mp/tdd" = ["patches/a.patch", "./patches/a.patch"]`
- **THEN** the command exits non-zero naming `patches."mp/tdd"` and `a.patch`

#### Scenario: Shared patch

- **WHEN** `"mp/tdd"` and `"mp/notes"` both list `patches/common.patch`
- **THEN** the config loads

## MODIFIED Requirements

### Requirement: Unsupported keys are errors

Any top-level key other than `sources`, `entries`, `bind`, `rename`, `reserved` and `patches`, and any source key
other than `path`, `git`, `branch` and `ref`, SHALL be an error, so declared intent is never silently ignored.

#### Scenario: Git source

- **WHEN** `[sources.mp]` has `git = "…"` and `tag = "v1"`
- **THEN** the command exits non-zero naming `sources.mp.tag` as unsupported

#### Scenario: Rename table

- **WHEN** the TOML has a `[rename]` table and a `reserved` list
- **THEN** neither is reported as unsupported

#### Scenario: Patches table

- **WHEN** the TOML has a `[patches]` table
- **THEN** it is not reported as unsupported
