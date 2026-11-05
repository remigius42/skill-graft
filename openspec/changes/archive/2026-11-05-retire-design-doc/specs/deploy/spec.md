## MODIFIED Requirements

### Requirement: Deploy what the lock records

`deploy` SHALL deploy the **Hull** `skill-graft.lock` records: it SHALL resolve the **Hull** as `resolve` does, only to
check it against the lock, and deploy only if the two are the same, but for path **Source** text and folders as "Changed
path Source deployed" says. The lock SHALL be compared parsed, so a comment or line endings an editor added to it are no
difference. Otherwise, and when the lock is missing, cannot be read or is of another `version`, `deploy` SHALL exit 1
writing nothing and running no `apm`, naming each **Skill** that differs, or what else does, and `skill-graft resolve`
to accept the change.

#### Scenario: Nothing changed

- **WHEN** the user runs `resolve`, then `deploy`
- **THEN** `deploy` exits 0, and `skill-graft.lock` keeps its bytes

#### Scenario: Lock reformatted by an editor

- **WHEN** after `resolve` the user adds a comment line to `skill-graft.lock` and converts its line endings to CRLF,
  then runs `deploy`
- **THEN** `deploy` exits 0, and `skill-graft.lock` is rewritten as skill-graft writes it: the comment gone, its line
  endings LF

#### Scenario: Config edited by hand

- **WHEN** after `resolve` the user adds `mp/notes` to `entries` by hand and runs `deploy`
- **THEN** `deploy` exits 1 saying the **Hull** differs from `skill-graft.lock` and naming `skill-graft resolve`,
  `.apm/skills/`, the lock and APM are untouched, and no `.apm/skills.new/` is left

#### Scenario: Patch edited by hand

- **WHEN** after `resolve` the user edits a **Patch** of `mp/tdd` and runs `deploy`
- **THEN** `deploy` exits 1 naming `mp/tdd` as differing from `skill-graft.lock`, and naming `skill-graft resolve`

#### Scenario: Cache export edited

- **WHEN** after `resolve` a file of `mp/tdd`'s **Upstream** folder in the cache is edited and the user runs `deploy`
- **THEN** `deploy` exits 1 naming `mp/tdd`

#### Scenario: Accepted with resolve

- **WHEN** `deploy` refused a hand edit to the config, and the user runs `resolve`, then `deploy`
- **THEN** `deploy` exits 0 and deploys the edited config's **Hull**

#### Scenario: No lock

- **WHEN** the **Package** has no `skill-graft.lock`, as after `init`, and the user runs `deploy`
- **THEN** `deploy` exits 1 naming `skill-graft resolve`, and writes nothing

#### Scenario: Lock of another version

- **WHEN** `skill-graft.lock` records `version = 2` and the user runs `deploy`
- **THEN** `deploy` exits 1 naming `skill-graft resolve`, and writes nothing

#### Scenario: Vendoring fails

- **WHEN** after `resolve` a path **Source**'s **Skill** changed, and a copy fails during `deploy`
- **THEN** `deploy` exits non-zero naming the file, and `skill-graft.lock` and `.apm/skills/` are byte for byte as
  before

### Requirement: Changed path Source deployed

When the only differences from the lock are the text of **Skills** of path **Sources** that have no **Patches** and the
paths path **Sources** are recorded at, `deploy` SHALL vendor and deploy them, write the new hashes and paths into
`skill-graft.lock`, and once it is written print a notice per such **Skill**,
`<skill id> changed in its path source since skill-graft.lock: deployed as is`. Any change to the **Hull**'s shape SHALL
be refused as "Deploy what the lock records" says, whatever **Source** caused it, and so SHALL a changed path **Source**
**Skill** with **Patches**.

#### Scenario: Own skill edited

- **WHEN** after `resolve` the user edits the text of `own/chisel`, in a path **Source**, and runs `deploy`
- **THEN** stderr holds `own/chisel changed in its path source since skill-graft.lock: deployed as is`,
  `.apm/skills/chisel/` holds the new text, the lock records its new hash, and `deploy` exits 0

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
