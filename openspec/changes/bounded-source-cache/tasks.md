# Tasks

Apply with the `mp-tdd` skill: each task red-green-refactor, one commit. `pre-commit run --all-files` stays green; new
words go into `.cspell.yaml`, sorted.

Commits differ from the tasks where a task alone could not pass the hooks: `compute._folder`'s line of 2.1 landed with
2.2; the order was 3.2, 5.1, 3.1, 3.3, as blobless clones need the batched fetch and the overlay first; 5.1's end-to-end
dry-run test is in 3.1's commit; and review fixes to the stamp, the pin and the lock scope are folded into 6.1, which
last touched those lines.

## 1. Seams

- [x] 1.1 `tests/conftest.py`'s `Upstream` sets `uploadpack.allowFilter` to `true` (nothing else: protocol v2 serves
  blobs by oid without `allowAnySHA1InWant`), with a `filters=False` switch to leave it unset. The whole suite passes
  unchanged (no behavior uses it yet)
- [x] 1.2 `git.run` sets `GIT_NO_LAZY_FETCH=1` whenever it names a repository. Test in `tests/infra/test_git.py`: in a
  blobless clone of a filtering `Upstream`, `git.run("cat-file", "-e", f"{sha}^{{commit}}", repo=…)` for a commit pushed
  after the clone fails and the clone still lacks it (`rev-list` from a separate, unpatched call). Verify red (clone
  made by hand with `--filter=blob:none` until 3.1 lands), then green. It, and every later test of a lookup never
  fetching, skips when `git --version` is below 2.44 (a helper in `tests/conftest.py`), as Apple's git on macOS is

## 2. One export per commit and subdirectory

- [ ] 2.1 `Cache.checkout` takes `subdirectory: str | None`; with one, it exports into
  `trees/<key>/<sha>-<12 hex of sha256(subdirectory)>` only the files under it, plus the blob at each proper prefix, as
  design.md says (`--literal-pathspecs`, `-c core.ignorecase=false`, prefix records filtered to exact paths); the
  reference's export is looked up under the same name. `compute._folder` passes `source.subdirectory`. Tests in
  `tests/infra/test_cache.py`: the export of `x` holds `x/…` and no other path; a prefix that is a symlink or a file is
  exported as such, and a sibling of a prefix is not; `*` in a subdirectory matches only itself. Verify red, then green
- [ ] 2.2 `tests/cli/test_subdirectory.py`: `test_shared_export` asserts two exports, each holding only its own
  subdirectory, per the changed **Shared export** scenario; a new **Same subdirectory** test asserts one. The existing
  **Missing at ref**, **A file, not a folder**, **Symlinked subdirectory** and **Case differs** tests pass unchanged,
  with today's messages. Verify the changed test fails first
- [ ] 2.3 `docs/design.md:25`: one export per commit and subdirectory. Verify `why` on a subdirectory **Source** in
  `tests/commands/test_explain.py` still prints an upstream folder that exists, and the lock's `upstream` is unchanged
  (an existing lock test, unchanged, passes)

## 3. Blobless clones and the batched blob fetch

- [ ] 3.1 `_clone` adds `--filter=blob:none`; every clone and fetch passes `--recurse-submodules=no`. Tests: a blobless
  clone of an upstream with a gitlink and `.gitmodules`, with `fetch.recurseSubmodules=yes` in the test's git
  environment, fetches a new commit without error or warning; after `fetch` from a filtering upstream, the repository
  holds no blob (`rev-list --objects --missing=print --all` marks every blob missing), nor after a second `fetch` of a
  new commit; with `Upstream(filters=False)` the clone is whole and `checkout` works (scenario **Remote without partial
  clones**); a repository cloned whole by hand (`seed`) stays whole across a `fetch` (scenario **Repository cloned whole
  before**). Verify red, then green
