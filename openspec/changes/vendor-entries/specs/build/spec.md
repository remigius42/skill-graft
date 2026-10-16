# Spec Delta

## Purpose

Vendors the **Entries** into the skill-graft APM package and deploys it through APM, failing loudly where APM
would fail quietly.

## ADDED Requirements

### Requirement: Vendor entries

`skill-graft build` SHALL make `~/.apm/skill-graft/.apm/skills/` hold exactly one folder per **Entry**, named
after the **Entry**'s name and holding a copy of the **Skill**'s whole folder. Nothing outside that folder is
vendored. Folders from earlier builds that are no longer **Entries** SHALL be removed.

#### Scenario: Whole folder copied

- **WHEN** **Entry** `own/chisel` is a folder holding `SKILL.md` and `refs/notes.md`
- **THEN** `.apm/skills/chisel/` holds `SKILL.md` and `refs/notes.md`, byte for byte

#### Scenario: Removed entry

- **WHEN** a previous build vendored `chisel` and `chisel` is no longer an **Entry**
- **THEN** `.apm/skills/chisel/` no longer exists after `build`

### Requirement: Deployed names are unique

Since this version has no **Renames**, each **Entry**'s **Deployed name** is its name. Two **Entries** with the
same **Deployed name** SHALL be an error, and `build` SHALL then write nothing.

#### Scenario: Clash across sources

- **WHEN** `mp/tdd` and `own/tdd` are both **Entries**
- **THEN** `build` exits non-zero naming both and leaves `.apm/skills/` unchanged

### Requirement: Deploy through APM

After vendoring, `build` SHALL run `apm install -g` and succeed only if APM exits 0 and `~/.apm/apm.yml` lists
`~/.apm/skill-graft`, written either with `~` or as an absolute path. APM's output SHALL reach the user.

#### Scenario: APM succeeds

- **WHEN** APM exits 0 and `~/.apm/apm.yml` lists the package
- **THEN** `build` exits 0

#### Scenario: APM exits non-zero

- **WHEN** `apm install -g` exits non-zero
- **THEN** `build` exits non-zero reporting APM's exit code

#### Scenario: Package not registered

- **WHEN** APM exits 0 but `~/.apm/apm.yml` is missing or does not list the package
- **THEN** `build` exits non-zero and prints `apm install -g ~/.apm/skill-graft` as the fix

#### Scenario: APM missing

- **WHEN** `apm` is not on `PATH`
- **THEN** `build` exits non-zero saying APM is not installed, after vendoring

### Requirement: Build without installing

`build --no-install` SHALL vendor as above and SHALL NOT run `apm` or read `~/.apm/apm.yml`.

#### Scenario: No install

- **WHEN** the user runs `skill-graft build --no-install`
- **THEN** `.apm/skills/` is written, `apm` is not run, and `build` exits 0
