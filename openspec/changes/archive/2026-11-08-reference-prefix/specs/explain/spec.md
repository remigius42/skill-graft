## ADDED Requirements

### Requirement: Mermaid names the reference prefix

With a `reference-prefix`, `tree --format mermaid` SHALL open with Mermaid front matter titling the diagram
`reference-prefix: <value>`, before `flowchart TD`. Without one, it SHALL print no front matter.

#### Scenario: Mermaid titled with the reference prefix

- **WHEN** `reference-prefix = "foo:"`, `mp/tdd` calls `/grilling` and mentions `` `grilling` ``, `mp/grilling` is
  renamed to `mp-grilling`, and the user runs `skill-graft tree --format mermaid`
- **THEN** it prints `---`, `title: "reference-prefix: foo:"` and `---`, each on a line of its own, then the diagram it
  prints without the key

#### Scenario: No title without one

- **WHEN** the config has no `reference-prefix` and the user runs `skill-graft tree --format mermaid`
- **THEN** its first line is `flowchart TD`

## MODIFIED Requirements

### Requirement: Why accepts a Skill ID or a Deployed name

`<skill>` SHALL be read as a **Skill ID** when it contains `/`, else as a **Deployed name** of a **Hull** **Skill**,
compared exactly. With a `reference-prefix`, a `<skill>` without `/` that is no **Deployed name** as written and starts
with it SHALL be read without it, as the name a vendored **Reference** shows.

#### Scenario: Deployed name

- **WHEN** `mp/code-review` is renamed to `mp-code-review` and the user runs `skill-graft why mp-code-review`
- **THEN** it prints the tree for `mp/code-review`

#### Scenario: Unrenamed skill by name

- **WHEN** `mp/grilling` is in the **Hull**, not renamed, and the user runs `skill-graft why grilling`
- **THEN** it prints the tree for `mp/grilling`

#### Scenario: Reference-prefixed name

- **WHEN** `reference-prefix = "foo:"`, `mp/grilling` is in the **Hull**, not renamed, and the user runs
  `skill-graft why foo:grilling`
- **THEN** it prints the tree for `mp/grilling`, as `skill-graft why grilling` does

#### Scenario: Deployed name starting with the reference prefix

- **WHEN** `reference-prefix = "mp-"`, `[sources.mp]` has `prefix = "mp-"`, and the user runs `skill-graft why mp-tdd`
- **THEN** it prints the tree for `mp/tdd`, the **Skill** deployed as `mp-tdd`

#### Scenario: Prefixed upstream name of a renamed skill

- **WHEN** `reference-prefix = "foo:"`, `mp/code-review` is renamed to `mp-code-review`, and the user runs
  `skill-graft why foo:code-review`
- **THEN** it exits non-zero naming `mp/code-review` and `mp-code-review`, as `skill-graft why code-review` does

#### Scenario: No reference prefix

- **WHEN** the config has no `reference-prefix`, `mp/grilling` is in the **Hull**, and the user runs
  `skill-graft why foo:grilling`
- **THEN** it exits non-zero saying no skill in the **Hull** deploys as `foo:grilling`
