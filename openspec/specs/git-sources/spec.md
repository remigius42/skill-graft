# git-sources Specification

## Purpose

Fetches git **Sources** into a cache outside the package and reads each at its **Ref**, so a build is the same wherever
and whenever it runs.

## Requirements

### Requirement: Cache outside the package

Git **Sources** SHALL be cached under `$XDG_CACHE_HOME/skill-graft/`, else `~/.cache/skill-graft/`: one bare repository
per git URL, shared by every alias naming that URL and fetched at most once per command, and one export per commit and
`subdirectory`. Deleting the cache SHALL lose nothing the remote still has: the next command that needs a **Ref**
fetches it again. An interrupted clone or export SHALL never be mistaken for a complete one, nor block the next run.

#### Scenario: Default location

- **WHEN** `XDG_CACHE_HOME` is unset and `build` reads a git **Source**
- **THEN** its repository and export are under `~/.cache/skill-graft/`, and `build` writes nothing under
  `~/.apm/skill-graft/` outside `.apm/skills/` and `skill-graft.lock`

#### Scenario: Shared URL

- **WHEN** `[sources.a]` and `[sources.b]` have the same `git` URL
- **THEN** the cache holds one repository for both, and a command fetches it once

#### Scenario: Cache deleted

- **WHEN** the user deletes the cache folder and runs `build`
- **THEN** `build` fetches again and vendors the same files

#### Scenario: Ref vanished, then cache deleted

- **WHEN** `ref` names commit A, A has been read before, the remote's branch was then reset so that A is on no branch,
  and the user deletes the cache folder and runs `build`
- **THEN** `build` exits non-zero naming the alias and the `ref`

#### Scenario: Interrupted checkout

- **WHEN** a previous run left a partial export of the `ref` behind
- **THEN** the next `build` ignores it, exports the `ref` again, and vendors every file

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
read any other commit. A commit in the cache whose files at the `subdirectory` read are in the cache too SHALL be used
without contacting the remote. When the commit is missing, the command SHALL fetch every branch; if the commit is still
missing, that SHALL be an error naming the alias and the `ref`. When only files are missing, it SHALL fetch just those.
With git 2.44 or later, looking up whether the cache holds a commit or a file SHALL never contact the remote.

#### Scenario: Upstream moved on

- **WHEN** `ref` names commit A, A has been read before, the remote's branch has moved to commit B, and the user runs
  `build`
- **THEN** the vendored skills are those at A, the remote is not contacted, and `skill-graft.toml` is unchanged

#### Scenario: Fresh machine

- **WHEN** the cache is empty and `ref` names commit A
- **THEN** `build` clones the repository and vendors the skills at A

#### Scenario: Ref gone upstream

- **WHEN** `ref` names a commit that is missing from the cache and on no branch of the remote, though the remote would
  still serve it asked by name
- **THEN** the command exits non-zero naming the alias and the `ref`

#### Scenario: Commit cached, files not

- **WHEN** commit A is in the cache, `[sources.a]` has read it with `subdirectory = "x"`, `[sources.b]` names the same
  URL and A with `subdirectory = "y"` for the first time, and the remote is unreachable
- **THEN** reading `b` exits non-zero naming `b` and the URL

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
- **THEN** the cache holds one repository and two exports of that commit, one holding only `x/skills` and the other only
  `y/skills`, and each **Source** has only the **Skills** under its own subdirectory

#### Scenario: Same subdirectory

- **WHEN** `[sources.a]` and `[sources.b]` have the same `git` URL, `ref` and `subdirectory`
- **THEN** the cache holds one export of that commit for both

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

### Requirement: Exports prune themselves

Every command that reads through the cache SHALL, at its end, whether it succeeded or failed, remove each export, and
each leftover of an interrupted export or clone, that no command has used for 30 days. A command SHALL mark each export
it uses as used. `update --dry-run` SHALL neither mark nor remove anything in the cache. An export removed SHALL be
exported again from the cached repository when next needed, without the remote.

#### Scenario: Stale export removed

