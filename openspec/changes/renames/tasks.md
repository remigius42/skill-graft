# Tasks

Apply with the `tdd` skill: each task red-green-refactor (failing test first, then code), one commit, and
`pre-commit run --all-files` green. New words go into `.cspell.yaml`. Tests set `HOME` to `tmp_path` and build
synthetic **Skills** and git repositories. `[rename]` and `reserved` stay unsupported config keys until the task
that honors them in full, so no commit accepts intent it ignores.

## 1. References

- [ ] 1.1 `references.py`: prose alternatives (backticked name, bare hyphenated token, boundaries as the hull spec
  lists) in the one regex, `kind = "prose"`, and a `span` on every **Reference**. Verify: backticked-and-hyphenated,
  not-prose, slash-form-wins, and every existing references test.

## 2. Hull

- [ ] 2.1 `hull.walk`: prose candidates (**Bind**, else exactly one readable own folder and no unreadable one),
  classified after the BFS into `prose` edges or suggestions; prose use marks a **Bind** used; `occurrences` per
  **Skill**, self-**References** included. Verify: inside-the-hull, outside-the-hull, only-another-source-has-it,
  ambiguous-in-its-own-source, matches-nothing, bound-prose, bound-prose-outside-the-hull, prose-bound-to-nothing,
  used-by-prose-only, and every existing hull test.

## 3. Rewrites

- [ ] 3.1 `rename.py`: `set_name` and `rewrites` from a deployed-name map (span replacement per UTF-8 Markdown
  file, BOM and line endings kept); `Hull` carries `deployed` (names only, until 4.1) and `rewrites`. Verify: unit
  tests for name-line-replaced, front-matter-without-a-name, no-front-matter, and rewrites for slash, Skill tool
  (quotes and arguments kept), backticked and hyphenated prose, self-reference, sibling file,
  unresolved-names-untouched, non-UTF-8 file untouched.
- [ ] 3.2 `vendor` writes the rewrites over the copy before the swap, through `files.atomic_write`; `resolve` hashes
  with them. Bound **References** are now rewritten end to end. Verify: bound-to-another-name (build), a read-only
  upstream Markdown file rewritten, copy-fails, and every existing build and git-build test.

## 4. Renames and reserved names

- [ ] 4.1 `[rename]` end to end: `Config.renames` (key a declared **Skill ID**, value one segment), `rename.deployed`
  with unused-rename warnings, uniqueness after renames with the `[rename]` hint (entries-only early check, no
  warnings), `vendor` under `.apm/skills/<deployed>/`, `name:` set. Verify: valid-rename, value-not-a-name,
  undeclared-alias-in-a-rename, rename-table (its `[rename]` half), patches-table, renamed, not-renamed,
  rename-outside-the-hull (warned once), clash-across-sources (lock unchanged), clash-through-a-reference,
  rename-settles-a-clash, rename-onto-another-skill's-name, renamed-skill-vendored, whole-folder-copied,
  slash-reference-to-a-renamed-skill, skill-tool-and-prose-forms, self-reference, sibling-file.
- [ ] 4.2 `reserved` end to end: `Config.reserved`, the user's list as errors, `SHIPPED` (checked against current
  Claude Code and Codex docs) as warnings, once per **Skill**. Verify: valid-reserved-list,
  reserved-not-a-list-of-names, rename-table (its `reserved` half), reserved-by-the-user, renamed-out-of-the-way,
  shipped-clash (warned once), renamed-onto-a-shipped-name, both-lists.

## 5. Lock and resolve output

- [ ] 5.1 `lock.py`: `deployed` on renamed **Skills**, `prose` edges, `[[suggestions]]`. Verify: renamed-skill,
  suggestion-recorded, prose-edge, rename-changes-the-hash, resolve-and-build-agree, same-input.
- [ ] 5.2 Tree marks `as <deployed>` and shows rewritten `prose` edges; `resolve` prints suggestions after the tree,
  `build` does not. Verify: tree, renames-marked, bound-prose-shown, suggestion-printed, no-suggestions.

## 6. Docs

- [ ] 6.1 `docs/design.md` (prose detection rules, bound **References** rewritten, `SHIPPED` and its severity,
  lock `deployed` and `[[suggestions]]`, tree `as`), `README.md` (renames and prose built); at archive, the main
  hull spec's Purpose names prose **References**. Verify: `pre-commit run --all-files` green.
