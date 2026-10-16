# Spec Delta

## Purpose

Reads the user's intent from `~/.apm/skill-graft/skill-graft.toml`: path **Sources** and **Entries**, rejecting
anything this version cannot honor.

## ADDED Requirements

### Requirement: Path sources

Each `[sources.<alias>]` table SHALL hold exactly one key, `path`: a folder, with `~` expanded and a relative
path taken relative to the folder holding `skill-graft.toml`. The alias names the **Source**.

#### Scenario: Home-relative path

- **WHEN** `[sources.own]` has `path = "~/skills"`
- **THEN** **Source** `own` is the folder `skills` under the user's home

#### Scenario: Missing folder

- **WHEN** a source's `path` does not name an existing folder
- **THEN** the command exits non-zero naming the alias and the path

### Requirement: Entries

`entries` SHALL be a list of **Skill IDs** of the form `<alias>/<name>`. An empty or absent list is valid and
builds no skills.

#### Scenario: Entry with an undeclared alias

- **WHEN** `entries = ["mp/tdd"]` and no `[sources.mp]` exists
- **THEN** the command exits non-zero naming `mp/tdd` and the alias `mp`

#### Scenario: Malformed entry

- **WHEN** an entry has no `/`, or an empty alias or name
- **THEN** the command exits non-zero naming the entry

### Requirement: Unsupported keys are errors

Any top-level key other than `sources` and `entries`, and any source key other than `path`, SHALL be an error,
so declared intent is never silently ignored.

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
