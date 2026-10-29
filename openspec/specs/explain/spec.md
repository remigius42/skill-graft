# explain Specification

## Purpose

`skill-graft why` and `skill-graft tree` show the user why a **Skill** is in the **Hull** and what the whole **Hull**
looks like, as text or as a Mermaid diagram, without changing anything.

## Requirements

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
diagram `--format mermaid` prints, in the form mermaid.live reads. skill-graft SHALL make no network call for it and
open no browser. `--link` without `--format mermaid` SHALL be a usage error.

#### Scenario: Link decodes to the diagram

- **WHEN** the user runs `skill-graft tree --format mermaid --link`
- **THEN** it prints one URL, and decoding its fragment (url-safe base64, then zlib, then JSON) gives a state whose
  `code` equals the output of `skill-graft tree --format mermaid`

#### Scenario: Link without Mermaid

- **WHEN** the user runs `skill-graft tree --link`
- **THEN** it exits 2 naming `--link` and `--format mermaid`

### Requirement: Recognized forge repositories

A git **Source** URL SHALL name a GitHub or GitLab repository when, as an `https`, `http`, `ssh` or `git` URL or as
`[user@]host:path`, it holds no `?`, `#`, whitespace or control character, its host is `github.com` or `gitlab.com` in
any case, and its path is name segments (a letter or digit, then letters, digits, `.`, `_` or `-`), two on GitHub and
two or more on GitLab, the last optionally ending in `.git`, then optionally one `/`. Its repository URL SHALL be
`https://<host>/<segments>`, without `.git`, built only from those parts. No other URL names a repository.

#### Scenario: Repository URLs

- **WHEN** a git **Source** URL is one of `https://github.com/o/r.git`, `https://github.com/o/r/`,
  `http://GitHub.com/o/r`, `git://github.com/o/r.git`, `ssh://git@github.com/o/r.git`,
  `ssh://git@github.com:22/o/r.git`, `git@github.com:o/r.git`, `github.com:o/r`,
  `https://user:secret@github.com/o/r.git`, `git@gitlab.com:g/sub/r.git`, `https://oauth2:secret@gitlab.com/g/r`
- **THEN** its repository URL is `https://github.com/o/r`, or for the GitLab ones `https://gitlab.com/g/sub/r` and
  `https://gitlab.com/g/r`

#### Scenario: Not a repository

- **WHEN** a git **Source** URL is one of `https://github.com@evil.example/o/r`, `https://evil.example/github.com/o/r`,
  `https://github.com.evil.example/o/r`, `https://www.github.com/o/r`, `https://github.com/o`,
  `https://github.com/o/r/x`, `https://gitlab.com/g`, `https://github.com/o/r?private_token=t`,
  `https://github.com/o/r#x`, `https://github.com/o/%72`, `https://github.com/o/../r`, `https://github.com//o/r`,
  `https://github.com/o/r.git/x`, `git@github.com:~o/r`, `file:///srv/github.com/o/r`, `/srv/github.com/o/r`,
  `user:tok@github.com:o/r` (host `user`), `https://git<tab>hub.com/o/r` with a tab character
- **THEN** it names no repository

### Requirement: Mermaid links to GitHub and GitLab

In `tree --format mermaid`, the subgraph of a **Source** whose URL names a GitHub or GitLab repository SHALL be titled
`alias · <repository URL without https://>`, wrapped in `<a href='<tree>' target='_blank' rel='noopener'>`, `<tree>`
being the repository URL, then `/tree/<Ref>` on GitHub or `/-/tree/<Ref>` on GitLab, then `/<subdirectory>` if it has
one, unless git's configuration rewrites the URL (`url.<base>.insteadOf`) or skill-graft's cache holds no repository git
can read for it. Each of its **Skills** SHALL get its label wrapped the same way, linking to its folder relative to the
repository root once symbolic links are resolved; a folder resolving outside the repository, which discovery of a git
**Source** never yields, SHALL get no link. Path segments SHALL be percent-encoded. No `click` line SHALL be printed.

#### Scenario: GitHub Source

- **WHEN** `[sources.mp]` has `git = "https://user:secret@github.com/o/mp.git"`, `subdirectory = "skills"` and
  `ref = "<sha>"`, and **Entry** `mp/tdd` is the folder `skills/tdd`

- **THEN** the diagram holds the lines below, and neither `user:` nor `secret`

  ```text
  subgraph s0["<a href='https://github.com/o/mp/tree/<sha>/skills' target='_blank' rel='noopener'>mp · github.com/o/mp</a>"]
  n0["<a href='https://github.com/o/mp/tree/<sha>/skills/tdd' target='_blank' rel='noopener'>mp/tdd</a>"]:::entry
  ```

#### Scenario: GitLab Source without subdirectory

- **WHEN** `[sources.mp]` has `git = "git@gitlab.com:g/sub/mp.git"` and `ref = "<sha>"`, and **Entry** `mp/tdd` is the
  folder `tdd`
- **THEN** the subgraph links to `https://gitlab.com/g/sub/mp/-/tree/<sha>` and is titled `mp · gitlab.com/g/sub/mp`,
  and `mp/tdd` links to `https://gitlab.com/g/sub/mp/-/tree/<sha>/tdd`

#### Scenario: Folder names encoded

- **WHEN** a GitHub **Source** has `subdirectory = "c#/my skills"` holding **Skill** folder `a?b`
- **THEN** the subgraph links to `…/tree/<sha>/c%23/my%20skills` and the **Skill** to
  `…/tree/<sha>/c%23/my%20skills/a%3Fb`

#### Scenario: Rewritten URL

- **WHEN** git's configuration has `url.<other>.insteadOf = https://github.com/` and `[sources.mp]` has
  `git = "https://github.com/o/mp.git"`
- **THEN** the subgraph is titled `"mp"`, and the diagram holds no `<a` and no `github.com`

#### Scenario: Unreadable cache repository

- **WHEN** `[sources.mp]` has `git = "https://github.com/o/mp.git"` and git cannot read its repository in skill-graft's
  cache
- **THEN** `tree --format mermaid` still prints the diagram, then the **Hull**'s warnings; the subgraph is titled
  `"mp"`, and the diagram holds no `<a`

#### Scenario: Skill folder through a symbolic link

- **WHEN** a GitHub **Source**'s folder `skills` is a symbolic link to `src/skills`, holding **Skill** folder `tdd`
- **THEN** the **Skill** links to `…/tree/<sha>/src/skills/tdd`

### Requirement: Why names the upstream folder

After the tree, `why <skill>` SHALL print `upstream: <absolute folder>`: the folder the **Skill**'s **Patches** apply
to, in the cache export at the `ref` or in a path **Source**, as resolved for this run. It is the base a new **Patch**
is written against.

#### Scenario: Path source

- **WHEN** `own/chisel` is at `~/src/chisel` and the user runs `skill-graft why own/chisel`
- **THEN** the last line is `upstream: <home>/src/chisel`

#### Scenario: Git source

- **WHEN** `mp/tdd` is at `skills/tdd` in git **Source** `mp` and the user runs `skill-graft why mp/tdd`
- **THEN** the last line starts with `upstream:` and names an absolute folder holding `mp/tdd`'s upstream `SKILL.md`
