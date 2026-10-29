## ADDED Requirements

### Requirement: SKILL.md is a regular file

A `SKILL.md` that is not a regular file once its symlinks are followed, such as a FIFO or a device, or a link to one,
SHALL NOT be read: its **Skill**'s name SHALL be unreadable, its error naming that `SKILL.md` by its full path. This
holds in every **Source**, path **Sources** included, and when the file is replaced by such a one while being read.

#### Scenario: SKILL.md linked to a device

- **WHEN** path source `own` holds `x/SKILL.md` as a symlink to `/dev/zero`, and `own/tdd`, another **Skill** of `own`,
  is the only **Entry**
- **THEN** `build` finishes and vendors `tdd`

#### Scenario: Entry names it

- **WHEN** path source `own` holds `x/SKILL.md` as a FIFO, and `own/x` is an **Entry**
- **THEN** the command exits non-zero naming `x/SKILL.md` as not a regular file, without blocking
