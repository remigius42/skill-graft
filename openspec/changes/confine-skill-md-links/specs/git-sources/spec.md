## MODIFIED Requirements

### Requirement: The checkout is the upstream tree

A git **Source**'s folder SHALL be the full tree of its `ref` with the bytes as committed, the same on every
machine: files marked `export-ignore` included, no `.gitattributes` conversion or filter applied, exec bits and
symlinks kept; with `subdirectory`, that folder of the tree. Skill discovery and vendoring then work as for a path
**Source**, except that discovery follows only symlinked folders that stay inside the **Source**'s folder, and
opens a `SKILL.md` that is a symlink only when it resolves inside its **Skill**'s folder: their author is not the
user. A **Skill** whose `SKILL.md` is a symlink resolving outside its folder SHALL have an unreadable name, its error
naming the link by its full path and not what it leads to.
Submodules SHALL be skipped and LFS objects SHALL NOT be fetched (their pointer files are vendored as committed).

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

#### Scenario: SKILL.md linked out of the tree

- **WHEN** commit A holds `evil/SKILL.md` as a symlink to a local file whose front matter holds `name: leaked-marker`,
  and `mp/evil` is an **Entry**
- **THEN** the command exits non-zero naming `evil/SKILL.md` as a link leading outside its **Skill**, and its output
  holds neither `leaked-marker` nor the local file's path

#### Scenario: Unused skill linked out of the tree

- **WHEN** commit A holds `evil/SKILL.md` as a symlink to `/dev/zero`, and `mp/tdd`, another **Skill** of commit A,
  is the only **Entry**
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
