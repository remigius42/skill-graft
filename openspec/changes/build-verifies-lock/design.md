# Design

## Context

Every command that writes the lock goes through `commands/transaction.py`'s `resolving`: it computes the **Hull** inside
`compute.compute_hull`, whose patched copies exist only within that block, yields a `Resolution`, renders the lock
(`lock_text`) before the block closes, then runs the caller's `writes` (the TOML) and writes the lock, restoring each
write in reverse on failure. Only `build` vendors: inside the block it calls `vendor.vendor`, which stages `skills.new`
(after `_recover` undoes a killed swap), swaps it in and deletes `skills.old` at once, then hashes the copies into
`resolution.hashes`. Nothing reads the lock but `update`, for its "edited since" check (`lock.load`, `lock.recorded`).
`update` lists remotes and fetches tips before it enters `resolving`.

`lock.skill_hashes(hull)` hashes each patched folder with its rewrites in place, through `deployed.walk`, which reads a
symlink's target as `vendor` copies it; so it equals `lock.folder_hash` of the **Vendored copy**. The lock records each
**Skill**'s **Deployed name** (`deployed`, when it is not the name) and that hash, which is all the copy check needs. A
path **Source** outside the project root is recorded as an absolute folder, so in project scope a committed lock records
one machine's folder.

Two shipped texts tell the user to `build` where a strict `build` would refuse: `init`'s message when APM fails after
registering (no lock yet), and the `graft-check` skill, whose **Patch** fix edits `[patches]` by hand and then builds
`--into`.

## Goals / Non-Goals

**Goals:**

- `build` deploys only the **Hull** the lock records, but for path **Source** text and folders.
- The lock and `.apm/skills/` are written together by every command that writes the lock, or neither is.
- No command overwrites an edited or unknown **Vendored copy**, and none takes a killed run's copies for one.

**Non-Goals:**

