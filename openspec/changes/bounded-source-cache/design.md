# Design

## Context

See proposal.md for why. `infra/cache.py` holds the cache: `Cache.fetch` clones (`--bare --no-local --no-tags`, fsck on)
or fetches every branch (`--prune`) under a per-repository `flock`; `Cache.checkout(alias, url, ref)` returns
`trees/<key>/<sha>`, exporting the whole tree with one `ls-tree -r` and one `cat-file --batch` into a temporary sibling
renamed into place, so a tree folder's existence means it is complete. `pipeline/compute.py` then takes `subdirectory`
of that tree, checking each part is a real folder of exactly that name (`_subdirectory`). Exports are read without a
lock: `checkout` returns a path that discovery and vendoring read later. `update --dry-run` layers `Cache(tmp, real)`
over the real cache: it reads the real repositories and exports, writes only under `tmp`. Every command builds its
`Cache` itself (ADR 0008); only `cli._main` sees every command end.

Spikes on git 2.55 showed:

- In a blobless clone, any git command that looks up a missing object fetches it from the remote on its own, one round
  trip each: `cat-file --batch` over 50 missing blobs ran 50 fetches, and `cat-file -e <sha>^{commit}` fetched a commit
  the cache lacked. `GIT_NO_LAZY_FETCH=1` stops both; explicit fetches still work under it.
- `rev-list --objects --missing=print --no-walk <tree>` lists the objects under that tree, missing ones marked `?`,
  without fetching, on git 2.39, 2.55 and 2.56. With a pathspec instead (`<ref> -- <subdirectory>`) it lists nothing at
  a commit that does not touch the subdirectory, on 2.39 and 2.56 (2.55 lists it); given a missing blob's oid, 2.39
  fails with `bad object`.
- `fetch --stdin origin` given blob oids fetches them in one request; it, like the lazy fetches, runs
  `index-pack --fsck-objects`.
- A server without `uploadpack.allowFilter` warns and serves a full clone. A protocol v0 server that allows filters but
  not `uploadpack.allowAnySHA1InWant` serves the blobless clone, then refuses the blobs by oid ("unadvertised object");
  `fetch --refetch --no-filter` makes the repository whole.
- `fetch --prune` with `+refs/heads/*:refs/heads/*` drops the ref of a force-pushed branch, and in a repository cloned
  whole `gc` then deletes the commit. A partial clone's `gc` keeps it, as git never prunes promisor packs, but a clone
  with `--filter` is one only by git's choice, and whole clones remain (cloned before, or converted). A ref outside
  `refs/heads/` keeps it, and the blobs fetched for it, through both, in either.
- An empty bare repository with `objects/info/alternates` pointing at another's objects and the promisor config copied
  fetches blobs by oid into itself, leaving the other untouched.

## Goals / Non-Goals

**Goals:**

- Disk bounded by what was used in the last 30 days, plus the repositories.
- A monorepo **Source** costs its commits, trees and one subdirectory's blobs, not every blob of its history.
- A **Ref** once read stays readable from the cache, whatever happens upstream, until the user deletes its repository.
- No behavior change for a user who never waits 30 days, beyond the first export of a subdirectory needing the remote.

**Non-Goals:**

- Bounding the repositories, and the commits and trees of every branch in them; pins only add to them.
- Streaming blobs into the export: one subdirectory's blobs are held in memory at once, as one tree's are today.
- A lock against pruning an export another run is reading (see Risks).

## Decisions

### Export folder per commit and subdirectory

`checkout(alias, url, ref, subdirectory)` exports into `trees/<key>/<sha>` without a subdirectory, as today, and into
`trees/<key>/<sha>-<12 hex of sha256(subdirectory)>` with one, holding `<subdirectory>/…` at its path. It still returns
the tree folder, and `compute` still applies `_subdirectory` to it, so the **Source**'s root, the lock's `upstream`
paths and `why` relative to the root are unchanged; only the absolute folder `why` prints moves.

