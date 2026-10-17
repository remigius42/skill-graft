# Spec Delta

## ADDED Requirements

### Requirement: Why names the upstream folder

After the tree, `why <skill>` SHALL print `upstream: <absolute folder>`: the folder the **Skill**'s **Patches**
apply to, in the cache export at the `ref` or in a path **Source**, as resolved for this run. It is the base a
new **Patch** is written against.

#### Scenario: Path source

- **WHEN** `own/chisel` is at `~/src/chisel` and the user runs `skill-graft why own/chisel`
- **THEN** the last line is `upstream: <home>/src/chisel`

#### Scenario: Git source

- **WHEN** `mp/tdd` is at `skills/tdd` in git **Source** `mp` and the user runs `skill-graft why mp/tdd`
- **THEN** the last line starts with `upstream:` and names an absolute folder holding `mp/tdd`'s upstream
  `SKILL.md`
