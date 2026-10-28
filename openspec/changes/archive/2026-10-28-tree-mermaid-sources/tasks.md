# Tasks

Apply with the `mp-tdd` skill: each task red-green-refactor, one commit.

## 1. One subgraph per Source, amber Entries

- [x] 1.1 Change `explain.mermaid` to `mermaid(hull, sources)`, `cli.py` passing `config.sources` for both
  `--format mermaid` and `--link`; group nodes into subgraphs `s0…` per alias in order of first **Skill**, titled
  with the alias, arrows after the last `end`; `classDef entry` amber as in the spec; tests in
  `tests/commands/test_explain.py`: "Diagram" with the new expected output, "Subgraphs in hull order" (`a/x`
  calls `/y` in `b`, which calls `/z` in `a`), "No source links" replacing `test_mermaid_has_no_source_links`
  (the `https://…example.com…` URL served from a local repository through `url.<upstream>.insteadOf` in the
  test's `GIT_CONFIG_GLOBAL` file); `test_mermaid_labels_quoted` counting the subgraph title too;
  `test_mermaid_link_decodes_to_the_diagram` still passes; verify the new tests fail first, then pass

## 2. Recognize GitHub and GitLab repositories

- [x] 2.1 Add `explain.repository(url) -> str | None` as the design's "Rebuild, never strip" describes; test it
  with a parametrized table holding every URL of the spec's "Repository URLs" and "Not a repository" scenarios,
  plus `HTTPS://GITHUB.COM/o/r` and `https://github.com:443/o/r` (accepted), `https://github.com/o/r.git.git`
  (repository `r.git`), and `https://github.com/o/r//`, `https://github.com/o/r?`, `https://github.com/o/r#` and
  `ssh://git@github.com:o/r`, and URLs holding a space, a newline or `\x00` (refused); assert the exact result,
  which also proves no user info is in it (no substring check: user `git` is in `github.com`); verify the tests
  fail first, then pass

## 3. Links for GitHub and GitLab Sources

- [x] 3.1 Add a `tests/conftest.py` helper cloning an `Upstream` into `Cache.repository(url)` for a given URL, and
  `explain.repositories(config, cache)`: alias → repository URL for each git **Source** `repository()` accepts
  whose cache repository exists and for which `git --git-dir <it> ls-remote --get-url <url>` prints `<url>`
  unchanged; `cli.py` passes it to `mermaid(hull, sources, repositories)`; tests through `main`: a seeded GitHub
  URL is linked, "Rewritten URL" (an `insteadOf` rule in the test's `GIT_CONFIG_GLOBAL` file) is not; verify they
  fail first, then pass
- [x] 3.2 For a **Source** in `repositories`, title the subgraph
  `alias · <repository without https://>` wrapped in a link to `<repository>/tree/<Ref>` (GitLab `/-/tree/<Ref>`)
  plus the `subdirectory`, and wrap each of its node labels in a link to its folder, resolved, relative to the
  resolved tree root (`.` adds nothing; outside the root, no link), each path segment through
  `quote(…, safe="")`; tests through `main`, URLs seeded into the cache: "GitHub Source", "GitLab Source without
  subdirectory", "Folder names encoded", "Skill folder through a symbolic link", plus a symbolic link leaving the
  tree (no link for that **Skill**); "Labels quoted" with a GitHub **Source**; verify they fail first, then pass.
  The symbolic link leaving the tree cannot be built: discovery of a git **Source** follows only links that stay
  inside it, and a `subdirectory` holds none, so that guard stays untested
- [x] 3.3 Manual check: generate `tree --format mermaid --link` for a config with a GitHub and a GitLab **Source**,
  open it in mermaid.live, confirm subgraph title and node links open the right tree in a new tab; if node links
  fail, stop and report before changing the spec
- [x] 3.4 After review: no link, and no failure, when git cannot read a **Source**'s cache repository
  ("Unreadable cache repository"); `ls-remote` only for **Sources** with a **Hull** **Skill**; `host:/path` refused.
  Then `repositories(config, cache, hull)` returns a `Repository` (`host/path`, the tree URL at the **Ref**, the
  `subdirectory`) and `mermaid(hull, repositories)` takes only that, replacing the signatures of 1.1, 3.1 and 3.2

## 4. Documentation

- [x] 4.1 Update `docs/design.md`'s `tree` entry: subgraphs per **Source**, amber **Entries**, links only for
  GitHub and GitLab and why (the design's first decision, in short), the URL rebuilt not stripped, none for a URL
  git rewrites, a shared `--link` naming the repositories, renderers that
  strip HTML or disable links; drop "no links to sources"; `tree --help` for `--link` says the link names the
  GitHub and GitLab repositories; verify
  `pre-commit run --all-files`

## 5. Archive

- [x] 5.1 In the archive commit, add an `### Added` entry under `[Unreleased]` in `CHANGELOG.md`:
  `tree --format mermaid` groups **Skills** by **Source**, draws **Entries** amber, and links a GitHub or GitLab
  **Source** and its **Skills** to the upstream tree at its **Ref**; verify `pre-commit run --all-files`
