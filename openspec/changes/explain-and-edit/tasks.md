# Tasks

Apply with the `tdd` skill: each task red-green-refactor (failing test first, then code), one commit, and
`pre-commit run --all-files` green. New words go into `.cspell.yaml`. Tests set `HOME` to `tmp_path` and build
synthetic **Skills** and git repositories. Each group updates `README.md` for what it ships.

## 1. Help and usage errors

- [x] 1.1 `cli.py`: `help=`/`description=` on the top level and on `init`, `resolve`, `build` and `update` and
  their arguments; the `help [command]` subcommand (argument `dest="topic"`); no or unknown command (top level
  or in `help`) prints the command list on stderr and exits 2. Verify: top-level-help for the commands that exist
  so far, extended by each later task that adds a command, which also gives it `help=`/`description=` and its own
  command-help test; command-help (no package folder), same-text (`help tree` does not run `tree`, checked once
  3.1 lands), unknown-topic, unknown-command, no-command.

## 2. Shared resolution

- [x] 2.1 `config.parse(text, file)` split from `load()`; `resolve.indexes()` split from `resolve.resolve`;
  `lock.py`'s tree line filter, node label and edge label become module functions (`errors.notice()` lands with
  its first use, in 5.2). Verify: every existing test unchanged and green.
- [ ] 2.2 `resolve`'s suggestion header names `skill-graft add <skill id>`. Verify: suggestion-printed,
  no-suggestions.

## 3. Tree

- [ ] 3.1 `tree [--format text]`: `_resolve` then `lock.tree`, writing nothing. Verify: same-tree, no-lock, stale
  lock unchanged (byte compare), failing-patch.
- [ ] 3.2 `explain.mermaid(hull)` and `--format mermaid`, labels escaped. Verify: diagram, labels-quoted,
  no-source-links, output identical across two runs.
- [ ] 3.3 `explain.link(source)` and `--link`; `--link` without `--format mermaid` exits 2. Verify:
  link-decodes-to-the-diagram, link-without-mermaid; once by hand, the printed URL opens the diagram on
  mermaid.live (note the result in the commit body).

## 4. Why

- [ ] 4.1 `explain.why(hull, skill)`: the inverted tree with `├─←`/`└─←`, `(entry)`, `(*)`, labels as in
  `resolve`'s tree, prose and self-edges left out; `why` command. Verify: two-paths, repeated-skill,
  an-entry-asked-about, renamed-patched-and-bound, prose-not-shown.
- [ ] 4.2 `<skill>` lookup and errors: **Skill ID** or **Deployed name**; upstream name of a renamed **Skill**;
  outside the **Hull** with and without prose mentions; unknown; undeclared alias. Verify: deployed-name,
  unrenamed-skill-by-name, upstream-name-of-a-renamed-skill, outside-the-hull-mentioned-in-prose,
  outside-the-hull-not-mentioned, bare-name-outside-the-hull-mentioned-in-prose, unknown, undeclared-alias.

## 5. Edits

- [ ] 5.1 `edit.py`: read, edit a `tomlkit` document, `config.parse`, resolve, then write TOML (atomic, symlink
  kept, untouched when unchanged, relative paths from the unresolved config path) and lock, print as `resolve`;
  `update._write_refs` uses the same write. Verify: every update test green, plus edit-fails-to-resolve and
  symlinked-config (with a relative path source) through 5.2.
- [ ] 5.2 `add <skill-id>…`. Verify: edit-succeeds, appended, multi-line-array, no-entries-key, unknown-skill,
  undeclared-alias, already-an-entry (bytes and mtime kept), already-reachable, reached-only-through-itself,
  added-together, notice-stream, no-op (nothing resolved, lock untouched, nothing on stdout).
- [ ] 5.3 `remove <skill-id>…`. Verify: removed, not-an-entry, still-reachable, last-entry, other comments kept,
  removed-not-circular (`mp/x` reached via `mp/y`, `mp/z` calling back: the notice names `mp/y`).
- [ ] 5.4 `rename <skill-id> <name>`, undo by upstream name. Verify: new-rename, comments-survive,
  already-that-name, invalid-name, undone, outside-the-hull, clash, user's-reserved-name,
  shipped-reserved-name, unknown-skill-to-rename, missing-argument (exit 2).

## 6. Docs

- [ ] 6.1 `docs/design.md`: `why`, `tree`, edits and help marked as built, the mermaid.live state shape. At
  archive, the new main specs keep their Purpose. Verify: `pre-commit run --all-files` green, and
  `openspec validate explain-and-edit --strict` passes.
