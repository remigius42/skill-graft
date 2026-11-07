# Design

## Context

`uv run mutmut run "skill_graft.infra.*"` on `206255fc`, 18 minutes, left 201 survivors, the count of `mutmut-src`'s
baseline row for `infra`. No later commit on `main` touches `infra/` or its tests. Each one's diff, read once
(`mutmut show`), falls in one of five kinds:

| Module   | Survivors | To kill | Dropped | Pragma | mypy refuses | Wording |
| -------- | --------: | ------: | ------: | -----: | -----------: | ------: |
| `cache`  |       131 |      72 |      26 |      0 |           27 |       6 |
| `git`    |        32 |      17 |       9 |      0 |            1 |       5 |
| `errors` |        13 |      13 |       0 |      0 |            0 |       0 |
| `text`   |        10 |       9 |       1 |      0 |            0 |       0 |
| `apm`    |         7 |       1 |       2 |      0 |            1 |       3 |
| `files`  |         7 |       4 |       2 |      1 |            0 |       0 |
| `paths`  |         1 |       0 |       1 |      0 |            0 |       0 |
| all      |       201 |     116 |      41 |      1 |           29 |      14 |

"Dropped" are equivalent mutants that removing a redundancy, or restructuring, leaves without a counterpart; "Pragma"
the equivalent ones that stay, each marked. The mypy kind is mostly `context=None` where `context: str`: `cache` threads
a context string through every git call. No survivor is a bug. Mutant numbers are mutmut's at `206255fc`; they shift
with edits, so each task reruns its module first. The classification was reviewed, and git 2.55 probed, for every flag
this design removes or keeps.

## Goals / Non-Goals

**Goals:** `infra/` with no survivor but known noise and one marked equivalent.

**Non-Goals:** `commands/` and `cli` (their own changes); testing message wording; changing what a user sees.

## Decisions

### Seams: each module's public functions, and `Cache`

Tests go through `cache.Cache` (`checkout`, `fetch`, `has_commit`), `cache.key`, `cache.prune`, `cache.lock`; `git.run`,
`git.apply`; `errors.flush_stdout`; `files.atomic_write`; `text.ranges`, `text.show`; `apm.registered`; `paths.cache`.
No test calls a `_private` function: every killed mutant in one is reached through these, as the existing tests do, and
a test of a private function would break with each restructure below. `files` and `text` get their first test files,
`tests/infra/test_files.py` and `test_text.py`.

### The export's second guards, with git's fsck off

`cache` passes `git.FSCK` to every clone and fetch, and fsck refuses a tree with `..`, `.git` or a duplicate name before
`_export` sees it: the existing hostile-tree tests pass on fsck alone, so `_safe` (9 mutants), the symlinks-last order
(4) and the `or os.path.lexists(target)` check (1) survive. Their tests set `git.FSCK` to `[]` with
`monkeypatch.setattr` (`cache` reads it at each call) and build the tree with the existing `write_object`, so the
export's own check is what refuses it. The order is observable only with a duplicate name: a symlink `a` to the folder
`b` inside the export, and a folder `a` holding `x`, writes `b/x` unless the symlink comes last. `_safe`'s empty part
comes from an entry named `z/`: git's pack-objects refuses an empty name even with fsck off.

### Recording git's arguments: guards no local remote shows, and cost

`test_cache.py`'s `recorded(monkeypatch)` already lists the calls `git.run` receives, and counts `rev-list` calls. It is
used only where a flag's absence changes nothing a local test can see:

- Security guards. `git.FSCK` on the blob fetch and the refetch (a lone blob gives fsck nothing to refuse);
  `--recurse-submodules=no` on both, in one test of the two fetches a refused blob fetch makes; `_clone`'s `--` before
  the URL (without it, a URL `--upload-pack=…` is read as an option, harmless today only because the temporary folder
  after it then becomes the source and git fails before any transport); and in `git.apply`, recorded from
  `subprocess.run`, the environment keys `GIT_CONFIG_NOSYSTEM`, `GIT_ATTR_NOSYSTEM`, `HOME` and `XDG_CONFIG_HOME` (a
  test cannot write the system config, and `HOME="None"` reads no user config either).
- Cost. The tips `_missing` lists from: the subdirectory's own tree or a blob's folder, not every tree on the path
  (`_listing`'s `and`, `rpartition`: extra tips list more blobs, filtered out); no `update-ref` when `_pin`'s pin
  exists; and `_fetch_blobs`'s `--no-tags`: the overlay copies no `remote.origin.tagopt`, and without the flag a dry
  run's blob fetch lists every tag upstream first (`ls-refs ref-prefix refs/tags/`), though it stores none (probed, git
  2.55).