- Each folder stays complete for what its name claims, so the rename-into-place marker still works and concurrent runs
  still converge on one export.
- Alternative: export subdirectories into the shared `<sha>` folder. Its existence would no longer mean complete: a
  second **Source** with another subdirectory would find it present and its own files missing, and nested subdirectories
  (`a`, `a/b`) would need per-path markers. Rejected for a few duplicated files in the nested case.
- Alternative: hash-free `<sha>/<subdirectory>` nesting: same completeness problem one level down.

### Listing only the subdirectory

The export lists `ls-tree -r -z --full-tree <ref> -- <subdirectory>`, plus the blob, if any, at each proper prefix: a
non-recursive `ls-tree -t -z --full-tree <ref> -- a a/b a/b/c` for `a/b/c`, keeping only the records whose path is
exactly one of those, since for a prefix that is a folder git lists its children (`a/sib`) too. `-t` lists the trees on
the way as well, which the missing-blob listing below starts from. A prefix that is a symlink or a file is then exported
as such, and `_subdirectory` refuses it with today's message (`runs through a symlink`, `is not a folder`) instead of
`does not exist`. Both run with `--literal-pathspecs` and `-c core.ignorecase=false`, so a name holding `*` matches
itself and `PStack` never matches `pstack`, on any file system: a clone on macOS's APFS, which ignores case, records
`core.ignorecase=true`, and git's pathspecs would follow it. A prefix that is a folder adds nothing to write; the
existing hostile-path guards (`_safe`, the real-parent check, symlinks last) apply unchanged.

### No git command fetches lazily

`git.run` sets `GIT_NO_LAZY_FETCH=1` on every call that names a repository, not only on the export's: in a blobless
clone, `has_commit`'s `cat-file -e` would otherwise fetch a missing commit by oid, outside `fetch`, its lock and its
fsck, break "never fetch a commit" in the **Hull diff**, let **Ref gone upstream** pass on a server that still serves
the orphan, and write into the real repository from a dry run. Explicit fetches are unaffected. Every object skill-graft
needs from the remote then comes from `fetch`, the batched blob fetch, or the fallback below, all under `lock(repo)`
with `git.FSCK`. Clone, which names no repository, needs none. Every fetch, clone included, passes
`--recurse-submodules=no`, as git's own promisor fetch does: a blobless repository holds no `.gitmodules` blob for the
user's `fetch.recurseSubmodules` to read, and lazy fetches are off. `GIT_NO_LAZY_FETCH` is git 2.44+; on older git a
lookup may still fetch lazily, slower and outside the lock, but correct. The spec's "never contacts the remote" is
scoped to git 2.44 or later, and the README names both versions this change relies on (2.44, and 2.36 below).

### Blobless clones; existing clones untouched

`_clone` adds `--filter=blob:none`. `fetch` adds nothing: in a partial clone git applies the remote's recorded filter
(`remote.origin.partialclonefilter`) itself, and an existing full clone keeps fetching blobs, so no migration and no
mixed state to handle.

### One batched blob fetch before the export

Before `cat-file --batch`, the export lists the blobs it lacks with
`rev-list --objects --missing=print --no-walk <trees…>` (`?` lines), which fetches nothing on any git, and keeps only
the missing oids the export's own records name. The trees, which a blobless repository always has, are the
subdirectory's own (the commit, without a subdirectory) and, for each file or symlink the listing above found on the
path, the folder holding it: no pathspec, which some git versions apply as history simplification even under
`--no-walk`, and no blob oid, which old git refuses when missing. A holding folder's siblings are listed, never fetched;
it walks local trees only, in the error cases where `_subdirectory` refuses the path. The listing above takes
`ls-tree -t`, so the trees on the path come with their oids. If any blob is missing, it runs, under `lock(repo)`,
`fetch --stdin origin` with those oids on stdin, `git.FSCK`, `-c fetch.negotiationAlgorithm=noop`,
`-q --no-tags --no-write-fetch-head`, `--recurse-submodules=no` and `--filter=blob:none`: `noop`, as git's own lazy
fetch does, since the want list is blobs and negotiating `have`s over every branch would only cost round trips. Its
failure names the alias and URL as a fetch's does. A blob still missing after it hits the `object … is missing` error.

