## MODIFIED Requirements

### Requirement: Rename a skill

`rename <skill-id> <name>` SHALL set the **Skill**'s value in `[rename]`, replacing an existing value in place or
appending a key, and SHALL append a `[rename]` table at the end of the file when it is absent. `<name>` SHALL be a valid
**Skill** name. A `<name>` equal to the current **Deployed name** SHALL be a notice and change nothing.

#### Scenario: New rename

- **WHEN** there is no `[rename]` table and the user runs `skill-graft rename mp/code-review mp-code-review`
- **THEN** the file ends with a `[rename]` table holding `"mp/code-review" = "mp-code-review"`, and the tree shows
  `mp/code-review as mp-code-review`

#### Scenario: Already that name

- **WHEN** `mp/tdd` is renamed to `mp-tdd` and the user runs `skill-graft rename mp/tdd mp-tdd`
- **THEN** it exits 0 with a notice, and `skill-graft.toml` keeps its bytes

#### Scenario: Already the prefixed name

- **WHEN** `[sources.mp]` has `prefix = "mp-"`, no `[rename]` key names `mp/tdd`, and the user runs
  `skill-graft rename mp/tdd mp-tdd`
- **THEN** it exits 0 with a notice, and `skill-graft.toml` keeps its bytes

#### Scenario: Invalid name

- **WHEN** the user runs `skill-graft rename mp/tdd a/b`
- **THEN** it exits non-zero naming `a/b`, and `skill-graft.toml` is unchanged

### Requirement: Undo a rename

`rename <skill-id> <name>` with `<name>` equal to what the **Skill** deploys as without a `[rename]` key (its
**Source**'s `prefix` followed by its name, else its name) SHALL remove its `[rename]` key, leaving the table in place
even if empty. Any other `<name>`, the upstream name under a **Prefix** included, SHALL be written as a key.

#### Scenario: Undone

- **WHEN** **Entry** `mp/code-review` is renamed to `mp-code-review` and the user runs
  `skill-graft rename mp/code-review code-review`
- **THEN** `[rename]` no longer holds `mp/code-review`, and the shipped reserved-name warning for `code-review` is
  printed

#### Scenario: Opted out of the prefix

- **WHEN** `[sources.mp]` has `prefix = "mp-"`, no `[rename]` key names **Entry** `mp/tdd`, and the user runs
  `skill-graft rename mp/tdd tdd`
- **THEN** `[rename]` holds `"mp/tdd" = "tdd"`, and the tree shows `mp/tdd` without `as`

#### Scenario: Back to the prefix

- **WHEN** `[sources.mp]` has `prefix = "mp-"`, `[rename]` has `"mp/tdd" = "tdd"`, and the user runs
  `skill-graft rename mp/tdd mp-tdd`
- **THEN** `[rename]` no longer holds `mp/tdd`, and the tree shows `mp/tdd as mp-tdd`