Every other flag gets a behavior test: `fetch`'s `--prune` (a deleted branch) and `--no-tags` (a fetch into a dry run's
overlay, which has no `tagopt`, takes no tag); `_refetch`'s `--no-tags` (with `remote.origin.tagOpt=--tags` passed
through `GIT_CONFIG_COUNT`, which outranks the repository's own `tagopt`); `_clone`'s `--reference-if-able` (alternates
point at the reference), `--no-tags` (a tag upstream; no `refs/tags`) and `-q` (the error of a clone fsck refuses holds
no `Cloning into`, which git prints once the transfer starts, even off a terminal, naming the temporary folder; a
missing repository fails before it); `-q` in `fetch` and `_refetch` (a `refs/heads/main.lock` left in the cache
repository fails the fetch after git prints `From …` and ref lines, which the error then holds without `-q`);
`_fetch_blobs`'s `origin` (a global `branch.main.remote = upstream` would otherwise pick the remote); `_refetch`'s
refspec (a ref only on a second branch); `_ls_tree`'s `--literal-pathspecs` and `--` (subdirectories named `:x`, which
git reads as pathspec magic for `x`, and `--name-only`; `ls-tree` never globs, so `a*` shows nothing); the overlay's
`--local` and `extensions.partialclone` (its config equals the real one's promisor settings, with a global config set
through `GIT_CONFIG_GLOBAL`; the test writes `extensions.partialclone` into the real repository itself, as git 2.55 no
longer does but the older git README.md supports does, and reads); `git.run`'s `GIT_NO_LAZY_FETCH` only with a `repo`
(run in a blobless clone's folder without `repo`, git's own lazy fetch brings a missing blob).

### Other `cache` gaps, by behavior

