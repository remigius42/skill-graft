# Spec Delta

## Purpose

Reads the user's intent from `~/.apm/skill-graft/skill-graft.toml`: path **Sources** and **Entries**, rejecting anything
this version cannot honor.

## ADDED Requirements

### Requirement: Path sources

Each `[sources.<alias>]` table SHALL hold exactly one key, `path`: a folder, with `~` expanded and a relative path taken
relative to the folder holding `skill-graft.toml`. The alias names the **Source** and SHALL be one path segment:
`[A-Za-z0-9][A-Za-z0-9._-]*`.

#### Scenario: Home-relative path

- **WHEN** `[sources.own]` has `path = "~/skills"`
- **THEN** **Source** `own` is the folder `skills` under the user's home

#### Scenario: Missing folder

- **WHEN** a source's `path` does not name an existing folder
- **THEN** the command exits non-zero naming the alias and the path

#### Scenario: Bad alias

- **WHEN** the TOML has `[sources."a/b"]` or `[sources.".."]`
- **THEN** the command exits non-zero naming the alias

### Requirement: Sources stay clear of the package and deploy folders

A source whose folder is inside `~/.apm/skill-graft/` or contains it SHALL be an error. A source inside or containing an
APM deploy folder (`~/.agents/skills`, `~/.claude/skills`, and the other harness skill folders) SHALL be a warning
naming the alias and the folder. Paths are compared resolved.

#### Scenario: Source is the package

- **WHEN** `[sources.own]` has `path = "."` (the folder holding `skill-graft.toml`)
- **THEN** the command exits non-zero naming `own` and writes nothing

#### Scenario: Source is a deploy folder

- **WHEN** `[sources.own]` has `path = "~/.agents/skills"`
- **THEN** the command prints a warning naming `own` and `~/.agents/skills`, and continues

### Requirement: Entries

`entries` SHALL be a list of **Skill IDs** of the form `<alias>/<name>`. An empty or absent list is valid and builds no
skills.

#### Scenario: Entry with an undeclared alias

- **WHEN** `entries = ["mp/tdd"]` and no `[sources.mp]` exists
- **THEN** the command exits non-zero naming `mp/tdd` and the alias `mp`

#### Scenario: Malformed entry

- **WHEN** an entry has no `/`, or an empty alias or name
- **THEN** the command exits non-zero naming the entry

#### Scenario: Repeated entry

- **WHEN** `entries = ["own/a", "own/a"]`
- **THEN** the command exits non-zero naming `own/a` as repeated

### Requirement: Value types

`sources` SHALL be a table of tables, each source's `path` a string, and `entries` a list of strings. A wrong type or a
source table without `path` SHALL be an error naming the key, never a crash.

#### Scenario: Entries as a string

- **WHEN** `entries = "own/chisel"`
- **THEN** the command exits non-zero naming `entries` and the expected list

#### Scenario: Empty source

- **WHEN** the TOML has `[sources.own]` with no keys
- **THEN** the command exits non-zero naming `sources.own.path` as missing

#### Scenario: Path not a string

- **WHEN** `[sources.own]` has `path = 1`
- **THEN** the command exits non-zero naming `sources.own.path`

### Requirement: Unsupported keys are errors

Any top-level key other than `sources` and `entries`, and any source key other than `path`, SHALL be an error, so
declared intent is never silently ignored.

#### Scenario: Git source

- **WHEN** `[sources.mp]` has `git = "https://example.com/skills.git"`
- **THEN** the command exits non-zero naming `sources.mp.git` as unsupported

#### Scenario: Rename table

- **WHEN** the TOML has a `[rename]` table
- **THEN** the command exits non-zero naming `rename` as unsupported

### Requirement: Missing or invalid config

A missing `skill-graft.toml` or one that is not valid TOML SHALL be an error naming the file.

#### Scenario: Not initialized

- **WHEN** `~/.apm/skill-graft/skill-graft.toml` does not exist
- **THEN** the command exits non-zero and tells the user to run `skill-graft init`