- **WHEN** the cache holds an export last used 31 days ago, and the user runs `resolve`
- **THEN** after `resolve` the export is gone

#### Scenario: Export in use kept

- **WHEN** the export of `mp`'s `ref` was last used 31 days ago, and the user runs `build`
- **THEN** `build` vendors from it, and the export is still in the cache afterwards

#### Scenario: Recent export kept

- **WHEN** the cache holds an export last used 29 days ago that the command does not read
- **THEN** after the command the export is still in the cache

#### Scenario: Failed command prunes too

- **WHEN** the cache holds an export last used 31 days ago, and `build` fails on a patch that does not apply
- **THEN** after `build` the export is gone

#### Scenario: Leftover removed

- **WHEN** a run killed 31 days ago left a partial export behind
- **THEN** the next command removes it

#### Scenario: Clone leftover removed

- **WHEN** a run killed 31 days ago while cloning a git **Source** for the first time left a partial clone behind
- **THEN** the next command removes it, and leaves every repository in place

#### Scenario: Dry run prunes nothing

- **WHEN** the cache holds an export last used 31 days ago, and the user runs `update --dry-run`
- **THEN** the export is still in the cache, its last use unchanged

#### Scenario: Pruned export read offline

- **WHEN** the export of `mp`'s `ref` was removed as unused, and `mp`'s remote is unreachable
- **THEN** `build` exports the `ref` again from the cache and vendors the same files

### Requirement: Repositories are kept

No command SHALL delete a cached repository, however long unused. Each commit a command reads, other than in
`update --dry-run`, SHALL stay in its repository with the files read at it, even after it vanished from every branch of
its remote and later fetches and git's housekeeping ran: the repository may then hold its only copy.

#### Scenario: Unused repository

- **WHEN** the cache holds a repository no command has read for 31 days, and the user runs `resolve`
- **THEN** after `resolve` the repository is still in the cache

#### Scenario: Ref vanished upstream

- **WHEN** `ref` names commit A, `build` has read A, the remote's branch was then reset so that A is on no branch, the
  repository was fetched again and garbage-collected, its export of A was pruned, and the remote is unreachable
- **THEN** `build` exports A again from the cache and vendors the same files

### Requirement: Fetch only what is read

A clone, and each later fetch into it, SHALL download commits and trees but no file contents; an export SHALL download
the contents of the files it writes and no others, in one request to the remote. An export SHALL hold only the
**Source**'s `subdirectory` of the tree, and the entries on the way to it. A repository cloned whole before, or from a
remote refusing partial clones, SHALL stay whole; one whose remote refuses files by name SHALL be fetched whole, once,
outside `update --dry-run`, with git 2.36 or later. Any other failure to fetch files SHALL leave the repository as it
was.

#### Scenario: One subdirectory of a monorepo

- **WHEN** commit A of `cp` holds `pstack/skills/tdd/SKILL.md` and `harness/big.bin`, `subdirectory = "pstack/skills"`,
  and the cache is empty
- **THEN** after `build` the cache holds neither the contents of `harness/big.bin` nor an export of it

#### Scenario: Remote without partial clones

- **WHEN** `[sources.mp]` names a remote that refuses partial clones
- **THEN** `build` clones it whole and vendors the skills at the `ref`

#### Scenario: Remote refusing files by name

- **WHEN** `[sources.mp]` names a remote that accepts a partial clone but speaks a protocol that refuses files asked by
  name, and the cache is empty
- **THEN** `build` vendors the skills at the `ref`, the repository then holds every file of every branch, and a later
  `build` at another `ref` asks the remote for nothing by name

#### Scenario: Files unreachable for a moment

- **WHEN** the cache holds a blobless repository of `mp`, the export of a new `ref` needs files, and the remote is
  unreachable
- **THEN** the command exits non-zero naming `mp` and the URL, and a later fetch into the repository still downloads no
  file contents

#### Scenario: Repository cloned whole before

- **WHEN** the cache holds a repository cloned whole by an earlier skill-graft, and `update` fetches a new tip
- **THEN** the repository holds every file of the new tip, as before
