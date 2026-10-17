# Tasks

Apply with the `tdd` skill: each task red-green-refactor (failing test first, then code), one commit, and
`pre-commit run --all-files` green. New words go into `.cspell.yaml`. Tests set `HOME` to `tmp_path` and build
synthetic **Skills** and git repositories. Each group updates `README.md` for what it ships.

## 1. Help and usage errors

- [ ] 1.1 `cli.py`: `help=`/`description=` on the top level and on `init`, `resolve`, `build` and `update` and
  their arguments; the `help [command]` subcommand; no or unknown command (top level or in `help`) prints the
  command list on stderr and exits 2. Verify: top-level-help, command-help (no package folder), same-text,
  unknown-topic, unknown-command, no-command.

## 2. Shared resolution

- [ ] 2.1 `config.parse(text, file)` split from `load()`; `resolve.resolve` also returns the **Source** indexes;
  `lock.py`'s tree line filter and node label become module functions; `errors.notice()`. Verify: every existing
  test unchanged and green.
- [ ] 2.2 `resolve`'s suggestion header names `skill-graft add <skill id>`. Verify: suggestion-printed,
  no-suggestions.

## 3. Tree

- [ ] 3.1 `tree [--format text]`: `_resolve` then `lock.tree`, writing nothing. Verify: same-tree, no-lock, stale
  lock unchanged (byte compare), failing-patch.
- [ ] 3.2 `explain.mermaid(hull)` and `--format mermaid`. Verify: diagram, quotes-in-a-label, no-source-links,
  output identical across two runs.
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
  outside-the-hull-not-mentioned, unknown, undeclared-alias.

## 5. Edits

- [ ] 5.1 `edit.py`: read, edit a `tomlkit` document, `config.parse`, resolve, then write TOML (atomic, symlink
  kept, untouched when unchanged) and lock, print as `resolve`; `update._write_refs` uses the same write. Verify:
  every update test green, plus edit-fails-to-resolve and symlinked-config through 5.2.
- [ ] 5.2 `add <skill-id>…`. Verify: edit-succeeds, appended, multi-line-array, no-entries-key, unknown-skill,
  undeclared-alias, already-an-entry (bytes and mtime kept), already-reachable, notice-stream.
- [ ] 5.3 `remove <skill-id>…`. Verify: removed, not-an-entry, still-reachable.
- [ ] 5.4 `rename <skill-id> <name>`, undo by upstream name. Verify: new-rename, comments-survive,
  already-that-name, invalid-name, undone, outside-the-hull, clash, user's-reserved-name,
  shipped-reserved-name, unknown-skill-to-rename, missing-argument (exit 2).

## 6. Docs

- [ ] 6.1 `docs/design.md`: `why`, `tree`, edits and help marked as built, the mermaid.live state shape. At
  archive, the new main specs keep their Purpose. Verify: `pre-commit run --all-files` green, and
  `openspec validate explain-and-edit --strict` passes.
