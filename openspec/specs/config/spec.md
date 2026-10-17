# config Specification

## Purpose

Reads the user's intent from `~/.apm/skill-graft/skill-graft.toml`: path **Sources** and **Entries**, rejecting
anything this version cannot honor.

## Requirements

### Requirement: Path sources

A path source's `path` SHALL name a folder, with `~` expanded and a relative path taken relative to the folder
holding `skill-graft.toml`. The alias names the **Source** and SHALL be one path segment:
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

A source whose folder is inside `~/.apm/skill-graft/` or contains it SHALL be an error. A source inside or
containing an APM deploy folder (`~/.agents/skills`, `~/.claude/skills`, and the other harness skill folders)
SHALL be a warning naming the alias and the folder. Paths are compared resolved.

#### Scenario: Source is the package

- **WHEN** `[sources.own]` has `path = "."` (the folder holding `skill-graft.toml`)
- **THEN** the command exits non-zero naming `own` and writes nothing

#### Scenario: Source is a deploy folder

- **WHEN** `[sources.own]` has `path = "~/.agents/skills"`
- **THEN** the command prints a warning naming `own` and `~/.agents/skills`, and continues

### Requirement: Entries

`entries` SHALL be a list of **Skill IDs** of the form `<alias>/<name>`. An empty or absent list is valid and
builds no skills.

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

`sources` SHALL be a table of tables, each source's `path`, `git`, `branch` and `ref` a string, and `entries` a
list of strings. A wrong type or a source table with neither `path` nor `git` SHALL be an error naming the key,
never a crash.

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

### Requirement: Missing or invalid config

A missing `skill-graft.toml` or one that is not valid TOML SHALL be an error naming the file.

#### Scenario: Not initialized

- **WHEN** `~/.apm/skill-graft/skill-graft.toml` does not exist
- **THEN** the command exits non-zero and tells the user to run `skill-graft init`

### Requirement: Source kinds

Each `[sources.<alias>]` table SHALL hold exactly one of `path` and `git`. Both, or neither, SHALL be an error
naming the source. `branch` and `ref` SHALL be allowed only beside `git`.

#### Scenario: Both kinds

- **WHEN** `[sources.mp]` has both `path` and `git`
- **THEN** the command exits non-zero naming `sources.mp`

#### Scenario: Ref on a path source

- **WHEN** `[sources.own]` has `path` and `ref`
- **THEN** the command exits non-zero naming `sources.own.ref` as unsupported

### Requirement: Git sources

A git source's `git` SHALL be a string handed to git unchanged, and SHALL be a URL with scheme `https`,
`http`, `ssh`, `git` or `file`, the scp-like form (`[user@]host:path`), or an absolute local path. A relative
path (including one starting with `~`), a value starting with `-`, any other scheme, and the
`<transport>::<address>` form SHALL be errors naming `sources.<alias>.git`. `branch`, if present, SHALL be a
branch name such as `main`, not a full reference name such as `refs/heads/main`. `ref`, if present, SHALL be a
full lowercase hex commit name, 40 or 64 digits; anything else SHALL be an error naming `sources.<alias>.ref`.
Loading accepts a git source without `ref`, so `update` can fill it in.

#### Scenario: Relative git path

- **WHEN** `[sources.mp]` has `git = "../skills"` or `git = "~/skills"`
- **THEN** the command exits non-zero naming `sources.mp.git` and the accepted forms

#### Scenario: Option or helper as URL

- **WHEN** `[sources.mp]` has `git = "--upload-pack=touch x"`, `git = "ext::sh -c touch% x"`, or
  `git = "foo://x"`
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
