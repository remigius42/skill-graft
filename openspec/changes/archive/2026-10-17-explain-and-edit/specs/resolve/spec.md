# Spec Delta

## MODIFIED Requirements

### Requirement: Prose suggestions

`resolve` SHALL print, after the tree, each suggested **Skill** with the **Skills** mentioning it and how to accept it
(`skill-graft add <skill id>`, named in the header), sorted, on standard output. `build` SHALL NOT print suggestions.

#### Scenario: Suggestion printed

- **WHEN** `mp/tdd` mentions `diagnosing-bugs`, and `mp/diagnosing-bugs` is not in the **Hull**
- **THEN** `resolve` prints, after the tree, a header naming `skill-graft add`, then a line naming `mp/diagnosing-bugs`
  and `mp/tdd`

#### Scenario: No suggestions

- **WHEN** no prose **Reference** points outside the **Hull**
- **THEN** `resolve` prints the tree alone
