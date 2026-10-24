## ADDED Requirements

### Requirement: Check limits

An optional `[check]` table SHALL set the limits of a hardened **Check**: `reader-turns` (default 30), `patcher-turns`
(default 10) and `readers-at-once` (default 4), each a positive integer written in decimal digits, and
`reader-budget-usd` (default 1.0) and `patcher-budget-usd` (default 0.5), each a positive number written in decimal
digits with an optional fraction. A key left out SHALL take its default. Any other value, or the same value in
another TOML form, SHALL be an error naming the key and what it must be, so the text the skill reads is the value.

#### Scenario: Defaults

- **WHEN** the TOML has no `[check]` table
- **THEN** the command succeeds as before

#### Scenario: Some limits set

- **WHEN** `[check]` has `reader-turns = 50`, `patcher-budget-usd = 2` and `reader-budget-usd = 0.25`
- **THEN** the command succeeds

#### Scenario: Turns not a positive integer

- **WHEN** `[check]` has `reader-turns = 0`, `reader-turns = 1.5`, `reader-turns = "30"`, `reader-turns = true`,
  `reader-turns = 0x1E`, `reader-turns = 3_0` or `reader-turns = +30`
- **THEN** the command exits non-zero naming `check.reader-turns` and a positive integer

#### Scenario: Budget not a positive number

- **WHEN** `[check]` has `reader-budget-usd = 0`, `reader-budget-usd = 0.0`, `reader-budget-usd = -1`,
  `reader-budget-usd = inf`, `reader-budget-usd = "1"`, `reader-budget-usd = true` or `reader-budget-usd = 1e0`
- **THEN** the command exits non-zero naming `check.reader-budget-usd` and a positive number

#### Scenario: Check not a table

- **WHEN** the TOML has `check = 4`
- **THEN** the command exits non-zero naming `check` and the expected table

## MODIFIED Requirements

### Requirement: Unsupported keys are errors

Any top-level key other than `sources`, `entries`, `bind`, `rename`, `reserved`, `patches` and `check`, any source key
other than `path`, `git`, `branch`, `ref`, `prefix` and `subdirectory`, and any `[check]` key other than
`reader-turns`, `reader-budget-usd`, `patcher-turns`, `patcher-budget-usd` and `readers-at-once`, SHALL be an error,
so declared intent is never silently ignored.

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

#### Scenario: Subdirectory key

- **WHEN** `[sources.cp]` has `git = "…"` and `subdirectory = "pstack/skills"`
- **THEN** `subdirectory` is not reported as unsupported

#### Scenario: Check key

- **WHEN** `[check]` has `reader-turns = 30` and `max-readers = 8`
- **THEN** the command exits non-zero naming `check.max-readers` as unsupported, and not `check.reader-turns`
