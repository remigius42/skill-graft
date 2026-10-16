# Spec Delta

## Purpose

Fetches git **Sources** into a cache outside the package and reads each at its **Ref**, so a build is the same
wherever and whenever it runs.

## ADDED Requirements

### Requirement: Cache outside the package

Git **Sources** SHALL be cached under `$XDG_CACHE_HOME/skill-graft/`, else `~/.cache/skill-graft/`: one bare
repository per git URL, shared by every alias naming that URL and fetched at most once per command, and one
checkout per commit. Deleting the cache SHALL lose nothing: the next command that needs a **Ref** fetches it
again. An interrupted clone or checkout SHALL never be mistaken for a complete one, nor block the next run.

#### Scenario: Default location

- **WHEN** `XDG_CACHE_HOME` is unset and `build` reads a git **Source**
- **THEN** its repository and checkout are under `~/.cache/skill-graft/`, and `build` writes nothing under
  `~/.apm/skill-graft/` outside `.apm/skills/`

#### Scenario: Shared URL

- **WHEN** `[sources.a]` and `[sources.b]` have the same `git` URL
- **THEN** the cache holds one repository for both, and a command fetches it once

#### Scenario: Cache deleted

- **WHEN** the user deletes the cache folder and runs `build`
- **THEN** `build` fetches again and vendors the same files

#### Scenario: Interrupted checkout

- **WHEN** a previous run left a partial checkout of the `ref` behind
- **THEN** the next `build` ignores it, checks the `ref` out again, and vendors every file

#### Scenario: Concurrent runs

- **WHEN** two commands export the same `ref`, or clone the same URL, at the same time
- **THEN** both succeed, and the cache holds one export or repository

#### Scenario: Interrupted clone

- **WHEN** a previous run was killed while cloning a git **Source** for the first time
- **THEN** the next `build` clones it again and succeeds

### Requirement: Hash format of the remote

The cache repository SHALL use the remote's object format, SHA-1 or SHA-256, so a `ref` of either length
works.

#### Scenario: SHA-256 remote

- **WHEN** a git **Source** names a SHA-256 repository and `ref` is a 64-digit commit name in it
- **THEN** `build` vendors the skills at that commit

### Requirement: Read at the ref

A command that reads a git **Source**'s skills SHALL read them at its `ref`, exactly, and SHALL never change
`ref` or read any other commit. A commit in the cache SHALL be used without contacting the remote. Only when
the commit is missing SHALL the command fetch every branch; if the commit is still missing, that SHALL be an
error naming the alias and the `ref`.

#### Scenario: Upstream moved on

- **WHEN** `ref` names commit A, A is in the cache, the remote's branch has moved to commit B, and the user runs
  `build`
- **THEN** the vendored skills are those at A, the remote is not contacted, and `skill-graft.toml` is unchanged

#### Scenario: Fresh machine

- **WHEN** the cache is empty and `ref` names commit A
- **THEN** `build` clones the repository and vendors the skills at A

#### Scenario: Ref gone upstream

- **WHEN** `ref` names a commit that is missing from the cache and on no branch of the remote
- **THEN** the command exits non-zero naming the alias and the `ref`

### Requirement: Build needs every ref

`build` SHALL fail when any git **Source** has no `ref`, whether or not an **Entry** uses it, naming the alias
and telling the user to run `skill-graft update <alias>`. `build` SHALL then write nothing.

#### Scenario: New git source

- **WHEN** `[sources.mp]` has `git` but no `ref`
- **THEN** `build` exits non-zero naming `mp` and `skill-graft update mp`

### Requirement: The checkout is the upstream tree

A git **Source**'s folder SHALL be the full tree of its `ref` with the bytes as committed, the same on every
machine: files marked `export-ignore` included, no `.gitattributes` conversion or filter applied, exec bits and
symlinks kept. Skill discovery and vendoring then work as for a path **Source**, except that discovery follows
only symlinked folders that stay inside the tree: their author is not the user. Submodules SHALL be skipped
and LFS objects SHALL NOT be fetched (their pointer files are vendored as committed).

#### Scenario: Skill from git

- **WHEN** commit A of source `mp` holds `skills/tdd/SKILL.md` and `skills/tdd/refs/x.md`, and `mp/tdd` is an
  **Entry**
- **THEN** `build` vendors `.apm/skills/tdd/` holding both files, without `.git`

#### Scenario: Attributes ignored

- **WHEN** commit A has `.gitattributes` with `* text eol=crlf` and `*.md filter=f`, the user's git config
  defines `filter.f.smudge`, and `SKILL.md` was committed with LF line endings
- **THEN** the vendored `SKILL.md` equals the committed blob byte for byte

#### Scenario: Link out of the tree

- **WHEN** commit A holds `out` as a symlink to a local folder holding `secret/SKILL.md`, and `mp/secret` is an
  **Entry**
- **THEN** `build` exits non-zero naming `mp/secret`, and nothing local is vendored

#### Scenario: Hostile tree

- **WHEN** commit A holds two entries named `a`, a symlink to a folder outside and a folder holding `x`
- **THEN** the command exits non-zero naming `a`, and nothing is written outside the cache

#### Scenario: Modes kept

- **WHEN** commit A holds an executable `scripts/run.sh` and a symlink `refs/a.md` → `b.md` inside a skill
- **THEN** the vendored `run.sh` is executable and `a.md` holds `b.md`'s content

### Requirement: Git failures are reported

When `git` is not on `PATH`, or a clone or fetch fails, the command SHALL exit non-zero naming the alias and
the URL and showing git's error output, never a traceback. Git and ssh SHALL prompt for credentials as they do
in the user's shell, with the user's git config applied.

#### Scenario: Unreachable remote

- **WHEN** `[sources.mp]` has `git` naming a folder that does not exist and the cache lacks its `ref`
- **THEN** the command exits non-zero naming `mp` and the URL

#### Scenario: Git missing

- **WHEN** `git` is not on `PATH` and a git **Source** must be read
- **THEN** the command exits non-zero saying git is not installed
