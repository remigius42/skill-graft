# Design

## Context

`explain.mermaid(hull)` prints nodes `n0…` in hull order, then the arrows of `_shown_edges`, then the `entry`
class. It sees only the **Hull**, which has each **Skill**'s upstream folder (`hull.upstream`) and each **Source**'s
root (`hull.roots`: a git **Source**'s whole tree, even when only a `subdirectory` is walked), but not the
**Sources**' URLs and **Refs**. `cli.py`'s `tree` callback already receives the `Config`. `tree` always reads a git
**Source** at a **Ref**: `compute.check_refs` refuses one without. See proposal.md for why.

`config.py` accepts a git URL as an `https`, `http`, `ssh`, `git` or `file` URL, as `[user@]host:path` (`SCP`), or
as an absolute path. A path **Source** keeps only its resolved folder, not the path as written.

Manual check in mermaid.live (v12.2.0, theme `default`, its default `securityLevel`): an
`<a href='…' target='_blank' rel='noopener'>` in a subgraph title renders and opens a new tab;
`click n href "…" _blank` navigates the same tab. Default nodes are white with a black border, subgraphs pink.

## Goals / Non-Goals

**Goals:**

- No secret from `skill-graft.toml` or git's configuration can reach the diagram, and so the `--link` URL,
  whatever the user wrote.

**Non-Goals:**

- Self-hosted GitHub or GitLab, Gitea, Bitbucket, Codeberg and others: alias only, see the first decision.
- Showing where a path **Source** or a local git path lives: a local path tells a reader the user's name and
  folder layout, and a path **Source** keeps no path as written to show.
- Shortening node labels inside a subgraph: they keep the **Skill ID**, so labels match `tree`'s lines.

## Decisions

- **Only `github.com` and `gitlab.com`, because only there is every shown part known to hold no secret.** A git
  URL can carry a credential in three places: the user info (`user:token@`), the query or fragment
  (`?private_token=…`), and the path (some proxies and mirrors put a token in a path segment). The first two have
  fixed places and could be stripped; a token in the path cannot be told from a folder name. On `github.com` and
  `gitlab.com` the path is `owner/repo` (GitLab: `group/…/repo`), names the forge resolves; a token there would
  not fetch, and `tree` cannot draw a **Source** it cannot fetch. That holds only if git fetches from the host the
  URL names: a `url.<base>.insteadOf` rule can send `https://github.com/<token>/repo` to a proxy that takes the
  token, so a URL git rewrites gets no link (see "Ask git"). Both also have a known tree URL
  (`/tree/<Ref>/…`, GitLab `/-/tree/<Ref>/…`), so a link cannot 404 for want of the forge's URL scheme. Any other
  host, a self-hosted instance included, gets the alias only. Rejected alternative: show every URL with
  credentials stripped. It leaks a token in a path, and its links 404 on forges with another URL scheme.
- **Rebuild, never strip.** `explain` parses the URL and keeps a result only if every part checks out, then
  writes `https://<host>/<segments>` from those parts alone. User info, password, port, query and fragment are
  never copied, so a credential cannot reach the output through a mistake in removing it. The steps:
  - A `?`, `#`, whitespace or control character anywhere refuses the URL, before parsing. A query or fragment is
    unusual for these hosts and is where a token is most likely, and `urlsplit` cannot tell an empty query from
    none. `urlsplit` silently drops tabs and newlines, so `git<tab>hub.com` would read as `github.com` while git
    fetches another host.
  - `[user@]host:path` (matching `config.SCP`, no `://`) takes host and path from `SCP`'s groups, as git does: the
    host runs up to the first `:`, so `user:tok@github.com:o/r` has host `user` and is refused. Any other form goes
    through `urllib.parse.urlsplit`, scheme `https`, `http`, `ssh` or `git` only, so `file://` and absolute paths
    never match.
  - The host is `urlsplit(...).hostname`, which drops user info and port and lowercases; a port that is not a
    number (`ssh://git@github.com:o/r`) refuses the URL. The host must equal `github.com` or `gitlab.com`:
    `github.com@evil.example` has host `evil.example`; `github.com.evil.example` and `www.github.com` are not
    equal.
  - The path, without one leading `/` and one trailing `/`, splits at `/`; the last segment loses one `.git`. Each
    segment must match `config.NAME` (`[A-Za-z0-9][A-Za-z0-9._-]*`), which refuses empty segments, `.`, `..`,
    `~user` and percent-encoding. GitHub needs exactly two segments, GitLab two or more.
- **One pure function, tested directly with the spec's URL lists.** `explain.repository(url) -> str | None`
  returns the rebuilt repository URL. Its accepted and refused cases are a `pytest.mark.parametrize` table in
  `tests/commands/test_explain.py`, each case asserting the exact result; that also proves no user info,
  password or token is in it. A substring check would be wrong: user `git` is in `github.com`. The diagram tests go
  through `main` as today. Whatever the function returns is all `mermaid` may show of a URL.
- **Ask git whether it rewrites the URL.** `git --git-dir <the Source's cache repository> ls-remote --get-url <url>`
  prints the URL after every `insteadOf` rule, without contacting the remote; run in the cache repository, it reads the
  configuration the fetch reads. A **Source** gets links only if git prints the URL unchanged, and none if its cache
  repository is missing (another cache served it). `explain.repositories(config, cache)` does this once per **Source**,
  after the **Hull** is computed, and returns alias → repository URL; `mermaid` takes that mapping, so it runs no git
  itself and its tests need no git configuration.
- **Tests seed the cache instead of rewriting URLs.** A test clones its local upstream into
  `Cache.repository(<https URL>)`; `checkout` finds the **Ref** there and never fetches. Rewriting with
  `insteadOf`, as other tests do, would now remove the links under test. One test does rewrite, to check that.
- **Links: repository URL, then `/tree/<Ref>` (GitHub) or `/-/tree/<Ref>` (GitLab), then the folder.** The folder
  of the subgraph is the `subdirectory`; of a **Skill**, `hull.upstream[skill]` resolved, relative to
  `hull.roots[alias]` resolved, as POSIX, `.` adding nothing. The root is the tree root, so that path already
  starts with the `subdirectory`. Discovery follows symbolic links to folders, and a forge shows a symbolic link as
  a file, so the resolved path is the one with a page; a folder resolving outside the root gets no link.
  `upstream` is the folder before any **Patch**, as the upstream tree at the **Ref** shows it. Each segment goes
  through `urllib.parse.quote(segment, safe="")`, so `#`, `?`, `%`, `'`, `<` and spaces cannot end the path, the
  attribute or the tag. The **Ref** is hex, the repository URL `NAME` segments: neither needs encoding.
- **`mermaid(hull, sources, repositories)`**: `sources` the `Config`'s mapping, for the **Ref** and
  `subdirectory`; `repositories` from `explain.repositories`. They belong to the config, not the **Hull**; adding
  them to `Hull` would widen a pipeline type for one view. `link()` is unchanged.
- **Subgraphs in order of each alias's first Skill in hull order, `s0…`; nodes inside in hull order; arrows after
  all subgraphs.** Node IDs stay `n0…`, so `n` and `s` never clash. Arrows outside every subgraph keep Mermaid from
  moving a node into the subgraph where an arrow happens to be written.
- **HTML link, not `click`.** Per the manual check. The same `<a>` goes in node labels, untested there until
  apply's manual check.
- **Title `alias · host/segments`.** The reader sees which repository a box is without hovering. `·` is
  non-ASCII; Mermaid and mermaid.live take UTF-8, and `link()` JSON-encodes the diagram.
- **Entry style `fill:#fde68a,stroke:#b45309,stroke-width:3px,color:#451a03` (amber).** Chosen from three
  previews against mermaid.live's white nodes and pink subgraphs. The explicit text color keeps the label readable
  under a dark theme, whose default text is light.

## Risks / Trade-offs

- [Renderers that escape or strip HTML, or disable links (GitHub)] → the title shows
  the `<a …>` markup or plain text; the diagram stays correct. Documented in `docs/design.md`.
- [A user of a self-hosted GitHub or GitLab expects it linked] → alias only; adding a host means checking that
  its paths are names too, a later change.
- \[`<a>` in node labels behaves differently from titles\] → manual check in apply; drop node links if it fails, a
  spec change.
- [GitHub or GitLab changes its tree URL] → links break; the diagram stays correct.
- \[A shared `--link` names the user's GitHub or GitLab repositories, private ones included, where the diagram
  showed only aliases before\] → accepted: the repository is what the link is for, and the user chooses to share
  it. Documented in `docs/design.md` and `tree --help`.
