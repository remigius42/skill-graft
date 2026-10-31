## MODIFIED Requirements

### Requirement: Entries

`entries` SHALL be a list of **Skill IDs** of the form `<alias>/<name>`. An empty or absent list is valid and vendors no
skills.

#### Scenario: Entry with an undeclared alias

- **WHEN** `entries = ["mp/tdd"]` and no `[sources.mp]` exists
- **THEN** the command exits non-zero naming `mp/tdd` and the alias `mp`

#### Scenario: Malformed entry

- **WHEN** an entry has no `/`, or an empty alias or name
- **THEN** the command exits non-zero naming the entry

#### Scenario: Repeated entry

- **WHEN** `entries = ["own/a", "own/a"]`
- **THEN** the command exits non-zero naming `own/a` as repeated
