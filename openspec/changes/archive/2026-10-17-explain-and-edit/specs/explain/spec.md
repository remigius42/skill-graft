# Spec Delta

## Purpose

`skill-graft why` and `skill-graft tree` show the user why a **Skill** is in the **Hull** and what the whole **Hull**
looks like, as text or as a Mermaid diagram, without changing anything.

## ADDED Requirements

### Requirement: Explaining writes nothing

`why` and `tree` SHALL compute the **Hull** from `skill-graft.toml` as `resolve` does, reading each git **Source** at
its `ref` and fetching only a commit missing from the cache, with the same warnings on standard error and the same
errors. They SHALL NOT read or write `skill-graft.lock`, write `skill-graft.toml` or `.apm/skills/`, or run `apm`.

#### Scenario: No lock

- **WHEN** `skill-graft.lock` does not exist and the user runs `skill-graft tree`
- **THEN** it prints the tree, exits 0, and `skill-graft.lock` still does not exist

#### Scenario: Stale lock

- **WHEN** the lock was written before `own/b` was added to `entries`, and the user runs `skill-graft why own/b`
- **THEN** it reports `own/b` as an **Entry**, and the lock's bytes are unchanged

#### Scenario: Failing patch

- **WHEN** a **Patch** of a **Hull** **Skill** fails to apply
- **THEN** `why` and `tree` exit non-zero naming the failing hunk, as `resolve` does

### Requirement: Why prints an inverted tree

`why <skill>` SHALL print the **Skill** on the first line, then, as a tree whose lines join with `├─←` and `└─←`, each
**Skill** with a slash or Skill tool **Reference** resolved to it, labelled as in `resolve`'s tree. Children SHALL be in
the order the walk reached them, which is the **Hull**'s order. A **Skill** SHALL be expanded once; its later lines end
in `(*)`. An **Entry** below the first line SHALL be marked `(entry)` and not expanded; the first line SHALL be
expanded, and marked `(entry)` when the **Skill** is an **Entry**. Prose edges and self-references SHALL be left out.

#### Scenario: Two paths

- **WHEN** **Entry** `mp/tdd` calls `/grilling` and `/implement`, `mp/implement` calls `Skill(grilling)`, and the user
  runs `skill-graft why mp/grilling`

- **THEN** it prints

  ```text
  mp/grilling
  ├─← mp/tdd (/grilling) (entry)
  └─← mp/implement (Skill(grilling))
      └─← mp/tdd (/implement) (entry)
  ```

#### Scenario: Repeated skill

- **WHEN** **Entries** `mp/a` and `mp/b` both call `/mid`, `mp/mid` calls `/x` and `/y`, both of which call `/leaf`, and
  the user runs `skill-graft why mp/leaf`

- **THEN** `mp/mid` is expanded under the first of `mp/x` and `mp/y` and its line under the other ends in `(*)`

#### Scenario: An entry asked about

- **WHEN** `mp/tdd` is an **Entry** that `mp/grilling` also calls, and the user runs `skill-graft why mp/tdd`
- **THEN** the first line is `mp/tdd (entry)`, followed by the path through `mp/grilling`

#### Scenario: Renamed, patched and bound

- **WHEN** **Entry** `mp/tdd` is renamed to `mp-tdd` and patched, and calls `/notes`, bound to `own/notes`
- **THEN** `skill-graft why own/notes` prints `└─← mp/tdd as mp-tdd (patched) (/notes, bind) (entry)` under `own/notes`

#### Scenario: Prose not shown

- **WHEN** `mp/tdd` calls `/grilling` and also mentions `` `grilling` `` in prose
- **THEN** `skill-graft why mp/grilling` prints one line for `mp/tdd`, labelled `/grilling`

### Requirement: Why accepts a Skill ID or a Deployed name

`<skill>` SHALL be read as a **Skill ID** when it contains `/`, else as a **Deployed name** of a **Hull** **Skill**,
compared exactly.

#### Scenario: Deployed name

- **WHEN** `mp/code-review` is renamed to `mp-code-review` and the user runs `skill-graft why mp-code-review`
- **THEN** it prints the tree for `mp/code-review`

#### Scenario: Unrenamed skill by name

- **WHEN** `mp/grilling` is in the **Hull**, not renamed, and the user runs `skill-graft why grilling`
- **THEN** it prints the tree for `mp/grilling`

### Requirement: Why explains a skill it cannot show

`why` SHALL exit non-zero, printing nothing on standard output, when `<skill>` names no **Hull** **Skill**. The error
SHALL say why and what to do instead. A bare name that is the name of a **Skill** prose suggests SHALL get that
**Skill**'s error, as if its **Skill ID** were given.

