# git-sources Delta

## MODIFIED Requirements

### Requirement: The checkout is the upstream tree

A git **Source**'s folder SHALL be the full tree of its `ref` with the bytes as committed, the same on every
machine: files marked `export-ignore` included, no `.gitattributes` conversion or filter applied, exec bits and
symlinks kept; with `subdirectory`, that folder of the tree. Skill discovery and vendoring then work as for a path
**Source**, except that discovery follows only symlinked folders that stay inside the **Source**'s folder: their
author is not the user. Submodules SHALL be skipped and LFS objects SHALL NOT be fetched (their pointer files are
vendored as committed).

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

## ADDED Requirements

### Requirement: Read only the subdirectory

A git **Source** with `subdirectory` SHALL have as its folder that subdirectory of the tree at the commit read:
its `ref`, or its branch tip during `update`. Discovery SHALL walk it as it walks a tree's root, following only
symlinked folders that stay inside the subdirectory. Skills elsewhere in the tree SHALL NOT be **Skills** of the
**Source**, not even as targets of a **Reference**.

#### Scenario: One plugin of many

- **WHEN** commit A of `cp` holds `pstack/skills/tdd/SKILL.md` and `harness/skills/tdd/SKILL.md`,
  `subdirectory = "pstack/skills"`, and `cp/tdd` is an **Entry**
- **THEN** `build` vendors `pstack/skills/tdd` as `tdd`, without an error about several skills matching

#### Scenario: Skill outside the subdirectory

- **WHEN** `subdirectory = "skills"`, commit A holds `skills/a/SKILL.md` calling `/b` and
  `.claude/skills/b/SKILL.md`, and `x/a` is an **Entry**
- **THEN** `x/b` is not in the **Hull**, and the unresolved-reference warning names `/b`

#### Scenario: Link out of the subdirectory

- **WHEN** `subdirectory = "skills"`, and commit A holds `skills/more` as a symlink to `../other`, which holds
  `c/SKILL.md`
- **THEN** `c` is not a **Skill** of the **Source**

#### Scenario: Skill at the subdirectory

- **WHEN** `subdirectory = "plugins/chisel"` and commit A holds `plugins/chisel/SKILL.md` naming `chisel`
- **THEN** `chisel` is a **Skill** of the **Source**

### Requirement: The subdirectory is a real folder at the commit

A command reading a git **Source** with `subdirectory` SHALL fail, naming the alias, the subdirectory and the
commit, when at that commit the subdirectory is missing, is not a folder, or has a symlink anywhere in its path.

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

- **WHEN** `subdirectory = "PStack/skills"` and commit A holds `pstack/skills`, on a case-insensitive file system
  as on any other
- **THEN** the command exits non-zero naming the alias, `PStack/skills` and A

#### Scenario: Shared export

- **WHEN** `[sources.a]` and `[sources.b]` have the same `git` URL and `ref`, `a` with
  `subdirectory = "x/skills"` and `b` with `subdirectory = "y/skills"`
- **THEN** the cache holds one export of that commit, and each **Source** has only the **Skills** under its own
  subdirectory