- [ ] 3.2 Before exporting, `checkout` lists the missing blobs with one `rev-list --objects --missing=print --no-walk`
  over the subdirectory and the prefixes that are blobs, and fetches them in one
  `-c fetch.negotiationAlgorithm=noop fetch --stdin origin` with `git.FSCK`, inside one `lock(repo)` block that never
  calls `fetch()`, as design.md's lock scope says. Tests: exporting 20 files of a subdirectory runs one blob fetch,
  carrying `negotiationAlgorithm=noop`, and no `cat-file --batch-check` (record `git.run` calls by patching it through
  its module); a symlinked prefix's blob, missing, is fetched in that same request; blobs outside the subdirectory, and
  older versions of those in it, stay missing (scenario **One subdirectory of a monorepo**); with the upstream folder
  removed, a commit in the cache whose files are not fails naming the alias and URL (scenario **Commit cached, files
  not**); an export removed by hand re-exports with the upstream removed (scenario **Pruned export read offline**).
  Verify red, then green
- [ ] 3.3 When the blob fetch fails with a refusal by name (`unadvertised object`, `not our ref`), and only then,
  `checkout` runs `fetch --refetch --no-filter` of every branch with `git.FSCK`, lists the missing blobs again, unsets
  `remote.origin.partialclonefilter` only when none is left, and exports; on git before 2.36 it fails saying it needs
  git 2.36. Tests: an `Upstream` cloned and fetched with `-c protocol.version=0` (set through
  `GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_0`/`GIT_CONFIG_VALUE_0` in the test's environment) vendors the skills, the
  repository then holds every blob, and a later `checkout` of a new commit runs no fetch by oid (scenario **Remote
  refusing files by name**); with the upstream removed, the command fails naming the alias and URL, no refetch runs and
  the filter is still recorded (scenario **Files unreachable for a moment**); a refusal for blobs the refetch does not
  bring either fails and leaves the filter recorded. Verify red, then green
- [ ] 3.4 The missing-object message no longer says to delete the folder, as design.md says. Adapt
  `test_missing_object_is_reported`: the blob deleted and the upstream removed, the error names the alias and the blob,
  and holds no `delete`. Verify red, then green
- [ ] 3.5 `tests/commands/test_update.py`: scenario **Old ref cached, its files not** (a fresh cache and a lock already
  pointing at A, then `update`: the diff shows A → tip), **Old ref's files unreachable** (A's commit cached, its files
  not, the tip exported, the upstream removed: `no previous hull to compare` naming the fetch, exit 0), and **Old ref
  not cached** still fetching nothing with a blobless repository. `tests/infra/test_cache.py`: scenario **Ref gone
  upstream** with an upstream that still serves the orphan by oid (`uploadpack.allowAnySHA1InWant`) fails, and the
  repository still lacks the commit. Verify red where behavior changes, then green. `_previous`' docstring as design.md
  says. `docs/design.md`: blobless clones, the first export of a commit and subdirectory needs the remote

## 4. Pins

- [ ] 4.1 `checkout` on a `Cache` without a `reference` pins on every call, without `lock(repo)`:
  `rev-parse --verify -q refs/skill-graft/<sha>`, then `update-ref` only when absent; best effort, as design.md says.
  Tests: after `checkout`, the ref exists; after `checkout` of an export that already existed, too; a second `checkout`
  runs no `update-ref`; `checkout` returns a surviving export when its repository was deleted, and when the repository
  lacks the commit, running no clone or fetch; `checkout` returns while another thread holds `lock(repo)`; scenario
  **Ref vanished upstream** end to end in `tests/cli/test_git_build.py` (build at A, reset the upstream branch to an
  orphan commit and `gc --prune=now` it, `fetch` the cache repository, run `git gc --prune=now` in it, remove the
  export, remove the upstream: `build` vendors the same files). Verify the end-to-end test fails without the pin, then
  green

## 5. The dry run's overlay

