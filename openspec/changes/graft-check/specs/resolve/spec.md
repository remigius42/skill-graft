## ADDED Requirements

### Requirement: Lock layout version

The lock SHALL hold `version = 1` for this layout: top-level `version`, `sources`, `skills`, `edges` and `suggestions`;
a **Source** with `git`, `ref` and, when set, `subdirectory`, or `path`; a **Skill** with `id`, `entry`, `upstream`,
`hash`, and when they apply `deployed` and `patches`; an edge with `from`, `to`, `kind`, and `bind` when true; a
suggestion with `id` and `from`. Any change to these keys or their meaning SHALL raise `version`.

#### Scenario: Version 1 keys

- **WHEN** `resolve` writes a lock whose **Hull** has a renamed, patched **Skill** from a git **Source** with a
  `subdirectory`, a bound edge and a suggestion
- **THEN** the lock has `version = 1` and exactly the keys above