- Diagnosing why a git **Source**'s hash differs (edited TOML, **Patch**, export, or upgrade).
- Read-only cache exports: a later change.
- Checking what `apm install` deploys when run outside skill-graft.
- A lock `version` bump: the layout is unchanged.
- Ignoring stray files (`.DS_Store`, a sync tool's conflict copies) in a **Vendored copy**: they count as edits.

## Decisions

- **`resolving` vendors, after `verify`.** Inside the `compute_hull` block, after the caller's body, while the patched
  copies exist: render `lock_text`, call `verify(lock_text)` if the caller set one, then, given `write`, recover a
  killed run and stage the copies into `skills.new`. A refused `verify` so touches nothing in `.apm/`. After the block:
  the caller's `writes`, the swap (`skills` → `skills.old`, `skills.new` → `skills`), then the lock; on any failure
  there, `BaseException` included, the swap is undone and `skills.new` removed before the TOML is restored, in the
  reverse order of the writes. With no `skills` before, as on a **Package**'s first `resolve`, the swap moves nothing to
  `skills.old`, and undoing it deletes the new `skills`. A failing undo of the swap is a notice naming the folder and
  the error, as a failing `_restore` is, and the TOML is still restored and the original error reported. Only then,
  outside the undo, `skills.old` is deleted best-effort: once the lock is written, nothing undoes it, and a leftover
  `skills.old` is resolved by the next run's recovery. A target `skills` path is a parameter, `scope.skills` by default,
  `<dir>/.apm/skills` for `--into`. `vendor.vendor` splits into `vendor.pending(skills, keep_old)`,
  `vendor.recover(skills, keep_old)`, `vendor.stage(hull, skills)`, `vendor.swap(skills)`, `vendor.swap_back(skills)`
  and `vendor.clear_old(skills)`. Rejected: vendoring in each command, which duplicates the ordering `resolving` exists
  to own.
- **Recovery by the lock, only when writing.** A run killed after the swap leaves `skills.old` beside `skills`, before
  or after the lock was written. `vendor.pending(skills, keep_old)` names, without touching anything, the folder
  recovery leaves as `skills`: `skills.old` alone; with both, `skills.old` if `keep_old(skills.old)`, else `skills`.
  `keep_old` is true when `skills.old` holds exactly the lock's **Vendored copies**, none missing and each matching: a
  run that only added **Skills** and was killed after its lock write leaves `skills.old` short of the new ones, so the
  complete `skills` is kept. `vendor.recover` does what `pending` names and deletes `skills.new`; it runs only right
  before staging. `transaction` builds `keep_old` from `lock`, so `vendor` imports no `lock`. `vendor.clear_old` first
  renames `skills.old` to `skills.trash`, which `recover` always deletes and never keeps: a run that changed nothing
  leaves a `skills.old` equal to the lock, and if its delete failed or was killed, the next run would take it back over
  an edit made since, without a word. Only a kill between the lock write and that rename still can.
- **The copy check.** `lock.copy_problems(skills, locked)` returns one line per entry of `skills` whose hash differs
  from the lock's for the **Skill** deployed under that name, per folder no **Skill** of the lock is deployed under, and
  per file at its top level, which a swap would drop; empty when they match. A missing copy is no problem.
  `transaction.check_copies(skills, locked)` checks the folder `pending` names, so a dry run and a refused `build`
  report what a writing run would and change nothing, and raises a `SkillGraftError` with those lines and the way out:
  move the edit into a **Patch**, or delete the folder. When the lock is missing, cannot be read or is of another
  `version` and `skills` holds anything, it raises instead an error saying the lock is missing or unreadable, so
  `.apm/skills/` cannot be checked, and to delete `.apm/skills/`, then run `skill-graft resolve`: the copies are not to
  blame. `resolving` runs it first, writing or not, unless the caller passes `checked=True`; `--into`'s `skills` is
  empty, so it passes. `update` calls it before listing remotes, so an edited copy is reported before any network or
  cache work, and passes `checked=True`, so the copies are hashed once.
- **Hashes come from `skill_hashes`.** `build`'s hashing of the copies goes; the lock's hashes are `skill_hashes(hull)`
  for every command, as for `update` today. A test pins `folder_hash(copy) == skill_hashes(hull)[skill]` for a renamed,
  patched, symlinked and executable **Skill**: the copy check fails every second command without it.
- **`build` checks the rendered lock.** `Resolution` gains `verify: Callable[[str], None] | None`. `build` sets it to
  compare `tomllib.loads(lock_text)` with the **Package**'s lock, parsed (`lock.load(scope.lock_file)`, also for
  `--into`). `lock.drift(new, old, path_aliases)` returns the path **Source** **Skills** whose `hash` differs and a
  refusal, `None` when nothing else differs: the two parsed locks compared with each path **Source**'s `path` and the
  `hash` of its **Skills** that have no `patches`, in either lock, dropped. A path **Source** **Skill** with **Patches**
  is checked as a git one's: its hash cannot tell an edit to its folder from one to a **Patch**, and a **Patch** edited
  by hand is refused. The refusal names each git **Source** **Skill** whose hash differs and each **Skill** joining or
  leaving; when none does, it says the **Sources**, names, edges or suggestions differ. No lock, or a `version` other
  than 1: refused, naming `resolve`. Parsed, not text: an editor's comment or line endings are no drift, as in
  `update`'s nothing-to-apply check. Rejected: comparing hashes alone, which misses a hand-edited `ref` that moves no
  hash, a **Bind** changing an edge, and a new **Entry** already in the **Hull**.
- **A path **Source**'s folder is no drift.** In project scope, a path **Source** outside the project root is recorded
  absolute, so a teammate's `build` would otherwise always refuse the committed lock. Path **Sources** are trusted as
  the user's own (only advised on), so where they live is as well; `build` writes the lock with this machine's folder.
  Rejected: refusing, so that each machine's `resolve` rewrites the committed lock.
- **The path **Source** notice comes after the lock.** `build` keeps what `drift` returned and, once `resolving` has
  written the lock, prints for each **Skill**
  `skill-graft: <skill id> changed in its path source since skill-graft.lock: deployed as is`, before APM's output. A
  failed write so never claims a change it rolled back.
