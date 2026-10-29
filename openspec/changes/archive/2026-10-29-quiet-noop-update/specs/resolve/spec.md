## MODIFIED Requirements

### Requirement: Prose suggestions

`resolve` SHALL print, after the tree, each suggested **Skill** with the **Skills** mentioning it and how to accept it
(`skill-graft add <skill id>`, named in the header), sorted, on standard output. `build` and `update` SHALL NOT print
them, but when there are any SHALL print one line on standard error,
`skill-graft: <n> prose suggestion(s): run skill-graft resolve`; `update` counts those of the new tips, and after
`--dry-run`, whose tips `resolve` cannot see yet, prints
`skill-graft: <n> prose suggestion(s) at the new tips: update, then run skill-graft resolve` instead, unless it moves no
`ref`: `resolve` then sees the same tips, and the line is `update`'s. `build --into` SHALL print no such line: `resolve`
would rewrite the **Package**'s lock, and the lock in the `--into` folder lists the suggestions.

#### Scenario: Suggestion printed

- **WHEN** `mp/tdd` mentions `diagnosing-bugs`, and `mp/diagnosing-bugs` is not in the **Hull**
- **THEN** `resolve` prints, after the tree, a header naming `skill-graft add`, then a line naming `mp/diagnosing-bugs`
  and `mp/tdd`

#### Scenario: No suggestions

- **WHEN** no prose **Reference** points outside the **Hull**
- **THEN** `resolve` prints the tree alone, and `build` prints no suggestion line

#### Scenario: Build announces suggestions

- **WHEN** `mp` has `diagnosing-bugs` and `notes`, **Entry** `mp/tdd` mentions `diagnosing-bugs` and `` `notes` `` but
  calls neither, and the user runs `build`
- **THEN** stderr holds `skill-graft: 2 prose suggestion(s): run skill-graft resolve`, and stdout no suggestion block

#### Scenario: Build into a folder announces none

- **WHEN** **Entry** `mp/tdd` mentions `diagnosing-bugs`, not in the **Hull**, and the user runs `build --into <dir>`
- **THEN** stderr holds no `prose suggestion(s)` line, and `<dir>/skill-graft.lock` lists `mp/diagnosing-bugs`

#### Scenario: Update announces suggestions

- **WHEN** at the new tip `mp/tdd` mentions `diagnosing-bugs`, not in the **Hull**, and the user runs `update`
- **THEN** stderr holds `skill-graft: 1 prose suggestion(s): run skill-graft resolve`

#### Scenario: Dry run announces suggestions

- **WHEN** the same, with `update --dry-run`
- **THEN** stderr holds `skill-graft: 1 prose suggestion(s) at the new tips: update, then run skill-graft resolve`

#### Scenario: Dry run moving no ref announces suggestions

- **WHEN** `mp/tdd` mentions `diagnosing-bugs`, not in the **Hull**, `mp`'s tip is its `ref`, and the user runs
  `update --dry-run`
- **THEN** stderr holds `skill-graft: 1 prose suggestion(s): run skill-graft resolve`
