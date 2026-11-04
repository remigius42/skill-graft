## MODIFIED Requirements

### Requirement: Tree as Mermaid

`tree --format mermaid` SHALL print a Mermaid `flowchart TD`, without a code fence: one subgraph per **Source** that has
a **Hull** **Skill**, holding one node per such **Skill** labelled as on its tree line (`as <deployed name>`,
`(patched)`), the **Entries** in a class `entry` drawn amber with a thicker border, and one arrow per pair of
**Skills**, kind and **Bind** that has a tree line, labelled with the **Reference** as written (`, bind` when a **Bind**
decided it). Prose arrows SHALL be dotted. The output SHALL be deterministic. Every label SHALL stand in double quotes,
so parentheses do not break the diagram, and each backtick in it SHALL be written `#96;`, so Mermaid does not read it as
a Markdown string.

#### Scenario: Diagram

- **WHEN** **Entry** `mp/tdd` from path **Source** `mp` calls `/grilling`, renamed to `mp-grilling`, and mentions
  `` `grilling` ``

- **THEN** `skill-graft tree --format mermaid` prints

  ```text
  flowchart TD
    subgraph s0["mp"]
      n0["mp/tdd"]:::entry
      n1["mp/grilling as mp-grilling"]
    end
    n0 -->|"/grilling"| n1
    n0 -.->|"#96;grilling#96;, prose"| n1
    classDef entry fill:#fde68a,stroke:#b45309,stroke-width:3px,color:#451a03
  ```

#### Scenario: Labels quoted

- **WHEN** a **Reference** is written `Skill(grilling)` or `` `grilling` ``
- **THEN** every node and arrow label in the diagram stands in double quotes, and no label holds a backtick

#### Scenario: No source links

- **WHEN** `[sources.own]` has `path = "~/own"` and `[sources.mp]` has
  `git = "https://user:secret@example.com/mp.git?private_token=t0k3n"`
- **THEN** their subgraphs are titled `"own"` and `"mp"`, and the diagram holds no `<a`, no `click` line, no `://`, and
  none of `user`, `secret`, `example.com` or `t0k3n`

#### Scenario: Subgraphs in hull order

- **WHEN** the **Hull** reaches `a/x`, then `b/y`, then `a/z`
- **THEN** subgraph `s0` is **Source** `a` holding `a/x` and `a/z` in that order, subgraph `s1` is `b`, and every arrow
  follows the last subgraph

### Requirement: Tree as a mermaid.live link

`tree --format mermaid --link` SHALL print one line: a `https://mermaid.live/edit#pako:` URL whose fragment encodes the
diagram `--format mermaid` prints, in the form mermaid.live reads: a JSON state holding the diagram as `code` and
`"mermaid": "{\"theme\": \"default\"}"`, zlib-deflated, in url-safe base64 without padding. skill-graft SHALL make no
network call for it and open no browser. `--link` without `--format mermaid` SHALL be a usage error.

#### Scenario: Link decodes to the diagram

- **WHEN** the user runs `skill-graft tree --format mermaid --link`
- **THEN** it prints one URL, and decoding its fragment (url-safe base64, then zlib, then JSON) gives a state whose
  `code` equals the output of `skill-graft tree --format mermaid`, whose `mermaid` is `{"theme": "default"}` as JSON,
  and the fragment holds no `=`

#### Scenario: Link without Mermaid

- **WHEN** the user runs `skill-graft tree --link`
- **THEN** it exits 2 naming `--link` and `--format mermaid`
