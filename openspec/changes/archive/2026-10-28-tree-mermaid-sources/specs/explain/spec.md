# Spec Delta

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

## ADDED Requirements

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
