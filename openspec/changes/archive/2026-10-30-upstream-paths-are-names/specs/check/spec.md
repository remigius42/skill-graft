## ADDED Requirements

### Requirement: The lock is checked before use

The skill SHALL check the lock before reading it, by one command that exits 0 and prints the lock's `version` and a
count only: of the lines that are not blank, skill-graft's header comment, `version`, an empty table as tomlkit writes
it (`edges = []`), a `[sources]` header, under `[sources.<name>]` (the name quoted when it holds a dot), or one of the
forms skill-graft writes in its `[[skills]]`, `[[edges]]` and `[[suggestions]]` tables; any other header counts. Each
`id`, `from` and `to` SHALL be `<alias>/<name>`, each `deployed` a name, matching `[A-Za-z0-9][A-Za-z0-9._-]*`, and each
`upstream` `.` or `/`-separated segments matching `[A-Za-z0-9._-]+`, not only dots. A `version` other than 1 SHALL take
the "Lock version" path; otherwise a count above 0 SHALL end the **Check** before the skill reads the lock or runs any
reader, naming no value.

#### Scenario: Crafted upstream

- **WHEN** the lock written by an older skill-graft has `upstream = "skills/$(curl x)/tdd"`
- **THEN** the **Check** ends, runs no reader and no command holding that value, and shows the user no part of it

#### Scenario: Line in another form

- **WHEN** a `[[skills]]` item of the lock holds `upstream="x"` or `"upstream" = "x"`
- **THEN** the count is above 0 and the **Check** ends

#### Scenario: Header in another form

- **WHEN** the lock holds `[[skills]] # x` or `[skills.x]`, then `upstream = "$(x)"`
- **THEN** the count is above 0 and the **Check** ends

#### Scenario: Newer lock version

- **WHEN** the lock has `version = 2` and keys this skill does not know
- **THEN** the skill gives the "Lock version" advice, not the bad-lock one

#### Scenario: Hidden folder

- **WHEN** every item of the lock is well formed, one with `upstream = ".claude/skills/tdd"`
- **THEN** the **Check** goes on

#### Scenario: No edges and no suggestions

- **WHEN** the lock's hull has no edges and no suggestions, so the lock holds `edges = []` and `suggestions = []`
- **THEN** the count is 0 and the **Check** goes on

#### Scenario: Alias holding a dot

- **WHEN** the config has `[sources."my.src"]`, so the lock holds that header
- **THEN** the count is 0 and the **Check** goes on

#### Scenario: No sources

- **WHEN** the config has no sources, so the lock holds a bare `[sources]` header
- **THEN** the count is 0

#### Scenario: Skill at a source's root

- **WHEN** every item of the lock is well formed, one with `upstream = "."` in a git **Source**
- **THEN** the **Check** goes on, and takes that **Source**'s root as the whole of `why`'s `upstream:` line
