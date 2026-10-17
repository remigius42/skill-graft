# Spec Delta

## MODIFIED Requirements

### Requirement: Prose suggestions

`resolve` SHALL print, after the tree, each suggested **Skill** with the **Skills** mentioning it and how to accept it
(`skill-graft add <skill id>`, named in the header), sorted, on standard output. `build` and `update` SHALL NOT
print them, but when there are any SHALL print one line on standard error,
`skill-graft: <n> prose suggestion(s): run skill-graft resolve`; `update` counts those of the new tips.

#### Scenario: Suggestion printed

- **WHEN** `mp/tdd` mentions `diagnosing-bugs`, and `mp/diagnosing-bugs` is not in the **Hull**
- **THEN** `resolve` prints, after the tree, a header naming `skill-graft add`, then a line naming
  `mp/diagnosing-bugs` and `mp/tdd`

#### Scenario: No suggestions

- **WHEN** no prose **Reference** points outside the **Hull**
- **THEN** `resolve` prints the tree alone, and `build` prints no suggestion line

#### Scenario: Build announces suggestions

- **WHEN** `mp/tdd` mentions `diagnosing-bugs` and `notes`, neither in the **Hull**, and the user runs `build`
- **THEN** stderr holds `skill-graft: 2 prose suggestion(s): run skill-graft resolve`, and stdout no suggestion block

#### Scenario: Update announces suggestions

- **WHEN** at the new tip `mp/tdd` mentions `diagnosing-bugs`, not in the **Hull**, and the user runs `update`
  or `update --dry-run`
- **THEN** stderr holds `skill-graft: 1 prose suggestion(s): run skill-graft resolve`
