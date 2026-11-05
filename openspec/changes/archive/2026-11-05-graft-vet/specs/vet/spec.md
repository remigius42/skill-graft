# Spec Delta

## MODIFIED Requirements

### Requirement: Vetting writes nothing

`vet` SHALL compute the **Hull** from `skill-graft.toml` as `resolve` does, fetching only a commit missing from the
cache, with the same warnings and the same errors, a **Hidden character** and a **Patch** that does not apply included.
It SHALL NOT read or write `skill-graft.lock`, write `skill-graft.toml` or `.apm/skills/`, or run `apm`; it SHALL write
nothing else but the folder `--into` names (Vet into a folder).

#### Scenario: No lock

- **WHEN** `skill-graft.lock` does not exist and the user runs `skill-graft vet`
- **THEN** it prints its **Flags**, exits 0, and `skill-graft.lock` still does not exist

#### Scenario: Hidden character

- **WHEN** a **Hull** **Skill**'s `SKILL.md` holds U+E0041
- **THEN** `skill-graft vet` exits 1, naming that file as `resolve` does, and prints no **Flag**

## ADDED Requirements

### Requirement: Vet into a folder

`vet --into <dir>` SHALL also write each vetted **Skill**'s files, as they would deploy and as it scanned them, to
`<dir>/<alias>/<name>/`, once every **Skill** is scanned, and print the same **Flags**. `<dir>` SHALL be refused as
`deploy --into` refuses its folder: not an existing empty folder, in a **Package**, a path **Source** or the git cache.
Besides a commit fetched into the git cache, it SHALL be the only thing `vet` writes; on any error `<dir>` SHALL stay
empty.

#### Scenario: A Skill not yet added

- **WHEN** `mp/review` is in no **Hull** and calls `/diagnose`, and the user runs
  `skill-graft vet --into <dir> mp/review` with `<dir>` an empty temporary folder
- **THEN** `<dir>` holds `mp/review/` and `mp/diagnose/`, their files as they would deploy, and `skill-graft.toml`, the
  lock and `.apm/skills/` are unchanged

#### Scenario: Patched and renamed

- **WHEN** a **Hull** **Skill** `mp/tdd` has a **Patch** and calls `/grilling`, deployed as `mp-grilling`
- **THEN** `<dir>/mp/tdd/SKILL.md` holds the patched line and `/mp-grilling`, byte for byte as `deploy` would vendor it

#### Scenario: A Skill with no Flag

- **WHEN** a vetted **Skill** holds nothing `vet` flags
- **THEN** its folder is still written under `<dir>`

#### Scenario: Folder not empty

- **WHEN** `<dir>` holds a file, or lies inside the **Package**
- **THEN** `vet --into <dir>` exits 1 naming `<dir>`, prints no **Flag**, and leaves `<dir>` as it was

#### Scenario: Hidden character

- **WHEN** a vetted **Skill**'s `SKILL.md` holds U+E0041
- **THEN** `vet --into <dir>` exits 1 as `vet` does, and `<dir>` stays empty

#### Scenario: Empty value

- **WHEN** the user runs `skill-graft vet --into ""`
- **THEN** it exits 2 naming `--into`, and nothing is written
