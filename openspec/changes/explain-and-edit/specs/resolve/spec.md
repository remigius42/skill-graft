# Spec Delta

## MODIFIED Requirements

### Requirement: Prose suggestions

`resolve` SHALL print, after the tree, each suggested **Skill** with the **Skills** mentioning it and how to
accept it (`skill-graft add <skill id>`), sorted, on standard output. `build` SHALL NOT print suggestions.

#### Scenario: Suggestion printed

- **WHEN** `mp/tdd` mentions `diagnosing-bugs`, and `mp/diagnosing-bugs` is not in the **Hull**
- **THEN** `resolve` prints, after the tree, a line naming `mp/diagnosing-bugs`, `mp/tdd`, and `skill-graft add`

#### Scenario: No suggestions

- **WHEN** no prose **Reference** points outside the **Hull**
- **THEN** `resolve` prints the tree alone
