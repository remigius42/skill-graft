# git-sources Delta

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

#### Scenario: Shared export

- **WHEN** `[sources.a]` and `[sources.b]` have the same `git` URL and `ref`, `a` with
  `subdirectory = "x/skills"` and `b` with `subdirectory = "y/skills"`
- **THEN** the cache holds one export of that commit, and each **Source** has only the **Skills** under its own
  subdirectory
