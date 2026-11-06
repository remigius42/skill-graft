## ADDED Requirements

### Requirement: Reference prefix

`reference-prefix`, an optional top-level key, SHALL be a string of the name characters and `:`, starting with a letter
or digit (`[A-Za-z0-9][A-Za-z0-9._:-]*`); anything else, the empty string included, SHALL be an error naming
`reference-prefix`.

#### Scenario: Valid reference prefix

- **WHEN** `skill-graft.toml` has `reference-prefix = "foo:"`, `reference-prefix = "foo"` or
  `reference-prefix = "my.plugin:"`
- **THEN** the config loads

#### Scenario: Reference prefix not allowed

- **WHEN** `skill-graft.toml` has `reference-prefix = ""`, `":foo"`, `"foo/"`, `"foo bar:"` or `1`
- **THEN** the command exits non-zero naming `reference-prefix`

#### Scenario: No separator at the end

- **WHEN** `skill-graft.toml` has `reference-prefix = "foo"`
- **THEN** the command warns that `reference-prefix` ends in a letter or digit, and proceeds

#### Scenario: Separator at the end

- **WHEN** `skill-graft.toml` has `reference-prefix = "foo:"` or `reference-prefix = "foo-"`
- **THEN** no warning names `reference-prefix`

## MODIFIED Requirements

### Requirement: Unsupported keys are errors

Any top-level key other than `sources`, `entries`, `bind`, `rename`, `reserved`, `patches`, `check` and
`reference-prefix`, any source key other than `path`, `git`, `branch`, `ref`, `prefix` and `subdirectory`, and any
`[check]` key other than `reader-turns`, `reader-budget-usd`, `patcher-turns`, `patcher-budget-usd` and
`readers-at-once`, SHALL be an error, so declared intent is never silently ignored.

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

#### Scenario: Reference prefix key

- **WHEN** the TOML has `reference-prefix = "foo:"`
- **THEN** it is not reported as unsupported

#### Scenario: Reference prefix on a source

- **WHEN** `[sources.mp]` has `git = "…"` and `reference-prefix = "foo:"`
- **THEN** the command exits non-zero naming `sources.mp.reference-prefix` as unsupported
