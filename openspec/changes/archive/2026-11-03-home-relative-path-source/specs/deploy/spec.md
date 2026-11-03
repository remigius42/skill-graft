## MODIFIED Requirements

### Requirement: Changed path Source deployed

When the only differences from the lock are the text of **Skills** of path **Sources** that have no **Patches** and the
paths path **Sources** are recorded at, `deploy` SHALL vendor and deploy them, write the new hashes and paths into
`skill-graft.lock`, and once it is written print a notice naming each such **Skill**. Any change to the **Hull**'s shape
SHALL be refused as "Deploy what the lock records" says, whatever **Source** caused it, and so SHALL a changed path
**Source** **Skill** with **Patches**.

#### Scenario: Own skill edited

- **WHEN** after `resolve` the user edits the text of `own/chisel`, in a path **Source**, and runs `deploy`
- **THEN** a notice names `own/chisel`, `.apm/skills/chisel/` holds the new text, the lock records its new hash, and
  `deploy` exits 0

#### Scenario: No notice when the lock write fails

- **WHEN** after `resolve` the user edits the text of `own/chisel`, and writing `skill-graft.lock` fails during `deploy`
- **THEN** `deploy` exits 1 naming the error, prints no notice naming `own/chisel`, and the lock and `.apm/skills/` are
  byte for byte as before

#### Scenario: Path source elsewhere on another machine

- **WHEN** in project scope `[sources.own]` has `path = "/opt/skills"`, the committed lock records another machine's
  folder for `own`, and the user runs `deploy`
- **THEN** `deploy` exits 0, and the lock records this machine's folder for `own`

#### Scenario: Home path source on another machine

- **WHEN** in project scope `[sources.own]` has `path = "~/skills"`, the committed lock was written by a user with
  another home folder, and the user runs `deploy` with the same skills in their `~/skills`
- **THEN** `deploy` exits 0, and the lock is byte for byte as committed

#### Scenario: Lock from before home paths

- **WHEN** in project scope `[sources.own]` has `path = "~/skills"`, the committed lock records `own` as an absolute
  folder, and the user runs `deploy`
- **THEN** `deploy` exits 0, and the lock records `own`'s path as `~/skills`

#### Scenario: Patched own skill

- **WHEN** after `resolve` the user edits a **Patch** of `own/chisel`, in a path **Source**, by hand and runs `deploy`
- **THEN** `deploy` exits 1 naming `own/chisel` and `skill-graft resolve`, and writes nothing

#### Scenario: Own skill reaches a new skill

- **WHEN** after `resolve` the user adds a call to `/grilling` to `own/chisel`, `mp/grilling` is not in the **Hull**,
  and the user runs `deploy`
- **THEN** `deploy` exits 1 naming `skill-graft resolve`, and writes nothing
