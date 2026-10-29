# git-sources Specification

## Purpose

Fetches git **Sources** into a cache outside the package and reads each at its **Ref**, so a build is the same wherever
and whenever it runs.

## Requirements

### Requirement: Cache outside the package

Git **Sources** SHALL be cached under `$XDG_CACHE_HOME/skill-graft/`, else `~/.cache/skill-graft/`: one bare repository
per git URL, shared by every alias naming that URL and fetched at most once per command, and one checkout per commit.
Deleting the cache SHALL lose nothing: the next command that needs a **Ref** fetches it again. An interrupted clone or
checkout SHALL never be mistaken for a complete one, nor block the next run.

#### Scenario: Default location

- **WHEN** `XDG_CACHE_HOME` is unset and `build` reads a git **Source**
- **THEN** its repository and checkout are under `~/.cache/skill-graft/`, and `build` writes nothing under
  `~/.apm/skill-graft/` outside `.apm/skills/` and `skill-graft.lock`

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

The cache repository SHALL use the remote's object format, SHA-1 or SHA-256, so a `ref` of either length works.

#### Scenario: SHA-256 remote

- **WHEN** a git **Source** names a SHA-256 repository and `ref` is a 64-digit commit name in it
- **THEN** `build` vendors the skills at that commit

### Requirement: Read at the ref

A command that reads a git **Source**'s skills SHALL read them at its `ref`, exactly, and SHALL never change `ref` or
read any other commit. A commit in the cache SHALL be used without contacting the remote. Only when the commit is
missing SHALL the command fetch every branch; if the commit is still missing, that SHALL be an error naming the alias
and the `ref`.

#### Scenario: Upstream moved on

- **WHEN** `ref` names commit A, A is in the cache, the remote's branch has moved to commit B, and the user runs `build`
- **THEN** the vendored skills are those at A, the remote is not contacted, and `skill-graft.toml` is unchanged

#### Scenario: Fresh machine

- **WHEN** the cache is empty and `ref` names commit A
- **THEN** `build` clones the repository and vendors the skills at A

#### Scenario: Ref gone upstream

- **WHEN** `ref` names a commit that is missing from the cache and on no branch of the remote
- **THEN** the command exits non-zero naming the alias and the `ref`

### Requirement: Build needs every ref

`build` SHALL fail when any git **Source** has no `ref`, whether or not an **Entry** uses it, naming every such alias
and telling the user to run the one `skill-graft update` command naming them all. `build` SHALL then write nothing.

#### Scenario: New git source

- **WHEN** `[sources.mp]` has `git` but no `ref`
- **THEN** `build` exits non-zero naming `mp` and `skill-graft update mp`

#### Scenario: Several new git sources

- **WHEN** `[sources.a]` and `[sources.b]` both have `git` but no `ref`
- **THEN** `build` exits non-zero naming `a`, `b` and `skill-graft update a b`

### Requirement: The checkout is the upstream tree

A git **Source**'s folder SHALL be the full tree of its `ref` with the bytes as committed, the same on every machine:
files marked `export-ignore` included, no `.gitattributes` conversion or filter applied, exec bits and symlinks kept;
with `subdirectory`, that folder of the tree. Skill discovery and vendoring then work as for a path **Source**, except
that discovery follows only symlinked folders that stay inside the **Source**'s folder, and opens a `SKILL.md` that is a
symlink only when it resolves inside its **Skill**'s folder: their author is not the user. A **Skill** whose `SKILL.md`
is a symlink resolving outside its folder SHALL have an unreadable name, its error naming the link by its full path and
not what it leads to. Submodules SHALL be skipped and LFS objects SHALL NOT be fetched (their pointer files are vendored
as committed).

#### Scenario: Skill from git

- **WHEN** commit A of source `mp` holds `skills/tdd/SKILL.md` and `skills/tdd/refs/x.md`, and `mp/tdd` is an **Entry**
- **THEN** `build` vendors `.apm/skills/tdd/` holding both files, without `.git`

#### Scenario: Attributes ignored

- **WHEN** commit A has `.gitattributes` with `* text eol=crlf` and `*.md filter=f`, the user's git config defines
  `filter.f.smudge`, and `SKILL.md` was committed with LF line endings
- **THEN** the vendored `SKILL.md` equals the committed blob byte for byte

#### Scenario: Link out of the tree

- **WHEN** commit A holds `out` as a symlink to a local folder holding `secret/SKILL.md`, and `mp/secret` is an
  **Entry**
- **THEN** `build` exits non-zero naming `mp/secret`, and nothing local is vendored

#### Scenario: SKILL.md linked out of the tree

- **WHEN** commit A holds `evil/SKILL.md` as a symlink to a local file whose front matter holds `name: leaked-marker`,
  and `mp/evil` is an **Entry**
- **THEN** the command exits non-zero naming `evil/SKILL.md` as a link leading outside its **Skill**, and its output
  holds neither `leaked-marker` nor the local file's path