A tab in a tree path (`split(b"\t", 1)` in `_export` and `_listing`), a space in the source path (the overlay's
`partition`), an empty promisor setting (its name and a space alone), a URL ending in `X` (`key`'s `rstrip`), an export
of several files (`_read_blobs`'s offset after each object drifts by one under its mutant, and the oid check below
refuses the second header), an executable's mode exactly `0o755` under umask `022`, a subdirectory sibling's blob left
unfetched (`_missing`'s `and`), a dry-run checkout of a subdirectory not served from the reference's whole-tree export,
prune at exactly `UNUSED`, past an entry gone before its age is read (`except OSError: continue`), and over an
unremovable leftover, `_build` keeping `make`'s error over a failing cleanup, a killed clone's leftover named `.tmp` and
pruned, and git before 2.36 (`unknown option \`refetch'\`, raised by a recording stub) getting the version message.

`_read_blobs` checks each header's oid against the one it asked for, and otherwise raises an error of its own,
`unexpected output from git cat-file --batch` with the oid: a misaligned parse now fails instead of returning wrong
bytes, and does not send the user to the cache's docs, as the missing-object error would. git's well-formed output never
reaches it, so a user sees nothing new; it kills `at = 1`, which only trimmed the first header's unread oid, with no
pragma.

### `git`, `errors`, `text`, `files`, `apm`

- `git.run`: without `repo`, no `--git-dir` (run in a repository's folder via `monkeypatch.chdir`); non-UTF-8 bytes in
  git's stderr (a repository path from `os.fsdecode(b"...\xff")`) replaced, not raised; a failure after
  `--literal-pathspecs` or `-c x=y` names its subcommand. `git.apply`: `--whitespace=nowarn` (trailing whitespace, no
  warning); a broken `$XDG_CONFIG_HOME/git/config` not read; non-UTF-8 stderr.
- `errors.flush_stdout`: `_discard` raising a bare `ValueError`, and a bare `OSError`, both suppressed; and with a real
  pipe as stdout whose flush fails, its descriptor afterwards writes to `os.devnull` (kills `_discard`'s ten, all of
  which the existing tests replace).
- `text.ranges`: called directly. `CRITICAL_CHARS` is built at import, before any mutant is active, but `ranges` is not
  import-time noise: `deployed` calls it at run time, so its mutants are gaps.
- `files.atomic_write`: the temporary file beside `file`, named `.<name>.…` (`os.replace` recorded).
- `apm.registered`: an item `X/../.apm/skill-graft` registers (`strip("\"'")`).

### Equivalent mutants: dropped first, a pragma only where none can be

`CONTRIBUTING.md`'s rule: remove what an equivalent mutant shows redundant, or restructure so none exists, or name the
value in a module-level constant (mutmut mutates only functions); only then the equivalent expression alone on a line of
its own, a bare `# pragma: no mutate` on it, `# Equivalent mutants: <reason>` above. No regions. None of these changes
what a user sees; each removal is a git or Python default, probed before it goes.

**Removed, redundant (13):**

- Defaults spelled out: `check=False` (`apm.install`, `git._call`; the pre-commit ruff selects `PLW1510`, so each call
  suppresses `PLW1510` with the reason, and a short comment where the exit code is read keeps the intent), `"wb"`
  (`atomic_write`), `-p1` and `-` (`git apply`; the docstring keeps naming them), `strict=True` in `_export`'s `zip`
  (`_read_blobs` returns one blob per oid or raises).
- `-q` in the overlay's `init`, which prints to stdout, returned unread. `-q` in `_fetch_blobs` too: probed, its output
  is the same without it, on success and on failure, as it writes no ref and no `FETCH_HEAD`.
- `--full-tree` in `_ls_tree`: a bare repository has no working-folder prefix.

**Restructured (28):**

- `.split()` for git's own `<mode> <kind> <oid>` and `<oid> <kind> <size>` headers (`_export`, `_listing`,
  `_read_blobs`), where `split(b" ")`'s `split(None)` mutant is equivalent; `_missing` takes the oid as the record's
  third field, `record.split()[2]`, without splitting off the name at the tab first, whose mutants all leave the oid
  third. The overlay's config line by `partition(" ")`: git lists an empty value as its name and a space alone.
- `_listing`'s path prefixes by `itertools.accumulate`, no `range(1, len(parts) + 1)` whose `+ 2` repeats the last.
- `_missing` lists from trees only: the whole tree's tip is `f"{ref}^{{tree}}"`, not the commit, so `--no-walk` goes;
  `_listing`'s and `_missing`'s docstrings, which explain the tips by `rev-list --no-walk`, follow.
- `_export` writes its files, then its symlinks, as two lists: no `sort(key=…)`, whose natural-order mutant is
  equivalent (blob modes `100644` and `100755` sort before `120000`).
- `paths.cache` reads `XDG_CACHE_HOME` without a default, `xdg and os.path.isabs(xdg)`.
- `git.run`'s locale, `LC_ALL=C` and `LANGUAGE=`, a module-level constant: an `LC_ALL` other than `C` is an unknown
  locale, which falls back to `C`, and `LANGUAGE` is ignored in `C`. `GIT_NO_LAZY_FETCH` stays behind `if repo`: `run`
  without one also serves `update`'s `ls-remote` and `check-ref-format`.
- `_tree`'s hash length, a module-level constant of its own (its `[:13]` is equivalent: a name that only needs to be
  stable; `key`'s length, killed by its test, stays apart, so changing one never renames the other's folders);
  `text.show`'s codec, `"unicode_escape"`, another (codec names ignore case); `atomic_write`'s `os.umask` argument,
  `ANY_MASK`, another (the mask set is replaced at once by the one read back).
- `_pin` asks `_has_commit(repo, pin)` instead of `rev-parse --verify -q pin`, whose `--verify`, `-q` and case mutants
  all read as "absent" or as before: still a read, then `update-ref` only when the pin is absent.
- The context of a check whose error is swallowed, `_has_commit`'s and `_pin`'s `update-ref`'s, a module-level constant
  instead of `str(repo)`, which no one reads.

**Marked (1):** `delete=False` in `atomic_write` (`None` is as false).

## Risks / Trade-offs

- [A recorded-arguments test pins an implementation] → only for security guards no local remote shows and for cost;
  every other flag has a behavior test.
- [Turning fsck off in a test hides a real fsck gap] → the existing tests keep fsck on; the new ones say why it is off.
- \[Prune's `except OSError: continue`→`break` is killed only if an entry fails before an old one\] → the test replaces
  `Path.lstat` so the first entry read fails, as one another run removed, and every old entry beside it goes.
- [A removed flag mattered after all] → each removal's reason is probed against git first; the existing tests run on the
  restructured code before any new one is written. Review found one: `--no-tags` in `fetch` and `_refetch`, removed for
  the clone's `tagopt`, which the overlay lacks and config in the environment outranks, so both keep it.
- [The oid check refuses output git considers fine] → `cat-file --batch` echoes the object name it was given, and the
  cache asks by full oid, so the two match whenever the parse is aligned.

## Migration Plan

None: tests, and source changes that keep what a user sees.