- [ ] 5.1 A `Cache` with a `reference` whose repository has the commit but lacks an export's blobs makes an overlay
  repository under its own root (`init --bare` with the reference's object format, alternates, the promisor config
  copied) and fetches the blobs into it, as design.md says; it pins nothing. Test in `tests/infra/test_cache.py`: the
  real repository's objects, refs and config and the real `trees/` are byte-identical before and after a
  reference-layered `checkout` that needed blobs; the export is complete; no clone ran (record `git.run` calls). Also
  with a SHA-256 upstream. `tests/commands/test_update.py`'s dry-run tests (**Dry run**, **Dry run with a diff file**:
  cache folder unchanged) pass. Scenario **Dry run, remote refusing files by name** with a `protocol.version=0`
  upstream: exit non-zero naming `mp` and `update` without `--dry-run`, no refetch, cache folder unchanged. Verify red,
  then green

## 6. Stamp and prune

- [ ] 6.1 `checkout` stamps the export folder's mtime when `reference is None`; `cache.prune(root, now)` removes, older
  than 30 days, each `trees/<key>/<entry>` (exports and `.tmp` leftovers) and each `repos/*.tmp`, by rename then
  `rmtree`, ignoring every `OSError`; never a `trees/<key>` folder, never a repository. Tests in
  `tests/infra/test_cache.py`, ages set with `os.utime`: 31 days removed, 29 kept, a `.tmp` leftover in `trees/` and one
  in `repos/` of 31 days removed (scenario **Clone leftover removed**), a repository of 31 days kept (scenario **Unused
  repository**), the emptied `trees/<key>` kept, a symlink inside an export is removed and its target is not, a
  reference-layered `checkout` leaves the real export's mtime alone, a prune racing a vanished entry raises nothing, a
  prune of a cache root that does not exist, or has no `trees/` or `repos/`, raises nothing. Verify red, then green
- [ ] 6.2 `cli._main` calls `cache.prune(paths.cache(), time.time())` after every command but `init` and `help`, on
  success and on `SkillGraftError`/`OSError`, not after `update --dry-run`. End to end in a new
  `tests/cli/test_cache.py`, one test per scenario of **Exports prune themselves**: **Stale export removed**
  (`resolve`), **Export in use kept** (`build`), **Recent export kept**, **Failed command prunes too** (a failing
  patch), **Leftover removed**, **Dry run prunes nothing** (mtime unchanged too); and `resolve` with only path
  **Sources** on an empty `XDG_CACHE_HOME` exits 0. `infra.cache` is imported inside `_main`, beside the command
  modules; `tests/cli/test_cli.py`'s native-Windows tests pass unchanged. Verify red, then green
- [ ] 6.3 `README.md`: a "Cache" section (where it is; exports unused for 30 days removed by any command; repositories
  never removed, every **Ref** read kept in its repository; deleting one by hand, or the folder, is safe unless a
  **Ref** has vanished upstream), and in "Installation", beside the Python requirement, the git versions: 2.44 or later
  keeps lookups offline (macOS's own git is older; Homebrew's is not), 2.36 or later is needed for a remote refusing
  files by name. `docs/design.md`: pins, pruning, and "Deleting it loses nothing" with that caveat. A test for scenario
  **Ref vanished, then cache deleted** in `tests/cli/test_git_build.py` (reset the upstream branch, delete the cache,
  `build` fails naming alias and `ref`). Verify the README passes the markdown hooks and the test passes

## 7. Integration

- [ ] 7.1 Full suite, `uv run mypy .`, `lint-imports` green, and the CI `test-macos` job green on the draft pull request
  (APFS, BSD tools, the runner's git); by hand, against a real GitHub monorepo with `subdirectory`, in a temporary
  `HOME`: `build`, then `du -sh` of the cache is a fraction of a full clone, a second `build` with the network off
  succeeds, and `update --dry-run` leaves the cache folder byte-identical
