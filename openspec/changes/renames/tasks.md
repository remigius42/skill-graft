# Tasks

Apply with the `tdd` skill: each task red-green-refactor (failing test first, then code), one commit, and
`pre-commit run --all-files` green. New words go into `.cspell.yaml`. Tests set `HOME` to `tmp_path` and build
synthetic **Skills** and git repositories. `[rename]` and `reserved` stay unsupported config keys until the task
that honors them in full, so no commit accepts intent it ignores.

## 1. References

- [x] 1.1 `references.py`: prose alternatives (backticked name, bare hyphenated token, boundaries as the hull spec
  lists) in the one regex, `kind = "prose"`, a `span` on every **Reference** (the name alone, trailing dots
  excluded), and `SKILL.md`'s front matter `name:` value skipped. Verify: backticked-and-hyphenated, not-prose (`#`
  anchors included), own-name-line (scan level), slash-form-wins, the span of `/grilling.`, and every existing
  references test.

## 2. Hull

- [x] 2.1 `hull.walk`: prose candidates (**Bind**, else exactly one readable own folder and no unreadable one),
  classified after the BFS into `prose` edges or suggestions; prose use marks a **Bind** used; `occurrences` per
  **Skill**, self-**References** included. Verify: inside-the-hull, outside-the-hull, only-another-source-has-it,
  ambiguous-in-its-own-source, matches-nothing, bound-prose, bound-prose-outside-the-hull, prose-bound-to-nothing,
  used-by-prose-only, and every existing hull test.

## 3. Rewrites

- [x] 3.1 `rename.py`: `set_name` (quoting a name YAML would misread) and `rewrites(hull)` (span replacement per
  UTF-8 Markdown file, BOM and line endings kept), computed on demand; `Hull` carries `deployed` (names only, until
  4.1). Verify: unit tests for name-line-replaced, name-YAML-would-misread, front-matter-without-a-name,
  no-front-matter, and rewrites for slash (sentence-end-kept), Skill tool (quotes and arguments kept), backticked
  and hyphenated prose, self-reference, sibling file, own-name-line, unresolved-names-untouched, non-UTF-8 file
  untouched.
- [x] 3.2 `vendor` copies through a `copy_function` writing the rewritten bytes; `lock.render` hashes with the
  rewrites, so `resolve`, `build` and `update` (lock and hull diff) agree; `build` hashes its copies by deployed name. Bound
  **References** are now rewritten end to end. Verify: bound-to-another-name (build), a read-only upstream file and
  folder rewritten, bound-self-reference, copy-fails, resolve-and-build-agree for a bind, an `update` lock equal to
  the `resolve` lock, and every existing build and git-build test.

## 4. Renames and reserved names

- [x] 4.1 `[rename]` end to end: `Config.renames` (key a declared **Skill ID**, value one segment), `rename.deployed`
  with unused-rename warnings, uniqueness after renames with the `[rename]` hint (entries-only early check, no
  warnings), `vendor` under `.apm/skills/<deployed>/`, `name:` set. Verify: valid-rename, value-not-a-name,
  undeclared-alias-in-a-rename, rename-table (its `[rename]` half), patches-table, renamed, not-renamed,
  rename-outside-the-hull (warned once), clash-across-sources (lock unchanged), clash-through-a-reference,
  rename-settles-a-clash, rename-onto-another-skill's-name, renamed-skill-vendored, whole-folder-copied,
  slash-reference-to-a-renamed-skill, skill-tool-and-prose-forms, self-reference, sibling-file.
- [x] 4.2 `reserved` end to end: `Config.reserved`, the user's list as errors, `SHIPPED` (checked against current
  Claude Code and Codex docs) as warnings, once per **Skill**. Verify: valid-reserved-list,
  reserved-not-a-list-of-names, rename-table (its `reserved` half), reserved-by-the-user, renamed-out-of-the-way,
  shipped-clash (warned once), renamed-onto-a-shipped-name, both-lists.

## 5. Lock and resolve output

- [x] 5.1 `lock.py`: `deployed` on renamed **Skills**, `prose` edges, `[[suggestions]]`. Verify: renamed-skill,
  suggestion-recorded, prose-edge, rename-changes-the-hash, resolve-and-build-agree, same-input.
- [ ] 5.2 Tree marks `as <deployed>` and shows rewritten `prose` edges; `resolve` prints suggestions after the tree,
  `build` does not. Verify: tree, renames-marked, bound-prose-shown, suggestion-printed, no-suggestions.

## 6. Docs

- [ ] 6.1 `docs/design.md` (prose detection rules, bound **References** rewritten, `SHIPPED` and its severity,
  lock `deployed` and `[[suggestions]]`, tree `as`), `README.md` (renames and prose built); at archive, the main
  hull spec's Purpose names prose **References**. Verify: `pre-commit run --all-files` green.
