# Spec Delta

## ADDED Requirements

### Requirement: Build resolves first

`build` SHALL resolve the **Hull** as `resolve` does and print its warnings before vendoring, and write
`skill-graft.lock` once vendoring succeeded, before running APM. A resolution or vendoring error SHALL leave the lock
unchanged.

#### Scenario: Lock written

- **WHEN** the user runs `build --no-install`
- **THEN** `skill-graft.lock` records the vendored **Hull**

#### Scenario: Vendoring fails

- **WHEN** a copy fails during `build`
- **THEN** `skill-graft.lock` is unchanged

#### Scenario: Warning does not stop build

- **WHEN** an **Entry** calls `/foo` and no **Source** has `foo`
- **THEN** `build` prints the warning and exits 0

## MODIFIED Requirements

### Requirement: Vendor entries

`skill-graft build` SHALL make `~/.apm/skill-graft/.apm/skills/` hold exactly one folder per **Hull** **Skill**, named
after the **Skill**'s name and holding a copy of the **Skill**'s whole folder. Nothing outside that folder is vendored.
Folders from earlier builds that are no longer in the **Hull** SHALL be removed. The folder SHALL be replaced only once
every copy succeeded; a failed copy SHALL leave it as it was.

#### Scenario: Whole folder copied

- **WHEN** **Entry** `own/chisel` is a folder holding `SKILL.md` and `refs/notes.md`
- **THEN** `.apm/skills/chisel/` holds `SKILL.md` and `refs/notes.md`, byte for byte

#### Scenario: Referenced skill vendored

- **WHEN** **Entry** `mp/tdd` calls `/grilling`, and `mp` has `grilling`
- **THEN** `.apm/skills/` holds `tdd/` and `grilling/`

#### Scenario: Removed entry

- **WHEN** a previous build vendored `chisel` and `chisel` is no longer in the **Hull**
- **THEN** `.apm/skills/chisel/` no longer exists after `build`

#### Scenario: Copy fails

- **WHEN** a previous build vendored `chisel`, and a **Hull** **Skill**'s folder holds a file the user cannot read
- **THEN** `build` exits non-zero naming the file, and `.apm/skills/` still holds the previous `chisel`

### Requirement: Symlinks stay within the skill

A symlink in a **Hull** **Skill**'s folder SHALL lead to an existing regular file inside that folder, and SHALL be
vendored as a copy of that file. A symlink leading outside the folder, to a missing file, to a FIFO or device, or to any
folder (which could form a cycle), SHALL be an error naming the link, and `build` SHALL then write nothing. Symlinks
under `.git`, which is never vendored, are not checked.

#### Scenario: Symlink leaving the skill

- **WHEN** a **Hull** **Skill**'s folder holds a symlink to a file or folder outside it, or to a folder inside it
- **THEN** `build` exits non-zero naming the symlink and writes nothing

#### Scenario: Symlink loop

- **WHEN** a **Hull** **Skill**'s folder holds a symlink that points to itself
- **THEN** `build` exits non-zero naming the symlink, on every supported Python version

#### Scenario: Symlink within the skill

- **WHEN** a **Hull** **Skill**'s folder holds a symlink to a file inside it
- **THEN** the vendored copy holds that file's content as a regular file

### Requirement: Deployed names are unique

Since this version has no **Renames**, each **Hull** **Skill**'s **Deployed name** is its name. Two **Hull** **Skills**
with the same **Deployed name**, compared ignoring case, SHALL be an error naming both, and `build` SHALL then write
nothing.

#### Scenario: Clash across sources

- **WHEN** `mp/tdd` and `own/tdd` are both **Entries**
- **THEN** `build` exits non-zero naming both and leaves `.apm/skills/` unchanged

#### Scenario: Clash through a reference

- **WHEN** **Entry** `own/grilling` exists, and **Entry** `mp/tdd` calls `/grilling`, resolved to `mp/grilling`
- **THEN** `build` exits non-zero naming `mp/grilling` and `own/grilling`
