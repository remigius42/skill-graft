# Proposal

## Why

The git cache only grows. Every commit read gets a full export under `trees/<key>/<sha>`, nothing ever deletes one, an
export holds the whole repository even when a **Source** reads one `subdirectory`, and a clone downloads every blob of
every branch's history. For a monorepo that is a lot of disk, network and, while exporting, memory, and the user has no
way to reclaim it short of deleting the cache folder by hand, which the docs say "loses nothing", not quite true.

## What Changes

- **Exports prune themselves.** Each command that reads through the cache stamps every export it uses; at its end,
  success or failure, it removes every export, and every leftover of a killed run, unused for 30 days. No setting. A
  `--dry-run` neither stamps nor prunes the real cache. Exports are derived: one pruned is exported again, locally, when
  next needed.
- **Every Ref read is pinned, and repositories are never deleted automatically**, nor by any command. Today a
  force-pushed branch loses its old commit to `fetch --prune` and git's `gc`; a pin, a ref of skill-graft's own in the
  repository, keeps each commit read, with its trees and fetched files, so the repository holds the only copy of a
  **Ref** that has since vanished upstream. The README gets a short section on the cache (where it is, what prunes
  itself, what deleting a repository by hand costs); the spec and `docs/design.md` drop "deleting the cache loses
  nothing" for that caveat, and the `object … is missing` error stops telling the user to delete the repository.
- **One export per commit and subdirectory.** A **Source** with `subdirectory` exports only that folder of the tree
  (plus the entries on its path, so a symlink or file there is still refused as today), in a folder of its own beside
  the commit's. Two **Sources** of one URL and **Ref** with different subdirectories get two exports, no longer one. The
  lock's `upstream` paths, relative to the **Source**'s root, do not change.
- **Blobless clones.** A new clone takes `--filter=blob:none`, and its fetches follow: commits and trees only. Before an
  export, the blobs it needs that the repository lacks are fetched in one batch, under the repository's lock, with the
  same fsck as any fetch; no git command skill-graft runs fetches anything lazily. Existing full clones stay as they
  are. A server without filter support gives a full clone, as today; one that accepts the filter but refuses files by
  name (an old protocol) has the repository fetched whole, once, and works from then on; a dry run there says to run
  `update` without `--dry-run` instead. A network failure never converts a repository. Lookups never fetching needs git
  2.44, the whole-fetch fallback git 2.36; the README says so.
  - Visible: the first export of a commit and subdirectory needs the remote, even when the commit is in the cache. An
    export pruned and exported again does not: its blobs stay in the repository.
- **Pruning also removes leftovers of killed clones**: a `.tmp` beside the repositories, 30 days old.
- **`update --dry-run`** still writes nothing to the real cache: blobs the real repository lacks go into an empty
  repository of its own in its temporary folder, reading everything else from the real one.
- **`update`'s Hull diff** may fetch the files of a current **Ref** whose commit is cached (never a commit): without
  that, a blobless clone on a fresh machine would lose the diff it shows today.

Not in scope: streaming `_read_blobs` (an export now holds one subdirectory, so its memory is bounded by that); fetching
fewer branches (a **Ref** may be on any branch); a setting for the 30 days; a command to clean the cache.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `git-sources`: the cache requirement (exports prune themselves, repositories are kept and keep every **Ref** read,
  deleting one by hand can lose a vanished **Ref**); reading at the **Ref** (contacting the remote for blobs a commit in
  the cache lacks, never for a commit outside `fetch`); one export per subdirectory (the **Shared export** scenario
  changes); fetching only what is read, with the fallbacks for remotes that cannot.
- `update`: the **Hull diff** still never fetches a commit, but fetches the files of a cached current `ref` it lacks, so
  a lock written on another machine still gets its diff; a failure there is reported as no previous **Hull**. A dry run
  on a remote refusing files by name fails, saying to run `update` without `--dry-run`.

## Impact

- `src/skill_graft/infra/cache.py`: blobless clone, the batched blob fetch and its whole-refetch fallback, pins,
  subdirectory exports and their folder name, the stamp, `prune`, the dry run's overlay repository, the missing-object
  message.
- `src/skill_graft/infra/git.py`: `run` sets `GIT_NO_LAZY_FETCH=1` whenever it names a repository.
- `src/skill_graft/pipeline/compute.py`: `checkout` takes the subdirectory.
- `src/skill_graft/cli.py`: prunes, through a new `commands/housekeeping.py`, after every command but `init` and `help`,
  and not after `update --dry-run`; imports it inside `_main`, as it does the other commands, so native Windows is still
  refused before `fcntl` loads.
- Tests: synthetic upstreams allow filters; `tests/infra/test_cache.py` gains pruning, pinning, subdirectory, blobless
  and fallback tests; `test_shared_export` and `test_missing_object_is_reported` change.
- `README.md` (a cache section), `docs/design.md`, `CHANGELOG.md`. `CONTEXT.md` unchanged.
