# Spec Delta

## ADDED Requirements

### Requirement: Source kinds

Each `[sources.<alias>]` table SHALL hold exactly one of `path` and `git`. Both, or neither, SHALL be an error naming
the source. `branch` and `ref` SHALL be allowed only beside `git`.

#### Scenario: Both kinds

- **WHEN** `[sources.mp]` has both `path` and `git`
- **THEN** the command exits non-zero naming `sources.mp`

#### Scenario: Ref on a path source

- **WHEN** `[sources.own]` has `path` and `ref`
- **THEN** the command exits non-zero naming `sources.own.ref` as unsupported

### Requirement: Git sources

A git source's `git` SHALL be a string handed to git unchanged, and SHALL be a URL with scheme `https`, `http`, `ssh`,
`git` or `file`, the scp-like form (`[user@]host:path`), or an absolute local path. A relative path (including one
starting with `~`), a value starting with `-`, any other scheme, and the `<transport>::<address>` form SHALL be errors
naming `sources.<alias>.git`. `branch`, if present, SHALL be a branch name such as `main`, not a full reference name
such as `refs/heads/main`. `ref`, if present, SHALL be a full lowercase hex commit name, 40 or 64 digits; anything else
SHALL be an error naming `sources.<alias>.ref`. Loading accepts a git source without `ref`, so `update` can fill it in.

#### Scenario: Relative git path

- **WHEN** `[sources.mp]` has `git = "../skills"` or `git = "~/skills"`
- **THEN** the command exits non-zero naming `sources.mp.git` and the accepted forms

#### Scenario: Option or helper as URL

- **WHEN** `[sources.mp]` has `git = "--upload-pack=touch x"`, `git = "ext::sh -c touch% x"`, or `git = "foo://x"`
- **THEN** the command exits non-zero naming `sources.mp.git`, and git is never run

#### Scenario: Accepted forms

- **WHEN** `git` is `https://example.com/s.git`, `git@example.com:me/s.git`, or `/srv/skills`
- **THEN** the source loads

#### Scenario: Short ref

- **WHEN** `[sources.mp]` has `ref = "abc1234"`
- **THEN** the command exits non-zero naming `sources.mp.ref` and the expected form

#### Scenario: Branch as full reference name

- **WHEN** `[sources.mp]` has `branch = "refs/heads/main"`
- **THEN** the command exits non-zero naming `sources.mp.branch`

## MODIFIED Requirements

### Requirement: Path sources

A path source's `path` SHALL name a folder, with `~` expanded and a relative path taken relative to the folder holding
`skill-graft.toml`. The alias names the **Source** and SHALL be one path segment: `[A-Za-z0-9][A-Za-z0-9._-]*`.

#### Scenario: Home-relative path

- **WHEN** `[sources.own]` has `path = "~/skills"`
- **THEN** **Source** `own` is the folder `skills` under the user's home

#### Scenario: Missing folder

- **WHEN** a source's `path` does not name an existing folder
- **THEN** the command exits non-zero naming the alias and the path

#### Scenario: Bad alias

- **WHEN** the TOML has `[sources."a/b"]` or `[sources.".."]`
- **THEN** the command exits non-zero naming the alias

### Requirement: Value types

`sources` SHALL be a table of tables, each source's `path`, `git`, `branch` and `ref` a string, and `entries` a list of
strings. A wrong type or a source table with neither `path` nor `git` SHALL be an error naming the key, never a crash.

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

Any top-level key other than `sources` and `entries`, and any source key other than `path`, `git`, `branch` and `ref`,
SHALL be an error, so declared intent is never silently ignored.

#### Scenario: Git source

- **WHEN** `[sources.mp]` has `git = "…"` and `tag = "v1"`
- **THEN** the command exits non-zero naming `sources.mp.tag` as unsupported

#### Scenario: Rename table

- **WHEN** the TOML has a `[rename]` table
- **THEN** the command exits non-zero naming `rename` as unsupported
