# Tasks

Apply with the `tdd` skill: each task red-green-refactor (failing test first, then code), one commit, and
`pre-commit run --all-files` green.

## 1. Test support

- [x] 1.1 `conftest`: unset `XDG_CACHE_HOME` and `XDG_CONFIG_HOME`, point `GIT_CONFIG_GLOBAL` at an empty file,
  set `GIT_CONFIG_NOSYSTEM=1` and `GIT_AUTHOR_*`/`GIT_COMMITTER_*`; add an `upstream` helper (`git init -b main`,
  optional SHA-256, commit fixture skills, return shas; URL = its absolute path); make `fake_apm` link the real
  `git` beside the fake `apm`. Verify: a test commits twice and reads both shas, a SHA-256 upstream gives
  64-digit shas, and `git` runs under `fake_apm`.

## 2. Config

- [x] 2.1 `Source = PathSource | GitSource`; exactly one of `path`/`git`; `branch`/`ref` only with `git`;
  string types; `git` an allowed-scheme URL, scp-like or absolute path (relative, `~`, leading `-`, other schemes,
  `<transport>::` rejected);
  `ref` 40 or 64 lowercase hex; `branch` not empty, `refs/…` or `-…`; `tag` and other keys still unsupported.
  Callers use `PathSource.folder`. Verify: every `config` delta scenario passes, existing config tests still
  pass.

## 3. Cache and checkout

- [x] 3.1 `paths.cache()` (`XDG_CACHE_HOME` if absolute, else `~/.cache/skill-graft`) and the URL key
  (trailing `/` and `.git` stripped, `repo` if empty). Verify: default-location, shared-URL and key unit tests.
- [ ] 3.2 `git.py`: runner (no prompt overrides, stdin inherited, `transfer.fsckObjects`, error wrapping, `--`
  before URLs), repository by `clone --bare` into a temporary name (leftover deleted first) then renamed, fetch
  all branches with `--prune`, once per URL per command, has-commit. Verify: git-missing, unreachable-remote,
  shared-URL-fetched-once, interrupted-clone and SHA-256-remote scenarios.
- [ ] 3.3 `checkout(source, ref)`: reuse an existing export, else fetch only when the commit is missing,
  ref-not-found error, export via `ls-tree -r -z` and `cat-file --batch` into `<sha>.tmp` (leftover deleted
  first; modes 100644, 100755, 120000; submodules skipped), then rename. Verify: upstream-moved-on (remote not
  contacted when cached), fresh-machine, cache-deleted, ref-gone, interrupted-checkout, attributes-ignored and
  modes-kept scenarios.

## 4. Build

- [ ] 4.1 Split `vendor` into `resolve` and copy-and-swap; add `folders(config, cache, refs)`; `build` fails
  on any git source without `ref` before writing. Verify: skill-from-git, new-git-source and every existing
  build test pass.

## 5. Update

- [ ] 5.1 Add `tomlkit`; `update [alias…]` CLI: selection errors (path source, unknown alias, unselected
  source without `ref`, `check-ref-format --branch`) before any remote is contacted; tip from one `ls-remote`
  per URL and branch (`--symref HEAD` without `branch`; no sha line → no-default-branch error); fetch only when
  the tip is not cached; print lines. No TOML write yet. Verify: path-source-named, unknown-alias,
  other-source-without-a-ref, revision-syntax-as-branch, missing-branch, branch-deleted-upstream,
  no-default-branch, tip-already-cached and output scenarios.
- [ ] 5.2 Resolve at the new tips; on success write `ref` via tomlkit (trivia kept, symlink target written,
  atomic replace, skipped when unchanged). Verify: new-commit, named-branch, default-branch-renamed,
  source-without-a-ref, only-named, entry-gone, no-deploy, comments-survive, symlinked-config and nothing-new
  scenarios.
- [ ] 5.3 `--dry-run`: temporary `Cache` reading the real one (existing export, else export from the real
  repository, else clone with `--reference-if-able` and fetch, all into the temporary folder); "not written"
  message. Verify: the three dry-run scenarios, asserting TOML bytes and a recursive snapshot of the cache
  folder are unchanged.

## 6. Init and docs

- [ ] 6.1 `init` template documents `git`, `branch`, `ref` and `skill-graft update`. Verify: the
  template-shows-a-git-source scenario and fresh-home still pass.
- [ ] 6.2 Real-APM integration test with a git source (`init`, `update`, `build`), skipped without `apm`;
  update `docs/design.md` (`update` writes only after resolution succeeds; cache location), `README.md`
  status, and `.cspell.yaml` words. Verify: `pre-commit run --all-files` green.