#### Scenario: Unused skill linked out of the tree

- **WHEN** commit A holds `evil/SKILL.md` as a symlink to `/dev/zero`, and `mp/tdd`, another **Skill** of commit A, is
  the only **Entry**
- **THEN** `build` finishes and vendors `tdd`

#### Scenario: SKILL.md linked inside its skill

- **WHEN** commit A holds `tdd/SKILL.md` as a symlink to `tdd/main.md`, whose front matter holds `name: tdd`, and
  `mp/tdd` is an **Entry**
- **THEN** `build` vendors `.apm/skills/tdd/` with `SKILL.md` holding `main.md`'s content

#### Scenario: Hostile tree

- **WHEN** commit A holds two entries named `a`, a symlink to a folder outside and a folder holding `x`
- **THEN** the command exits non-zero naming `a`, and nothing is written outside the cache

#### Scenario: Modes kept

- **WHEN** commit A holds an executable `scripts/run.sh` and a symlink `refs/a.md` → `b.md` inside a skill
- **THEN** the vendored `run.sh` is executable and `a.md` holds `b.md`'s content

### Requirement: Read only the subdirectory

A git **Source** with `subdirectory` SHALL have as its folder that subdirectory of the tree at the commit read: its
`ref`, or its branch tip during `update`. Discovery SHALL walk it as it walks a tree's root, following only symlinked
folders that stay inside the subdirectory. Skills elsewhere in the tree SHALL NOT be **Skills** of the **Source**, not
even as targets of a **Reference**.

#### Scenario: One plugin of many

- **WHEN** commit A of `cp` holds `pstack/skills/tdd/SKILL.md` and `harness/skills/tdd/SKILL.md`,
  `subdirectory = "pstack/skills"`, and `cp/tdd` is an **Entry**
- **THEN** `build` vendors `pstack/skills/tdd` as `tdd`, without an error about several skills matching

#### Scenario: Skill outside the subdirectory

- **WHEN** `subdirectory = "skills"`, commit A holds `skills/a/SKILL.md` calling `/b` and `.claude/skills/b/SKILL.md`,
  and `x/a` is an **Entry**
- **THEN** `x/b` is not in the **Hull**, and the unresolved-reference warning names `/b`

#### Scenario: Link out of the subdirectory

- **WHEN** `subdirectory = "skills"`, and commit A holds `skills/more` as a symlink to `../other`, which holds
  `c/SKILL.md`
- **THEN** `c` is not a **Skill** of the **Source**

#### Scenario: Skill at the subdirectory

- **WHEN** `subdirectory = "plugins/chisel"` and commit A holds `plugins/chisel/SKILL.md` naming `chisel`
- **THEN** `chisel` is a **Skill** of the **Source**

### Requirement: The subdirectory is a real folder at the commit

A command reading a git **Source** with `subdirectory` SHALL fail, naming the alias, the subdirectory and the commit,
when at that commit the subdirectory is missing, is not a folder, or has a symlink anywhere in its path.

#### Scenario: Missing at ref

- **WHEN** `subdirectory = "pstack/skills"` and commit A has no `pstack/skills`
- **THEN** `resolve` and `build` exit non-zero naming the alias, `pstack/skills` and A, and write nothing

#### Scenario: A file, not a folder

- **WHEN** commit A holds `pstack/skills` as a file
- **THEN** the command exits non-zero naming the alias, `pstack/skills` and A

#### Scenario: Symlinked subdirectory

- **WHEN** `subdirectory = "skills/pstack"` and commit A holds `skills` as a symlink to `plugins`, which holds
  `pstack/tdd/SKILL.md`
- **THEN** the command exits non-zero naming the alias, `skills/pstack` and A

#### Scenario: Case differs

- **WHEN** `subdirectory = "PStack/skills"` and commit A holds `pstack/skills`, on a case-insensitive file system as on
  any other
- **THEN** the command exits non-zero naming the alias, `PStack/skills` and A

#### Scenario: Shared export

- **WHEN** `[sources.a]` and `[sources.b]` have the same `git` URL and `ref`, `a` with `subdirectory = "x/skills"` and
  `b` with `subdirectory = "y/skills"`
- **THEN** the cache holds one export of that commit, and each **Source** has only the **Skills** under its own
  subdirectory

### Requirement: Git failures are reported

When `git` is not on `PATH`, or a clone or fetch fails, the command SHALL exit non-zero naming the alias and the URL and
showing git's error output, never a traceback. Git and ssh SHALL prompt for credentials as they do in the user's shell,
with the user's git config applied.

#### Scenario: Unreachable remote

- **WHEN** `[sources.mp]` has `git` naming a folder that does not exist and the cache lacks its `ref`
- **THEN** the command exits non-zero naming `mp` and the URL

#### Scenario: Git missing

- **WHEN** `git` is not on `PATH` and a git **Source** must be read
- **THEN** the command exits non-zero saying git is not installed
