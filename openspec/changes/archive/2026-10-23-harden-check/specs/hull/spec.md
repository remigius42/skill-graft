## MODIFIED Requirements

### Requirement: Every Markdown file

**References** SHALL be read from every file ending in `.md` (any case) in the **Skill**'s folder, at any depth, `.git`
excepted, once the **Skill**'s symlinks are checked and any file that is not a regular file, folder or symlink (a FIFO,
socket or device) is refused as an error naming it. A Markdown file that is not UTF-8 SHALL fail resolution, naming it,
as the `hidden-characters` capability says. One that cannot be read at all, a dangling link included, SHALL be an error
naming it. A **Reference** that resolves, **Binds** applied, to the referencing **Skill** SHALL give no edge, and is
still rewritten as the `renames` capability says.

#### Scenario: Reference in a sibling file

- **WHEN** `mp/tdd`'s `refs/loop.md` holds `/grilling`, and its `SKILL.md` does not
- **THEN** `mp/grilling` is in the **Hull**

#### Scenario: Not UTF-8

- **WHEN** a **Hull** **Skill**'s `notes.md` holds invalid UTF-8
- **THEN** the command exits non-zero naming `notes.md` as not UTF-8, and writes nothing

#### Scenario: Symlink to a device

- **WHEN** a **Skill** reached from an **Entry** holds `x.md` as a symlink to `/dev/zero`
- **THEN** the command exits non-zero naming `x.md` as pointing outside the **Skill**, without reading it

#### Scenario: Dangling link

- **WHEN** a **Hull** **Skill** holds `notes.md` as a symlink to a missing `gone.md` inside it
- **THEN** the command exits non-zero naming `notes.md`, without a traceback, and writes nothing

#### Scenario: Special file

- **WHEN** a **Hull** **Skill** holds a FIFO named `pipe`
- **THEN** `resolve` and `build` exit non-zero naming `pipe` as not a regular file, without reading it

#### Scenario: Self-reference

- **WHEN** `mp/tdd` holds `/tdd`, and no **Bind** names `mp/tdd`
- **THEN** the **Hull** gets no edge from `mp/tdd` to itself

#### Scenario: Bound self-reference

- **WHEN** `mp/tdd` holds `/tdd`, and `[bind]` has `"mp/tdd" = "own/tdd"`
- **THEN** `own/tdd` is pulled in, and the command exits non-zero as `mp/tdd` and `own/tdd` share a **Deployed name**