**Lock scope**: `checkout` lists the missing blobs first under no lock, so an export whose files are at hand never waits
behind another run's clone or fetch. Only when some are missing does it take `lock(repo)`, once, around listing them
again (another run may have fetched them meanwhile), the blob fetch and the refetch fallback, and it never calls
`fetch()` while holding it: `lock` is an `flock` on a newly opened file, so taking it again in the same process would
wait forever. A missing commit is fetched (`fetch()`, its own lock) before that block. The export itself reads under no
lock, as today; the pin takes none (below).

- Alternative: let `cat-file --batch` fetch lazily. One round trip per blob, measured; rejected.
- Alternative: find the missing blobs with `cat-file --batch-check`: on git before 2.44 that lookup is itself the lazy
  fetch, blob by blob, outside the lock. Rejected for `rev-list --missing=print`, which never fetches.
- Alternative: `git backfill` (2.49+). Batches by path, but too new to require.

### A remote that refuses blobs by oid: refetch whole

Only when the batched blob fetch fails with the server's refusal of an object asked by name (git's
`Server does not allow request for unadvertised object` on protocol v0, `not our ref` on v2; git gives no distinct exit
code), as a v0 server without `uploadpack.allowAnySHA1InWant` that accepted the filtered clone does, the repository is
converted, under the same lock:
`fetch --refetch --no-filter --no-tags --recurse-submodules=no origin '+refs/heads/*:refs/heads/*'` with `git.FSCK`
downloads every branch whole. Then the missing-blob listing runs again: only if it finds none is
`remote.origin.partialclonefilter` unset, so later fetches stay whole, and the export goes on. Any other failure (the
network, credentials) fails the command naming the alias and URL, and leaves the repository as it was. When the refetch
fails, or leaves blobs missing (the refusal was for files the server no longer has, as at a pinned **Ref** that vanished
upstream), the command fails too, and the filter stays recorded. Pins and the objects they keep are local, so a vanished
**Ref** survives the conversion. `--refetch` is git 2.36+; on older git the fallback fails saying it needs git 2.36.

- Alternative: detect v0 at clone time. Git exposes no reliable signal; the failure is what tells.
- Alternative: re-clone whole and swap. Would lose pins of vanished **Refs**; rejected.

### Pin each commit read

`checkout` on the real cache (`reference is None`) pins the commit it read:
`rev-parse --verify -q refs/skill-graft/<sha>` first, and only when that ref is absent,
`update-ref refs/skill-graft/<sha> <sha>` in the repository. Neither takes `lock(repo)`: `update-ref` takes git's own
lock on that one ref, and two runs pinning the same commit write the same value, so the pin never waits behind another
run's clone or fetch. The pin is outside `refs/heads/`, so `fetch --prune` never touches it, and it keeps the commit,
its trees and every blob fetched for it through `gc`. Every checkout, not only an export: exports made before this
change are stamped and reused, and would otherwise never be pinned. A dry run pins nothing.

Pinning is best effort: when the repository is missing (the user deleted it, its export survived) or lacks the commit (a
re-clone after a **Ref** vanished upstream), `checkout` skips the pin and returns the export, as today; it never clones
or fetches just to pin, and a failing `update-ref` fails nothing.

- Alternative: keep the repository and trust it ("may hold the only copy"): `gc --auto`, which fetch runs, deletes the
  unreachable commit after `gc.pruneExpire`; the review showed the promise empty without a pin.
- Cost: one `rev-parse` per git **Source** per command, an `update-ref` the first time, and the pinned commits forever;
  small next to a clone.

