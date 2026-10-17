# Tasks

Apply with the `tdd` skill: each task red-green-refactor (failing test first, then code), one commit, and
`pre-commit run --all-files` green. New words go into `.cspell.yaml`. Tests set `HOME` to `tmp_path` and build
synthetic **Skills**, patches (written with `diff -ruN` or `git diff` in the test) and git repositories.
`[patches]` stays an unsupported config key until 2.1 honors it end to end, so no commit accepts intent it
ignores.

## 1. Applying a patch

- [ ] 1.1 `git.apply(folder, patch)`: `git -c apply.ignoreWhitespace=no apply -p1 --reject --whitespace=nowarn -`
  in `folder`, user, system and `GIT_CONFIG*` environment config off, `GIT_CEILING_DIRECTORIES` at the parent,
  `(ok, stderr)` back, a missing `git` naming `[patches]`. Verify: unit tests for applies, context-moved,
  anchored-at-the-start, config-in-the-environment, user-git-config (a `GIT_CONFIG_GLOBAL` file setting
  `apply.whitespace = fix` and `apply.ignoreWhitespace = change` changes nothing), enclosing-repository (the folder
  inside a git work tree), no-git.
- [ ] 1.2 `patch.apply(skill, upstream, files, work)`: copy without `.git`, following symlinks; apply in order;
  failures from new `.rej` files (target file, `@@` headers) or git's stderr when there is none, later patches not
  tried (`PatchFailed`); `SKILL.md` kept, name unchanged and `check_files` passing on the copy, else `PatchFailed`.
  Verify: unit tests for patch-changes-the-text, patches-in-order, patch-to-a-sibling-file, diff-of-two-folders,
  every-failing-hunk-named, patch-refused-whole, later-patch-not-tried, upstream-ships-a-reject-file, name-changed,
  name-added, SKILL.md-deleted, path-outside-the-skill, mode-change, source-is-a-repository, upstream-unchanged.

## 2. Patches in the hull

- [ ] 2.1 `[patches]` end to end: `Config.patches` (`PatchFile`, paths against the config's folder, bytes read at
  load, `Binary files … differ`, `Only in` and `GIT binary patch` lines, duplicates by resolved path); `walk`
  patches before the scan, `Hull.upstream` and `Hull.patches`; `resolve.resolve(..., work)` with the temporary
  folder opened in `cli` and `update` (existing callers and tests pass one). Verify: config scenarios
  (valid-patches, value-not-a-list-of-paths, undeclared-alias-in-a-patch, missing-patch-file, listed-twice,
  shared-patch, patches-table, binary-change, added-file-without--N), patch-adds-a-reference,
  patch-removes-a-reference, rename-on-top, symlink-leaving-the-skill, symlink-within-the-skill,
  upstream-checked-first, build-writes-nothing, no-git, path-sources-without-patches, and every existing test.
- [ ] 2.2 Failures collected: `walk` records `PatchFailed` with the **Upstream** folder, skips that **Skill**'s
  scan, raises one `PatchError` after the BFS naming each failure and "redo it against" and the **Upstream**
  folder, or with another walk error last; `patch.unused` warns on keys naming no **Hull** **Skill**. Verify:
  context-changed, two-skills-fail, another-error-after-a-patch-failure, reached-only-through-a-failed-skill,
  patch-outside-the-hull, unlisted-file.

## 3. Lock and tree

- [ ] 3.1 `lock.render`: `upstream` on every **Skill**, `patches` in apply order on a patched one. Verify:
  upstream-recorded, patches-recorded, patch-changes-the-hash, resolve-and-build-agree-with-patches, same-input.
- [ ] 3.2 `lock.tree`: `(patched)` after the name and any `as <name>`. Verify: patches-marked, and the tree,
  renames-marked and bound-prose-shown scenarios unchanged.

## 4. Update

- [ ] 4.1 `update`: a `PatchError` at the tips leaves TOML and lock as they are and names the tip's **Upstream**
  folder; in a dry run, one under the temporary cache says to run without `--dry-run`; `_previous` reports
  "patches fail at the current refs". Verify: patch-fails-at-the-tip, patch-redone,
  dry-run-with-a-failing-patch, patch-already-rewritten-for-the-tip.

## 5. Docs

- [ ] 5.1 `docs/design.md` (§ Patches as built, the lock's `upstream` and `patches`, the tree's `(patched)`),
  `README.md` (patches built, the recipe for writing one). Verify: the recipe in the README, run by hand on a
  synthetic **Skill**, gives a patch `build` applies; `pre-commit run --all-files` green.
