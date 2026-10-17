# build Specification

## Purpose

Vendors the **Entries** into the skill-graft APM package and deploys it through APM, failing loudly where APM
would fail quietly.

## Requirements

### Requirement: Vendor entries

`skill-graft build` SHALL make `~/.apm/skill-graft/.apm/skills/` hold exactly one folder per **Hull** **Skill**,
named after the **Skill**'s **Deployed name** and holding a copy of the **Skill**'s whole folder, renamed and
rewritten as the `renames` capability says and otherwise byte for byte. Nothing outside that folder is vendored.
Folders from earlier builds that are no longer in the **Hull** SHALL be removed. The folder SHALL be replaced only
once every copy succeeded; a failed copy SHALL leave it as it was.

#### Scenario: Whole folder copied

- **WHEN** **Entry** `own/chisel` is a folder holding `SKILL.md` and `refs/notes.md`
- **THEN** `.apm/skills/chisel/` holds `SKILL.md` and `refs/notes.md`, byte for byte

#### Scenario: Referenced skill vendored

- **WHEN** **Entry** `mp/tdd` calls `/grilling`, and `mp` has `grilling`
- **THEN** `.apm/skills/` holds `tdd/` and `grilling/`

#### Scenario: Renamed skill vendored

- **WHEN** **Entry** `mp/tdd` is renamed to `mp-tdd`
- **THEN** `.apm/skills/` holds `mp-tdd/` and no `tdd/`

#### Scenario: Removed entry

- **WHEN** a previous build vendored `chisel` and `chisel` is no longer in the **Hull**
- **THEN** `.apm/skills/chisel/` no longer exists after `build`

#### Scenario: Copy fails

- **WHEN** a previous build vendored `chisel`, and a **Hull** **Skill**'s folder holds a file the user cannot
  read
- **THEN** `build` exits non-zero naming the file, and `.apm/skills/` still holds the previous `chisel`

### Requirement: Symlinks stay within the skill

A symlink in a **Hull** **Skill**'s folder SHALL lead to an existing regular file inside that folder, and SHALL be
vendored as a copy of that file. A symlink leading outside the folder, to a missing file, to a FIFO or device, or
to any folder (which could form a cycle), SHALL be an error naming the link, and `build` SHALL then write nothing.
Symlinks under `.git`, which is never vendored, are not checked.

#### Scenario: Symlink leaving the skill

- **WHEN** a **Hull** **Skill**'s folder holds a symlink to a file or folder outside it, or to a folder inside it
- **THEN** `build` exits non-zero naming the symlink and writes nothing

#### Scenario: Symlink loop

- **WHEN** a **Hull** **Skill**'s folder holds a symlink that points to itself
- **THEN** `build` exits non-zero naming the symlink, on every supported Python version

#### Scenario: Symlink within the skill

- **WHEN** a **Hull** **Skill**'s folder holds a symlink to a file inside it
- **THEN** the vendored copy holds that file's content as a regular file

### Requirement: Deploy through APM

After vendoring, `build` SHALL run `apm install -g <absolute path of ~/.apm/skill-graft>`, which also
registers the package, and succeed only if APM exits 0 and `~/.apm/apm.yml` lists the package: as `- x` or
`- path: x`, with `~` or an absolute path, compared resolved. In project scope it SHALL instead run
`apm install ./.apm/skill-graft` in the project root and check the project root's `apm.yml`, where a relative
path is relative to the project root. APM's output SHALL reach the user.

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

#### Scenario: Project build from a subfolder

- **WHEN** the user runs `skill-graft build` in `~/repo/src`, `~/repo/.apm/skill-graft/` exists, and APM exits 0
  leaving `- ./.apm/skill-graft` in `~/repo/apm.yml`
- **THEN** APM ran in `~/repo` with `install ./.apm/skill-graft` and no `-g`, and `build` exits 0

#### Scenario: Project package not registered

- **WHEN** in project scope APM exits 0 but `<project>/apm.yml` does not list the package
- **THEN** `build` exits non-zero naming `<project>/apm.yml` and the expected path

### Requirement: Build without installing

`build --no-install` SHALL vendor as above and SHALL NOT run `apm` or read the scope's `apm.yml`.

#### Scenario: No install

- **WHEN** the user runs `skill-graft build --no-install`
- **THEN** `.apm/skills/` is written, `apm` is not run, and `build` exits 0

### Requirement: Build resolves first

`build` SHALL resolve the **Hull** as `resolve` does and print its warnings before vendoring, and write
`skill-graft.lock` once vendoring succeeded, before running APM. A resolution or vendoring error SHALL leave the
lock unchanged.

#### Scenario: Lock written

- **WHEN** the user runs `build --no-install`
- **THEN** `skill-graft.lock` records the vendored **Hull**

#### Scenario: Vendoring fails

- **WHEN** a copy fails during `build`
- **THEN** `skill-graft.lock` is unchanged

#### Scenario: Warning does not stop build

- **WHEN** an **Entry** calls `/foo` and no **Source** has `foo`
- **THEN** `build` prints the warning and exits 0