### The dry run fetches blobs into an overlay of its own

`_repository_with` may return the real repository to a dry run. When the export's blobs are missing there, a `Cache`
with a `reference` does not fetch into it, nor clone: it makes `repos/<key>.git` under its own root with
`git init --bare --object-format=<the real one's>`, `objects/info/alternates` naming the real repository's objects, and
`remote.origin.url`, `remote.origin.promisor`, `remote.origin.partialclonefilter` and `extensions.partialClone` copied;
then runs the batched blob fetch into it and exports from it. No ref advertisement, negotiation or connectivity check of
every branch, as a borrowing clone would cost on every dry run. When the commit is missing from the real repository too,
the dry run still clones its own as today. The reference's exports are still used when present, under the
subdirectory-aware name.

The overlay never runs the refetch fallback: refetching every branch into a temporary folder on each dry run would cost
a full download each time. When its blob fetch is refused by name, the dry run fails, its error saying to run `update`
without `--dry-run`, as `_fetch_hint` says for a patch failing at a tip it could not fetch; `update` then converts the
real repository once.

- Alternative: let the dry run fetch blobs into the real repository (additive, content-addressed, fsck'd). Rejected to
  keep "`--dry-run` writes no cache" exact.

### Hull diff: commit check unchanged, files fetched

`update._uncached` keeps checking commits only (`has_commit`, now never fetching), so a missing commit is still reported
with its likely causes and never fetched. A cached commit whose files are missing goes through `checkout`, which fetches
the blobs; a failure there is already caught by `_previous` (`the current refs do not resolve: <error>`), which names
the fetch. `_previous`' docstring ("Never fetches: the diff is not worth a remote call") becomes: never fetches a
commit; fetches the files of a cached one.

### The missing-object message

`_read_blobs`' `object … is missing from <repo>; delete that folder and run again` would now send the user to delete a
repository, the one thing that can lose a vanished **Ref**. It says instead that the remote did not send the object, and
no longer advises deleting anything:
`object <oid> is missing from <repo>, and fetching it did not bring it; see "Cache" in the README`.

### Stamp and prune

- **Stamp**: `checkout` sets the export folder's mtime to now (`os.utime`) each time it returns one, only when
  `self.reference is None`: a dry run neither stamps the real cache nor needs to stamp its own. Folder mtime and not
  atime: `relatime`/`noatime` make atime unreliable, and nothing else changes an export folder's mtime once placed.
- **Prune**: `cache.prune(root, now)` removes, when its mtime is over 30 days old, each `trees/<key>/<entry>` (exports
  and `.tmp` leftovers alike) and each `repos/*.tmp` (a clone killed mid-run: garbage, never a repository holding a
  pin). It renames the entry to a fresh `.tmp` sibling (`_temporary`'s naming) and removes it with `shutil.rmtree`,
  which does not follow symlinks. It never removes a `trees/<key>` folder, even empty: a concurrent export runs
  `mkdir(exist_ok=True)` then `mkdtemp` inside it, and removing the folder between the two would fail that run; an empty
  folder costs one inode. It never removes a repository. Every `OSError` is ignored, per entry and in listing `trees/`,
  `trees/<key>` and `repos/` (any of which may not exist, as on a machine that never read a git **Source**): a
  concurrent pruner got there first, or a run is holding it, and pruning must never fail a command. A renamed entry
  keeps its old mtime, so one a killed pruner leaves behind is removed by the next.
- **Where**: `cli._main` calls it after the command, on success and on `SkillGraftError`/`OSError`, for every command
  but `init` and `help`, and not for `update --dry-run`. Not on `KeyboardInterrupt`: Ctrl-C should exit at once.
  Alternative: each command prunes its own `Cache`: ten call sites, and `update` would need to know its own dry-run
  state twice. `cli` is the one place that knows a command ended; it calls `housekeeping.prune()`, a command module's
  function calling `cache.prune(paths.cache(), time.time())`, holding no `Cache` (ADR 0008 holds), since `cli` reaches
  `infra` only through `commands`. `_main` imports it in its body, beside the other command modules, never `cli.py` at
  load: `cache.py` imports `fcntl`, and `main` must refuse native Windows before any POSIX-only module loads
  (`state-supported-platforms`); its stand-in test, which blocks `fcntl`, keeps passing.
- 30 days is a module constant, no setting.

### Docs

- `README.md`: a short "Cache" section: where it is; exports unused for 30 days removed by any command; repositories
  never removed, and every **Ref** read stays in its repository even after it vanishes upstream; deleting a repository
  by hand, or the folder, is safe unless a **Ref** has since vanished upstream, which then cannot be fetched again.
- `docs/design.md:25`: one export per commit and subdirectory, blobless, pinned, pruned; "deleting it loses nothing"
  gets the vanished-**Ref** caveat.

## Risks / Trade-offs

- [A run reads an export the moment another run prunes it] → only an export unused for 30 days, and the reader stamps
  before it reads, so the window is the time between the pruner's `stat` and its rename. The reader then fails with a
  missing file; a rerun exports again. Accepted rather than a reader lock across discovery and vendoring.
- [First export of a commit and subdirectory needs the remote] → today only a missing commit does. Specified in
  `git-sources`; an export once made keeps its blobs in the repository, pinned, so a pruned one re-exports offline.
- \[git older than 2.44 ignores `GIT_NO_LAZY_FETCH`\] → the missing blobs are found with `rev-list --missing=print`,
  which never fetches, so the export still makes one request; only other lookups of an object the cache lacks (a missing
  commit) may fetch lazily, slower and outside the lock, still fsck'd by `index-pack`. macOS is supported, and the git
  Apple ships with its command line tools is older (2.39 as of this writing): there that degraded case is the default,
  and the README says a newer git (Homebrew's) keeps lookups offline. Tests of the no-lookup guarantee skip below 2.44.
- \[macOS's temporary folders live under `/var`, a link to `/private/var`\] → tests comparing cache paths (the overlay's
  alternates, `.tmp` leftovers) compare them resolved; the CI job on macOS runs the whole suite.
- [git's refusal messages are matched as text] → a git release that rewords them makes a v0 remote fail with its fetch
  error instead of converting; the test with `protocol.version=0` catches that on the git it runs. `git.run` sets
  `LC_ALL=C`, so a translation never hides them. A network or credential failure never converts.
- \[A refusal for files the server no longer has, as at a pinned **Ref** that vanished upstream, triggers the refetch\]
  → one full download wasted, after which the blobs are still missing, the command fails, and the filter stays recorded;
  never wrong content. Since the filter stays, every later command reading those files downloads the repository whole
  again and fails the same way, until the `ref` changes. Accepted as rare: it needs a commit that vanished upstream,
  read for a `subdirectory` never exported at it before (a commit once read keeps its files), from a remote refusing
  files by name or unreachable ones, as GitHub does.
- [A promisor fetch's prompts (ssh, credentials) now come during an export] → same prompts, same config, as any fetch.
- \[Tests run `file://` upstreams, which serve no filter by default\] → the synthetic `Upstream` sets only
  `uploadpack.allowFilter` (protocol v2 needs nothing else for blobs by oid); one test leaves it off for the whole-clone
  fallback, one runs with `protocol.version=0` for the refetch fallback.
- [The cache grows in repositories and pins still] → by design (proposal: repositories are kept); blobless clones make
  them small.

## Migration Plan

None needed. Old full exports of subdirectory **Sources** are no longer read and age out after 30 days; old full clones
keep working and stay full; commits read before the change are pinned the next time a command reads them. Rolling back
to an older skill-graft: it reads `<sha>` exports, re-exporting the missing ones from a blobless repository through lazy
fetches, slower but correct; it ignores the pins.
