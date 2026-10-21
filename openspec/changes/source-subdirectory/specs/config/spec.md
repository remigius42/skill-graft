# config Delta

## MODIFIED Requirements

### Requirement: Value types

`sources` SHALL be a table of tables, each source's `path`, `git`, `branch`, `ref`, `prefix` and `subdirectory` a
string, and `entries` a list of strings. A wrong type or a source table with neither `path` nor `git` SHALL be an
error naming the key, never a crash.

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

#### Scenario: Subdirectory not a string

- **WHEN** `[sources.cp]` has `git = "…"` and `subdirectory = 1`
- **THEN** the command exits non-zero naming `sources.cp.subdirectory`

### Requirement: Unsupported keys are errors

Any top-level key other than `sources`, `entries`, `bind`, `rename`, `reserved` and `patches`, and any source key
other than `path`, `git`, `branch`, `ref`, `prefix` and `subdirectory`, SHALL be an error, so declared intent is
never silently ignored.

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

### Requirement: Source kinds

Each `[sources.<alias>]` table SHALL hold exactly one of `path` and `git`. Both, or neither, SHALL be an error
naming the source. `branch`, `ref` and `subdirectory` SHALL be allowed only beside `git`.

#### Scenario: Both kinds

- **WHEN** `[sources.mp]` has both `path` and `git`
- **THEN** the command exits non-zero naming `sources.mp`

#### Scenario: Ref on a path source

- **WHEN** `[sources.own]` has `path` and `ref`
- **THEN** the command exits non-zero naming `sources.own.ref` as unsupported

#### Scenario: Subdirectory on a path source

- **WHEN** `[sources.own]` has `path = "~/plugins"` and `subdirectory = "pstack/skills"`
- **THEN** the command exits non-zero naming `sources.own.subdirectory` as unsupported

## ADDED Requirements

### Requirement: Git source subdirectory

A git source's `subdirectory`, if present, SHALL be a relative path of segments separated by `/`, each non-empty
and neither `.` nor `..`, with no control character and no segment `.apm` followed by `skill-graft`. Anything
else, the empty string, a leading or trailing `/` and `//` included, SHALL be an error naming
`sources.<alias>.subdirectory`, never a crash. Loading SHALL NOT read the repository; the commit read checks the
folder.

#### Scenario: Valid subdirectory

- **WHEN** `[sources.cp]` has `git = "https://github.com/cursor/plugins.git"` and `subdirectory = "pstack/skills"`
- **THEN** the config loads

#### Scenario: Subdirectory leaving the repository

- **WHEN** `[sources.cp]` has `subdirectory` set to `"../x"`, `"a/../../x"`, `"/etc"`, `"."`, `"a/./b"`, `""`,
  `"a//b"` or `"a/"`
- **THEN** the command exits non-zero naming `sources.cp.subdirectory`, and git is never run

#### Scenario: Control character

- **WHEN** `[sources.cp]` has `subdirectory = "a\u0000b"` or `subdirectory = "a\nb"`
- **THEN** the command exits non-zero naming `sources.cp.subdirectory`, without a traceback

#### Scenario: Subdirectory into a package

- **WHEN** `[sources.cp]` has `subdirectory = "proj/.apm/skill-graft/.apm/skills"`
- **THEN** the command exits non-zero naming `sources.cp.subdirectory`
