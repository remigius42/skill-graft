# Tasks

Apply with the `tdd` skill: each task red-green-refactor (failing test first, then code), one commit, and
`pre-commit run --all-files` green. New words go into `.cspell.yaml`. Tests build synthetic **Skills**; no real
skill text is copied in. Each group updates `README.md` or `docs/design.md` for what it ships.

## 1. Slash references

- [ ] 1.1 `references.py`: the two lookbehinds on the slash alternative. Verify: path-arguments, after-a-code-span,
  standalone-token (with `` (`/grilling`) `` and `'/grilling'`), and every existing hull test unchanged.
  `docs/design.md`: the slash rule.

## 2. Skill tool sentences

- [ ] 2.1 `references.scan`: the sentence pass, text `Skill tool "name"`, prose matches on its spans skipped.
  Verify: sentence-form, backticked-name-in-a-sentence (no prose edge in the lock), sentence-across-lines,
  outside-the-sentence, unquoted-name, call-forms unchanged; `tree` shows `(Skill tool "grilling")`.
- [ ] 2.2 Renames carry into the sentence form. Verify: renamed (vendored text reads `"mp-grilling"`), and a
  `[bind]` to `false` silences a sentence reference. `docs/design.md` and `README.md`: the sentence form.

## 3. Announced suggestions

- [ ] 3.1 `build` prints the suggestion line on stderr when there are suggestions. Verify: build-announces-
  suggestions, no-suggestions (no line), stdout holds no block.
- [ ] 3.2 `update` and `update --dry-run` print it for the new tips. Verify: update-announces-suggestions.
  `README.md`: where suggestions show.

## 4. Real-world check

- [ ] 4.1 By hand, outside the test suite, in this repository's project package: `uv run skill-graft update`
  then `tree` shows `mp/grilling`, `mp/domain-modeling`, `mp/codebase-design` and `mp/writing-for-agents` in
  the **Hull** and no `/orders` or `/build-tool` warning. Note the result in the commit body. Verify:
  `pre-commit run --all-files` green and `openspec validate reference-detection --strict` passes.
