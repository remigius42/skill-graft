# Spec Delta

## ADDED Requirements

### Requirement: Resolve dry run and diff

`resolve --dry-run` and `resolve --diff <file>` SHALL behave as the editing commands' `--dry-run` and `--diff` do, the
**Hull diff** that of the **Vendored copies** against the **Hull** of `skill-graft.toml` as it stands, and the hint
`review: skill-graft resolve --dry-run --diff <file>`. Its dry run SHALL say
`dry run: skill-graft.lock and .apm/skills/ not written`. Its file's header's second line SHALL say it compares the
**Vendored copies** against what `skill-graft.toml` as it stands would vendor.

#### Scenario: A ref moved by hand

- **WHEN** the user set `sources.mp.ref` to B by hand, the lock records A, `mp/tdd` changed between them, and the user
  runs `resolve --dry-run --diff review.diff`
- **THEN** `mp/tdd`'s source line in `review.diff` names `mp`, A and B

#### Scenario: A patch written by hand

- **WHEN** the user added a **Patch** of `mp/tdd` to `[patches]` by hand and runs `resolve --dry-run --diff review.diff`
- **THEN** it prints `~ mp/tdd` naming each file the **Patch** changes, `review.diff` holds that text as deployed, and
  `skill-graft.lock` and `.apm/skills/` are unchanged

#### Scenario: Nothing changed

- **WHEN** nothing changed since the lock was written and the user runs `resolve --dry-run`
- **THEN** it prints `hull unchanged`, then its `dry run:` line, and no `review:` line