- **The lock's header** becomes `# Written by skill-graft, which reads it back. Do not edit.`
- **Committed copies keep their bytes.** In project scope `.apm/skills/` is committed and hashed byte for byte, so
  `core.autocrlf` or `* text=auto` on a teammate's checkout would turn every copy into an edit. Every command that
  vendors writes `.apm/skill-graft/.gitattributes`, if missing, holding `/.apm/skills/** -text` and `/patches/** -text`:
  git then stores and checks out the copies and **Patches** byte for byte. One the user wrote stays as it is. It is one
  of `resolving`'s writes, restored with the TOML. `build --into` writes none: it changes nothing in the **Package**,
  and its folder is a throwaway. `/patches/** -text` covers only **Patches** inside the **Package**; those beside a
  symlinked `skill-graft.toml`'s target are the user's repository's to mark. Rejected: hashing with line endings
  normalized, which would deploy text other than the lock records.
- **`build.py` keeps only its own concerns:** the `--into` checks and undo, `verify`, the notice, the suggestions line
  and `apm.install`. `resolve.py` and `edit.py` change only through `resolving`; `update.py` also checks the copies
  before fetching.
- **`init` and `graft-check` follow.** `init`'s message when APM fails after registering says to fix the problem, then
  run `skill-graft resolve` and `skill-graft build`. `graft-check`'s **Patch** fix runs `skill-graft resolve` after
  appending to `[patches]`, before its throwaway build; when that `resolve` or the build fails, the fix is undone, then
  `skill-graft resolve` runs again if the first one succeeded. Its close drops "the commands that edit config write the
  lock and leave the vendored copies behind": `.apm/skills/` now always matches the lock, so after a declined **Check**
  it says the **Package**'s copies match its config, and to run `skill-graft build` if it has not run since the last
  change, which it cannot tell. A **Package** with no lock ends the **Check** at its first build, whose error names
  `resolve`. `evals/graft-check/run.sh` resolves where it built from a hand-written config.
- **`docs/design.md`'s table** lists `.apm/skills/<name>/` as written by `resolve`, `build`, `update` and the editing
  commands, and the sentence "The lock is output only" becomes "`build` deploys what the lock records".

## Risks / Trade-offs

- An existing **Package** whose lock a `resolve` or edit wrote after its last `build` → the first command refuses its
  copies as edited. Acceptable: no migration code; `CHANGELOG.md` says to check them and delete `.apm/skills/`.
- A skill-graft upgrade that renders the lock or rewrites differently → `build` refuses until `resolve`. `CHANGELOG.md`
  says so for each such release.
- A stray file in a copy (Finder's `.DS_Store`, a sync tool's conflict copy) → refused as an edit. Acceptable: the error
  names the folder; skipping names would make the hash depend on a list to maintain.
- A folder link added inside a copy → not seen: `folder_hash` reads a skill as `deployed.walk` does, which lists a
  folder link but does not enter it, so APM deploys what it points at unchecked. Acceptable: no upstream skill holds one
  (resolving refuses a folder link in a hull skill), so only a deliberate edit adds it, as same-user tampering below.
- A run of `update` or an edit command killed after writing the TOML and before the lock → recovery restores the copies
  that match the old lock, but the TOML keeps the edit, so the next `build` refuses as for a hand edit and `resolve`
  accepts what the command started. Acceptable: today the same kill leaves the TOML and the lock apart unnoticed.
- A clone committed before `.gitattributes` existed → its checkout may already hold converted copies; the first command
  refuses them, and `CHANGELOG.md` says to delete them and check them out again
  (`git checkout -- .apm/skill-graft/.apm/skills`) once `.gitattributes` is in, or delete them and `resolve`.
- A copy deleted by hand, then a run that changed a **Skill** killed before its lock write → `skills.old` lacks the
  deleted copy, so recovery drops it and keeps the new copies, which the next command refuses as edited against the old
  lock. Acceptable: rare, and deleting the folders is the way out; telling this apart would need a record of the run.
- A teammate's `build` in project scope rewrites the committed lock's absolute path **Source** folders → as today.
- `resolve` and the editing commands now copy the **Hull** → the copy is small next to resolution's git work.
- A path **Source**'s file saved while a command runs, after `render` hashed it and before `stage` copied it → the lock
  records one text, the copy holds the other, and the next command refuses the copy as edited. Acceptable: the window is
  a run's milliseconds, and deleting the folder is the way out; hashing the staged copies instead would read every copy
  once more on every run.
- Same-user tampering → not prevented: the lock is as writable as the cache (ADR 0009).
- Many tests build from a config written by hand → `tests/conftest.py`'s `build` helper runs `resolve` first; direct
  `main(["build", …])` calls in tests that expect success do too.
