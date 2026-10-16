# Spec Delta

## Purpose

Vendors the **Entries** into the skill-graft APM package and deploys it through APM, failing loudly where APM
would fail quietly.

## ADDED Requirements

### Requirement: Vendor entries

`skill-graft build` SHALL make `~/.apm/skill-graft/.apm/skills/` hold exactly one folder per **Entry**, named
after the **Entry**'s name and holding a copy of the **Skill**'s whole folder. Nothing outside that folder is
vendored. Folders from earlier builds that are no longer **Entries** SHALL be removed. The folder SHALL be
replaced only once every copy succeeded; a failed copy SHALL leave it as it was.

#### Scenario: Whole folder copied

- **WHEN** **Entry** `own/chisel` is a folder holding `SKILL.md` and `refs/notes.md`
- **THEN** `.apm/skills/chisel/` holds `SKILL.md` and `refs/notes.md`, byte for byte

#### Scenario: Removed entry

- **WHEN** a previous build vendored `chisel` and `chisel` is no longer an **Entry**
- **THEN** `.apm/skills/chisel/` no longer exists after `build`

#### Scenario: Copy fails

- **WHEN** a previous build vendored `chisel`, and an **Entry**'s folder holds a symlink to a missing file
  inside it
- **THEN** `build` exits non-zero naming the file, and `.apm/skills/` still holds the previous `chisel`

### Requirement: Symlinks stay within the skill

A symlink in an **Entry**'s folder SHALL lead to a file inside that folder, and SHALL be vendored as a copy of
that file. A symlink leading outside the folder, or to any folder (which could form a cycle), SHALL be an error
naming the link, and `build` SHALL then write nothing. Symlinks under `.git`, which is never vendored, are not
checked.

#### Scenario: Symlink leaving the skill

- **WHEN** an **Entry**'s folder holds a symlink to a file or folder outside it, or to a folder inside it
- **THEN** `build` exits non-zero naming the symlink and writes nothing

#### Scenario: Symlink loop

- **WHEN** an **Entry**'s folder holds a symlink that points to itself
- **THEN** `build` exits non-zero naming the symlink, on every supported Python version

#### Scenario: Symlink within the skill

- **WHEN** an **Entry**'s folder holds a symlink to a file inside it
- **THEN** the vendored copy holds that file's content as a regular file

### Requirement: Deployed names are unique

Since this version has no **Renames**, each **Entry**'s **Deployed name** is its name. Two **Entries** with the
same **Deployed name** SHALL be an error, and `build` SHALL then write nothing.

#### Scenario: Clash across sources

- **WHEN** `mp/tdd` and `own/tdd` are both **Entries**
- **THEN** `build` exits non-zero naming both and leaves `.apm/skills/` unchanged

### Requirement: Deploy through APM

After vendoring, `build` SHALL run `apm install -g <absolute path of ~/.apm/skill-graft>`, which also
registers the package, and succeed only if APM exits 0 and `~/.apm/apm.yml` lists the package: as `- x` or
`- path: x`, with `~` or an absolute path, compared resolved. APM's output SHALL reach the user.

#### Scenario: APM succeeds

- **WHEN** APM exits 0 and `~/.apm/apm.yml` lists the package
- **THEN** `build` exits 0

#### Scenario: Registration removed by hand

- **WHEN** the user deleted the package's line from `~/.apm/apm.yml` and runs `build`
- **THEN** APM re-adds it and `build` exits 0

#### Scenario: Symlinked home

- **WHEN** `HOME` is a symlink and `~/.apm/apm.yml` lists the package by its resolved path
- **THEN** `build` treats the package as registered

#### Scenario: APM exits non-zero

- **WHEN** `apm install -g` exits non-zero
- **THEN** `build` exits non-zero reporting APM's exit code

#### Scenario: Package not registered

- **WHEN** APM exits 0 but `~/.apm/apm.yml` is missing or does not list the package
- **THEN** `build` exits non-zero naming `~/.apm/apm.yml` and the expected path

#### Scenario: APM missing

- **WHEN** `apm` is not on `PATH`
- **THEN** `build` exits non-zero saying APM is not installed, after vendoring

### Requirement: Build without installing

`build --no-install` SHALL vendor as above and SHALL NOT run `apm` or read `~/.apm/apm.yml`.

#### Scenario: No install

- **WHEN** the user runs `skill-graft build --no-install`
- **THEN** `.apm/skills/` is written, `apm` is not run, and `build` exits 0
