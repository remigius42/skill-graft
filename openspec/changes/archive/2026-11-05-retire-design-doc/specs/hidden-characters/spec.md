## MODIFIED Requirements

### Requirement: Hidden characters fail resolution

Resolution SHALL fail, exit 1, when a **Hull** **Skill** holds a **Hidden character** in a file's text or in a file or
folder name: a Unicode tag character (U+E0001 to U+E007F), a bidi embedding, override or isolate (U+202A to U+202E,
U+2066 to U+2069), or a supplementary variation selector (U+E0100 to U+E01EF). The error SHALL name each file, line,
code point and class. `skill-graft.toml` is the user's, not a **Skill**, and SHALL NOT be scanned.

#### Scenario: Tag characters in SKILL.md

- **WHEN** **Entry** `mp/tdd`'s `SKILL.md` holds U+E0041 on line 7
- **THEN** `skill-graft resolve` exits 1, naming that file, line 7, `U+E0041` and the tag character class

#### Scenario: Bidi override in a script

- **WHEN** a **Hull** **Skill**'s `scripts/run.sh` holds U+202E
- **THEN** `skill-graft resolve` exits 1, naming `scripts/run.sh`

#### Scenario: In a file name

- **WHEN** a **Hull** **Skill** holds a file whose name contains U+202E
- **THEN** `skill-graft resolve` exits 1, naming that path and `U+202E`

#### Scenario: Outside the hull

- **WHEN** a **Source** holds a **Skill** with U+E0041 that no **Hull** **Skill** reaches
- **THEN** `skill-graft resolve` succeeds

#### Scenario: In the config

- **WHEN** a comment in `skill-graft.toml` holds U+202E, and no **Hull** **Skill** holds a **Hidden character**
- **THEN** `skill-graft resolve` succeeds

### Requirement: One run reports every hidden character

A **Skill** holding a **Hidden character**, or a Markdown file that is not UTF-8, SHALL still have its other
**References** read, so the walk reaches every **Skill** it would, and one run SHALL report every **Hidden character**
and every such Markdown file of the **Hull**. Like a failing **Patch**, they SHALL be reported before another error that
stops the walk: the error SHALL list the failing **Patches** under `patches do not apply:`, then these under
`hidden characters:`, then that error. The warnings for unused `[rename]`, `[patches]` and `[bind]` keys SHALL be left
out.

#### Scenario: Two skills

- **WHEN** **Entry** `mp/tdd` holds U+E0041, and calls `/grilling`, which holds U+202E
- **THEN** one `skill-graft resolve` reports both

#### Scenario: With Markdown that is not UTF-8

- **WHEN** **Entry** `mp/tdd`'s `notes.md` is Latin-1, and `mp/tdd` calls `/grilling`, which holds U+202E
- **THEN** one `skill-graft resolve` reports both

#### Scenario: With a failing patch

- **WHEN** `mp/tdd`'s **Patch** fails and **Entry** `mp/notes` holds U+E0041
- **THEN** one `skill-graft resolve` reports both, the line `patches do not apply:` before the line `hidden characters:`
