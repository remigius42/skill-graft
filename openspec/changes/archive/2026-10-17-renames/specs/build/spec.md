# Spec Delta

## MODIFIED Requirements

### Requirement: Vendor entries

`skill-graft build` SHALL make `~/.apm/skill-graft/.apm/skills/` hold exactly one folder per **Hull** **Skill**, named
after the **Skill**'s **Deployed name** and holding a copy of the **Skill**'s whole folder, renamed and rewritten as the
`renames` capability says and otherwise byte for byte. Nothing outside that folder is vendored. Folders from earlier
builds that are no longer in the **Hull** SHALL be removed. The folder SHALL be replaced only once every copy succeeded;
a failed copy SHALL leave it as it was.

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

- **WHEN** a previous build vendored `chisel`, and a **Hull** **Skill**'s folder holds a file the user cannot read
- **THEN** `build` exits non-zero naming the file, and `.apm/skills/` still holds the previous `chisel`

## REMOVED Requirements

### Requirement: Deployed names are unique

**Reason**: With **Renames**, a **Deployed name** is no longer the **Skill**'s name; uniqueness now holds after renames
and is checked by `resolve` too. **Migration**: Covered by the `renames` capability's "Deployed names are unique"
requirement; behavior without `[rename]` is unchanged.
