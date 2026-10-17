# Tasks

Apply with the `tdd` skill: each task red-green-refactor (failing test first, then code), one commit, and
`pre-commit run --all-files` green. New words go into `.cspell.yaml`. Tests build synthetic **Skills**; no real
skill text is copied in. Each group updates `README.md` or `docs/design.md` for what it ships.

## 1. Slash references

- [x] 1.1 `references.py`: the quote-after-`(`/`[`/`,` and closing-backtick lookbehinds on the slash alternative.
  Verify: path-arguments (first argument, later argument, second list item), after-a-code-span
  (`` `lint`/check `` exercises the backtick rule), standalone-token (with `` (`/grilling`) `` and
  `run '/grilling'`), and every existing hull test unchanged. `docs/design.md`: the slash rule.

## 2. Skill tool sentences

- [x] 2.1 `references.scan`: the sentence windows and candidates, merged with the `REFERENCE` matches by span and
  sorted by offset; text `Skill tool "name"`. Verify: sentence-form, backticked-name-in-a-sentence (no prose
  edge in the lock), sentence-across-lines (no prose edge), sentence-ends (next sentence, list item),
  not-a-sentence-end (`e.g.`, period inside the quotes), one-reference-per-name (two `Skill tool`s, a
  `Skill(...)` inside the sentence), unquoted-name, call-forms unchanged, and a file with `/a` before a sentence
  naming `"b"` lists `a` first.
- [ ] 2.2 `hull.walk`: a sentence candidate that resolves to nothing is dropped without a warning; one that resolves
  is an edge of kind `skill-tool`, shown as `(Skill tool "grilling")` in `tree`. Verify: unresolved-name,
  tree label.
- [ ] 2.3 Renames and binds carry into the sentence form. Verify: renamed (vendored text reads `"mp-grilling"`,
  and a build with the rename succeeds twice), and a `[bind]` to `false` silences a candidate.
  `docs/design.md` and `README.md`: the sentence form.

## 3. Announced suggestions

- [ ] 3.1 `build` prints the suggestion line on stderr when there are suggestions. Verify:
  build-announces-suggestions, no-suggestions (no line), stdout holds no block.
- [ ] 3.2 `update` and `update --dry-run` print it for the new tips. Verify: update-announces-suggestions.
  `README.md`: where suggestions show.

## 4. Real-world check

- [ ] 4.1 By hand, outside the test suite, in this repository's project package: `uv run skill-graft update`
  then `tree` shows `mp/grilling`, `mp/domain-modeling`, `mp/codebase-design` and `mp/writing-for-agents` in
  the **Hull** and no `/orders` or `/build-tool` warning. Note the result in the commit body. Verify:
  `pre-commit run --all-files` green and `openspec validate reference-detection --strict` passes.
