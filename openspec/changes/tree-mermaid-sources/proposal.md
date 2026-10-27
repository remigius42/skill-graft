# Proposal

## Why

`tree --format mermaid` draws every **Skill** in one flat diagram. With several **Sources**, the reader has to
read each **Skill ID** to see where a **Skill** comes from, the **Entries** differ from the **Skills** they pull in
only by a slightly thicker border, and nothing in the diagram leads to the upstream code. `explain-and-edit` left
links to the **Sources** out of scope; a manual check in mermaid.live has since shown that an HTML link in a
subgraph title works there and opens a new tab, while Mermaid's `click … _blank` does not.

## What Changes

- The Mermaid diagram draws one subgraph per **Source** holding its **Skills**, in **Hull** order, titled with its
  alias; arrows cross subgraphs as before. Node IDs, label texts and arrows stay as they are.
- **Entries** are drawn amber, not only with a thicker border.
- A **Source** whose git URL names a GitHub or GitLab repository gets the title `alias · github.com/owner/repo`,
  linking to its tree at its **Ref** in a new tab, and each of its **Skills** links to its folder at that **Ref**.
  The URL is rebuilt from the host and the repository's path; nothing else from the configured URL appears. A
  URL git's configuration rewrites (`insteadOf`) gets no link, as git may fetch it from elsewhere. A shared
  `--link` then names the repository, private ones included.
- Every other **Source** (path **Sources**, local git paths, other hosts) shows only its alias. A URL from
  `skill-graft.toml` can hold a token anywhere, and `--link` puts the diagram into a URL the user may share; only
  for GitHub and GitLab can skill-graft tell, for every part it shows, that no secret is in it.

Out of scope: Mermaid `click` lines; links to other forges or self-hosted GitHub or GitLab instances.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `explain`: "Tree as Mermaid" groups **Skills** by **Source** and draws **Entries** amber; the "No source links"
  scenario now covers every **Source** outside GitHub and GitLab. New requirements say which URLs name a GitHub
  or GitLab repository and how those **Sources** and their **Skills** link to it.

## Impact

- `src/skill_graft/commands/explain.py`: `mermaid(hull, sources, repositories)` with subgraphs and links;
  recognizing a GitHub or GitLab repository URL; asking git whether it rewrites it.
- `src/skill_graft/cli.py`: passes `config.sources` and the linkable repositories to `explain.mermaid`.
- `tests/commands/test_explain.py`: the diagram scenarios through `main`, GitHub and GitLab URLs served from a
  local repository seeded into the cache; the URL cases against the recognizing function directly.
- `tests/conftest.py`: a helper seeding the cache for a URL.
- `docs/design.md`'s `tree` entry. `CHANGELOG.md` at archive: an `### Added` entry.
