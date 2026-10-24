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

A source whose folder is inside, or contains, the **Package** in effect or the user scope's **Package** SHALL
be an error. A source inside or containing an APM deploy folder
(`~/.agents/skills`, `~/.claude/skills`, and the other harness skill folders) SHALL be a warning naming the
alias and the folder; in project scope, also `.agents/skills`, `.claude/skills`, `.grok/skills` and
`.kiro/skills` under the project root. Paths are compared resolved.

#### Scenario: Source is the package

- **WHEN** `[sources.own]` has `path = "."` (the folder holding `skill-graft.toml`)
- **THEN** the command exits non-zero naming `own` and writes nothing

#### Scenario: Source is a deploy folder

- **WHEN** `[sources.own]` has `path = "~/.agents/skills"`
- **THEN** the command prints a warning naming `own` and `~/.agents/skills`, and continues

#### Scenario: Source is the project's deploy folder

- **WHEN** in project scope `[sources.own]` has `path = "../../.claude/skills"`
- **THEN** the command prints a warning naming `own` and `<project>/.claude/skills`, and continues

#### Scenario: Project source is a user deploy folder

- **WHEN** in project scope `[sources.own]` has `path = "~/.claude/skills"`
- **THEN** the command prints a warning naming `own` and `~/.claude/skills`, and continues

#### Scenario: Source contains the project package

- **WHEN** in project scope `[sources.own]` has `path = "../.."` (the project root)
- **THEN** the command exits non-zero naming `own` and writes nothing

#### Scenario: Project source contains the user package

- **WHEN** in project scope `[sources.own]` has `path = "~/.apm"`
- **THEN** the command exits non-zero naming `own` and `~/.apm/skill-graft`, and writes nothing

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

### Requirement: Missing or invalid config

A missing `skill-graft.toml` or one that is not valid TOML SHALL be an error naming the file.

#### Scenario: Not initialized

- **WHEN** `~/.apm/skill-graft/skill-graft.toml` does not exist
- **THEN** the command exits non-zero and tells the user to run `skill-graft init`

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

### Requirement: Git source subdirectory

A git source's `subdirectory`, if present, SHALL be a relative path of segments separated by `/`, each non-empty
and neither `.`, `..` nor `.git` in any case, with no control character and no segment `.apm` followed by
`skill-graft`. Anything else, the empty string, a leading or trailing `/` and `//` included, SHALL be an error naming
`sources.<alias>.subdirectory`, never a crash. Loading SHALL NOT read the repository; the commit read checks the
folder.

#### Scenario: Valid subdirectory

- **WHEN** `[sources.cp]` has `git = "https://github.com/cursor/plugins.git"` and `subdirectory = "pstack/skills"`
- **THEN** the config loads

#### Scenario: Subdirectory leaving the repository

- **WHEN** `[sources.cp]` has `subdirectory` set to `"../x"`, `"a/../../x"`, `"/etc"`, `"."`, `"a/./b"`, `""`,
  `"a//b"`, `"a/"`, `"a/.git/b"` or `".GIT"`
- **THEN** the command exits non-zero naming `sources.cp.subdirectory`, and git is never run

#### Scenario: Control character

- **WHEN** `[sources.cp]` has `subdirectory = "a\u0000b"` or `subdirectory = "a\nb"`
- **THEN** the command exits non-zero naming `sources.cp.subdirectory`, without a traceback

#### Scenario: Subdirectory into a package

- **WHEN** `[sources.cp]` has `subdirectory = "proj/.apm/skill-graft/.apm/skills"`
- **THEN** the command exits non-zero naming `sources.cp.subdirectory`

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

### Requirement: Prefixes

A source's `prefix`, on a path or a git **Source**, SHALL be a name, one path segment
(`[A-Za-z0-9][A-Za-z0-9._-]*`); anything else, the empty string included, SHALL be an error naming
`sources.<alias>.prefix`.

#### Scenario: Valid prefix

- **WHEN** `[sources.mp]` has `git = "…"` and `prefix = "mp-"`, or `[sources.own]` has `path = "…"` and
  `prefix = "own."`
- **THEN** the config loads

#### Scenario: Prefix without a kind

- **WHEN** `[sources.mp]` holds only `prefix = "mp-"`
- **THEN** the command exits non-zero saying `sources.mp` needs `path` or `git`, not that `prefix` is unsupported

#### Scenario: Prefix not a name

- **WHEN** `[sources.mp]` has `prefix = ""`, `prefix = "-x"`, `prefix = "a/"` or `prefix = 1`
- **THEN** the command exits non-zero naming `sources.mp.prefix`

### Requirement: Reserved names

`reserved` SHALL be a list of names, one path segment each. Anything else SHALL be an error naming `reserved`.

#### Scenario: Valid reserved list

- **WHEN** `reserved = ["review"]`
- **THEN** the config loads

#### Scenario: Reserved not a list of names

- **WHEN** `reserved = "review"` or `reserved = ["a/b"]`
- **THEN** the command exits non-zero naming `reserved`

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

### Requirement: Patch files git would misread

A listed patch file holding a line `git apply` skips as noise, losing a change silently (`Binary files … differ`,
`Only in …`), or a `GIT binary patch` block, SHALL be an error naming the file, used or not.

#### Scenario: Binary change

- **WHEN** a listed patch holds a `Binary files upstream/x.png and edited/x.png differ` line, or a
  `GIT binary patch` block, and its key names no **Hull** **Skill**
- **THEN** the command exits non-zero naming the patch file

#### Scenario: Added file without -N

- **WHEN** a listed patch holds an `Only in edited/refs: new.md` line, as `diff -ru` without `-N` writes it
- **THEN** the command exits non-zero naming the patch file
