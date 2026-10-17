# Design

## Context

`cli.py` dispatches `init`, `resolve`, `build` and `update` through argparse. `_resolve` loads the config and
computes the **Hull**. `lock.tree(hull)` renders `resolve`'s tree; `lock.suggestions(hull)` renders the
suggestions. `update._write_refs` already edits `skill-graft.toml` in place with `tomlkit` and
`files.atomic_write`, keeping a symlink. `config.load()` reads the file and validates it; nothing parses config
text that is not on disk. `resolve.resolve` builds per-**Source** indexes but does not return them. `Hull` keeps
every edge with its `text`; the lock does not, which is one reason `why` and `tree` resolve rather than read it.

## Goals / Non-Goals

**Goals:**

- One resolution path for every command: `why`, `tree` and the edits go through the same `_resolve` as `resolve`.
- An edit is checked against exactly the text that will be written.

**Non-Goals:**

- A cached or incremental **Hull**; `why`/`tree` cost the same as `resolve`.
- "Did you mean" for mistyped commands: Python 3.11's argparse has none.

## Decisions

- **Explain from a fresh Hull, never the lock.** The lock lacks the reference text, can be missing or stale, and
  the spec "the lock is output only" forbids reading it. The alternative, storing `text` in the lock and reading
  it, would make the lock an input. `why`/`tree` call `_resolve` in a temporary work folder and render.
- **`explain.py`** holds the reverse tree, Mermaid and link. The reverse tree inverts `hull.edges` (slash and
  Skill tool only, self-edges dropped), deduplicated per (source, target, kind, bind) as `lock.tree` does, and
  ordered by each source's position in `hull.skills` (the walk's order). Mermaid reuses `lock.tree`'s line
  filter (prose only when the
  deployed name differs) and node label, so the two shapes cannot drift. Those two helpers move out of `tree`'s
  closure into module functions in `lock.py`.
- **The mermaid.live link** is `pako:` plus the zlib-compressed (level 9) JSON state in url-safe base64
  without padding, the state being `{"code": <diagram>, "mermaid": "{\"theme\": \"default\"}"}`. That is pako's
  `deflate` (zlib format) and js-base64's url-safe form, as mermaid-live-editor decodes them. The test
  decodes it back. One manual check during apply: paste a generated link into a browser.
- **Edits: `config.load` splits into `load()` and `parse(text, file)`.** `edit.py` reads the TOML bytes, edits a
  `tomlkit` document, then `config.parse(tomlkit.dumps(doc), file)` gives the **Config** that is resolved. Only on
  success does it write those same bytes, then the lock. The alternative, mutating a loaded `Config`, could
  resolve something other than what gets written.
- **The in-place write is shared.** `update._write_refs`' read/parse/atomic-write moves to an `edit` helper used
  by both, so the symlink and byte rules live once.
- **Skill existence** for `add`/`rename`/`why <id>` uses `discovery.find` on the index of the alias.
  `resolve.resolve` exposes its indexes (it returns them beside the **Hull**), so no **Source** is indexed twice.
- **Array style.** tomlkit's `Array.append` keeps a multi-line array multi-line when the existing items each
  have their own line; the trailing-comma case is pinned by a test, and where tomlkit falls short the item is
  added with explicit `Whitespace`/`Comment` trivia. A new `entries` key is inserted before the first table by
  rebuilding the document body order (tomlkit `container` insert at index).
- **Notices** go through the existing `warn` path's stream (stderr) but without the `warning:` prefix: a new
  `notice()` in `errors.py`.
- **Help.** Every `add_parser` gets `help=` (list summary) and `description=` (page). The `help` subcommand
  re-invokes the parser with `[command, "--help"]`, or `["--help"]`. A custom `ArgumentParser.error` override on
  the top-level parser appends the command list for no or unknown command. argparse already exits 2 on usage
  errors. `--link` without `--format mermaid` is checked after parsing via `parser.error`, which also exits 2.

## Risks / Trade-offs

- \[`why`/`tree` fetch on a cold cache\] → Same as `resolve`; documented in their help text.
- [mermaid.live changes its URL format] → The link is a convenience; `--format mermaid` stays. The state shape
  lives in one function.
- [tomlkit formatting gaps for multi-line arrays] → Pinned by scenario tests; fallback to explicit trivia.
- \[Large **Hulls** give long URLs\] → Compressed; browsers accept far longer fragments than a typical hull needs.
