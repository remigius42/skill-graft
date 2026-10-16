# Tasks

Apply with the `tdd` skill: each task red-green-refactor (failing test first, then code), one commit, and
`pre-commit run --all-files` green. New words go into `.cspell.yaml`. Tests set `HOME` to `tmp_path` and build
synthetic **Skills** and git repositories.

## 1. Config

- [ ] 1.1 `[rename]` (`Config.renames: dict[SkillId, str]`, key a declared **Skill ID**, value one segment) and
  `reserved` (`Config.reserved: list[str]`); both no longer unsupported. Verify: valid-rename, value-not-a-name,
  undeclared-alias-in-a-rename, valid-reserved-list, reserved-not-a-list-of-names, rename-table, patches-table.

## 2. References

- [ ] 2.1 `references.py`: prose alternatives (backticked name, bare hyphenated token) in the one regex,
  `kind = "prose"`, and a `span` on every **Reference**. Verify: backticked-and-hyphenated, not-prose,
  slash-form-wins, and every existing references test.

## 3. Names

- [ ] 3.1 `rename.py`: `deployed` (+ unused-rename warnings), `check` (uniqueness ignoring case with a `[rename]`
  hint, user `reserved` error, `SHIPPED` warning), `SHIPPED` checked against current Claude Code and Codex docs;
  `resolve.resolve` uses it before and after the walk instead of `_check_deployed_names`. Verify: renamed,
  not-renamed, rename-outside-the-hull, clash-across-sources, clash-through-a-reference, rename-settles-a-clash
  (resolve level), rename-onto-another-skill's-name, reserved-by-the-user, renamed-out-of-the-way, shipped-clash,
  renamed-onto-a-shipped-name, both-lists.

## 4. Hull

- [ ] 4.1 `hull.walk`: prose candidates (**Bind**, else own `index.folders`), classified after the BFS into
  `prose` edges or suggestions; prose use marks a **Bind** used; `occurrences` per **Skill**, self-**References**
  included. Verify: inside-the-hull, outside-the-hull, only-another-source-has-it, matches-nothing, bound-prose,
  bound-prose-outside-the-hull, prose-bound-to-nothing, used-by-prose-only, and every existing hull test.

## 5. Rewrites and build

- [ ] 5.1 `rename.set_name` and `rename.rewrites` (span replacement per UTF-8 Markdown file, renamed and bound
  targets, BOM and line endings kept); `Hull` carries `deployed` and `rewrites`. Verify: unit tests for
  name-line-replaced, front-matter-without-a-name, no-front-matter, and rewrites for slash, Skill tool (quotes and
  arguments kept), backticked and hyphenated prose, bound-to-another-name, self-reference, sibling file,
  unresolved-names-untouched, non-UTF-8 file untouched.
- [ ] 5.2 `vendor` writes `.apm/skills/<deployed>/` and the rewrites over the copy before the swap. Verify:
  whole-folder-copied, renamed-skill-vendored, slash-reference-to-a-renamed-skill, skill-tool-and-prose-forms,
  bound-to-another-name, rename-settles-a-clash (build), clash-across-sources (lock unchanged), copy-fails, and
  every existing build and git-build test.

## 6. Lock and resolve output

- [ ] 6.1 `lock.py`: `deployed` on renamed **Skills**, `prose` edges, `[[suggestions]]`, `folder_hash` over the
  rewrites in `resolve`. Verify: renamed-skill, suggestion-recorded, prose-edge, rename-changes-the-hash,
  resolve-and-build-agree, same-input.
- [ ] 6.2 Tree marks `as <deployed>` and shows `prose` edges to renamed targets; `resolve` prints suggestions
  after the tree, `build` does not. Verify: tree, renames-marked, suggestion-printed, no-suggestions.

## 7. Docs

- [ ] 7.1 `docs/design.md` (prose detection rules, bound **References** rewritten, `SHIPPED` and its severity,
  lock `deployed` and `[[suggestions]]`, tree `as`), `README.md` (renames and prose built). Verify:
  `pre-commit run --all-files` green.
