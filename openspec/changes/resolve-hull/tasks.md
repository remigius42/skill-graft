# Tasks

Apply with the `tdd` skill: each task red-green-refactor (failing test first, then code), one commit, and
`pre-commit run --all-files` green. New words go into `.cspell.yaml`.

## 1. Config

- [ ] 1.1 `[bind]`: `Config.binds: dict[SkillId, SkillId | None]` (`None` from `false`); key and value
  `<alias>/<name>`, aliases declared; `bind` no longer unsupported. Verify: valid-bind, undeclared-alias,
  bind-to-nothing, value-neither-a-skill-ID-nor-false and rename-table scenarios; existing config tests pass.

## 2. References

- [ ] 2.1 `references.py`: scan a skill folder's `*.md` files (sorted, `SKILL.md` first, `.git` skipped) for
  slash and Skill tool references in text order; non-UTF-8 is an error naming the file. Verify: unit tests for
  standalone-token, paths-and-URLs, call-forms, reference-in-a-sibling-file and not-UTF-8.

## 3. Hull

- [ ] 3.1 `discovery.find` takes a label so errors name an entry, a reference or a bind. Verify: existing
  discovery tests pass with unchanged messages for entries.
- [ ] 3.2 `resolve.folders` covers every declared source; `hull.py` resolves references (own source, one
  other, several → error with `[bind]` hint, none → warning once per skill and name) and walks the hull BFS,
  ignoring self-references; `resolve.resolve` returns the `Hull`, checking symlinks and deployed names
  (ignoring case) across it. Verify: own-source-wins, one-other-source, several-other-sources, no-such-skill,
  two-hops, cycle, ambiguous-target, source-with-no-entry, clash-through-a-reference.
- [ ] 3.3 Binds in resolution: override, settle ambiguity, missing target error naming the bind, `false`
  drops the name, unused bind warning, unmatched warning names the `false` line; bound edges flagged `bind`. Verify:
  bind-across-sources, bind-settles-ambiguity, bind-to-a-missing-skill, path-in-a-code-block, unwanted-match,
  typo-in-a-bind, no-such-skill.

## 4. Build

- [ ] 4.1 `build` vendors the hull and prints warnings (no lock yet). Verify: referenced-skill-vendored,
  removed-entry, warning-does-not-stop-build, and every existing build and git-build test.

## 5. Lock and resolve command

- [ ] 5.1 `lock.py`: render TOML (sources, skills with entry flag and folder hash, edges with kind), sorted,
  written atomically. Verify: edges-with-kinds, hash-follows-content, same-input unit tests.
- [ ] 5.2 `skill-graft resolve`: write the lock, print the tree (stdout) and warnings (stderr); `build` writes
  the lock too; errors leave it unchanged. Verify: resolve-succeeds, resolution-error, upstream-moved-on (remote
  not contacted), tree, lock-written, lock-edited-by-hand.

## 6. Update

- [ ] 6.1 `update` resolves the hull at the new tips, writes the lock with the TOML (not on `--dry-run`).
  Verify: reference-turns-ambiguous-upstream, lock-follows-the-TOML, and every existing update test.
- [ ] 6.2 Hull diff: resolve at the old refs, print the legend and `+`/`-`/`~` lines sorted, `hull unchanged`,
  or the no-previous-hull note. Verify: skill-added-upstream, skill-dropped-upstream, legend, nothing-changed,
  old-refs-unresolvable, and the dry run prints the same.

## 7. Docs

- [ ] 7.1 `docs/design.md`: the Skill tool form (call form only), code blocks counting, `false` **Binds**, the
  lock format (edge kind plus `bind` flag), `build` and `update` writing the lock, the `cargo tree` output.
  Verify: `pre-commit run --all-files` green.