#### Scenario: Upstream name of a renamed skill

- **WHEN** `mp/code-review` is renamed to `mp-code-review` and the user runs `skill-graft why code-review`
- **THEN** it exits non-zero naming `mp/code-review` and `mp-code-review`

#### Scenario: Outside the hull, mentioned in prose

- **WHEN** `mp/tdd` mentions `diagnosing-bugs`, `mp/diagnosing-bugs` is not in the **Hull**, and the user runs
  `skill-graft why mp/diagnosing-bugs`
- **THEN** it exits non-zero saying it is not in the **Hull**, naming `mp/tdd` and `skill-graft add mp/diagnosing-bugs`

#### Scenario: Outside the hull, not mentioned

- **WHEN** `mp/notes` exists in **Source** `mp` but is not in the **Hull** and no prose mentions it
- **THEN** `skill-graft why mp/notes` exits non-zero saying it is not in the **Hull**, naming `skill-graft add mp/notes`

#### Scenario: Bare name outside the hull, mentioned in prose

- **WHEN** `mp/tdd` mentions `diagnosing-bugs`, `mp/diagnosing-bugs` is not in the **Hull**, and the user runs
  `skill-graft why diagnosing-bugs`
- **THEN** it exits non-zero as for `skill-graft why mp/diagnosing-bugs`

#### Scenario: Unknown

- **WHEN** the user runs `skill-graft why mp/nope` and **Source** `mp` has no **Skill** `nope`, or
  `skill-graft why nope` and no **Hull** **Skill** deploys as `nope` and no prose mentions `nope`
- **THEN** it exits non-zero naming `nope`

#### Scenario: Undeclared alias

- **WHEN** the user runs `skill-graft why zz/tdd` and no **Source** `zz` is declared
- **THEN** it exits non-zero naming the alias `zz`

### Requirement: Tree prints resolve's tree

`tree`, and `tree --format text`, SHALL print exactly the tree `resolve` prints for the same config, without the prose
suggestions.

#### Scenario: Same tree

- **WHEN** the user runs `skill-graft resolve` and `skill-graft tree` on the same config, with prose suggestions
- **THEN** `tree`'s output equals `resolve`'s up to the line before the suggestions

### Requirement: Tree as Mermaid

`tree --format mermaid` SHALL print a Mermaid `flowchart TD`, without a code fence: one node per **Hull** **Skill**
labelled as on its tree line (`as <deployed name>`, `(patched)`), the **Entries** in a class `entry` drawn with a
thicker border, and one arrow per pair of **Skills**, kind and **Bind** that has a tree line, labelled with the
**Reference** as written (`, bind` when a **Bind** decided it). Prose arrows SHALL be dotted. The output SHALL be
deterministic. Every label SHALL stand in double quotes, so parentheses do not break the diagram, and each backtick in
it SHALL be written `#96;`, so Mermaid does not read it as a Markdown string.

#### Scenario: Diagram

- **WHEN** **Entry** `mp/tdd` calls `/grilling`, renamed to `mp-grilling`, and mentions `` `grilling` ``

- **THEN** `skill-graft tree --format mermaid` prints

  ```text
  flowchart TD
    n0["mp/tdd"]:::entry
    n1["mp/grilling as mp-grilling"]
    n0 -->|"/grilling"| n1
    n0 -.->|"#96;grilling#96;, prose"| n1
    classDef entry stroke-width:3px
  ```

#### Scenario: Labels quoted

- **WHEN** a **Reference** is written `Skill(grilling)` or `` `grilling` ``
- **THEN** every node and arrow label in the diagram stands in double quotes, and no label holds a backtick

#### Scenario: No source links

- **WHEN** the **Hull** has **Skills** from git and path **Sources**
- **THEN** the diagram holds no `click` line and no URL

### Requirement: Tree as a mermaid.live link

`tree --format mermaid --link` SHALL print one line: a `https://mermaid.live/edit#pako:` URL whose fragment encodes the
diagram `--format mermaid` prints, in the form mermaid.live reads. skill-graft SHALL make no network call for it and
open no browser. `--link` without `--format mermaid` SHALL be a usage error.

#### Scenario: Link decodes to the diagram

- **WHEN** the user runs `skill-graft tree --format mermaid --link`
- **THEN** it prints one URL, and decoding its fragment (url-safe base64, then zlib, then JSON) gives a state whose
  `code` equals the output of `skill-graft tree --format mermaid`

#### Scenario: Link without Mermaid

- **WHEN** the user runs `skill-graft tree --link`
- **THEN** it exits 2 naming `--link` and `--format mermaid`
