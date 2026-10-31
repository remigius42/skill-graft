# Design

## Context

Checked against `main` (`69d3471`):

- `commands/transaction.py`'s `resolving` is the one place that writes the lock: it loads the lock, checks the copies
  against it (`check_copies`, unless `checked`), computes the **Hull**, yields a `Resolution`, renders the lock and,
  given `write`, stages the copies; then runs the caller's `writes`, writes `.gitattributes` if missing, swaps the
  copies in and writes the lock, undoing all on failure. With `write=False` it writes nothing.
- `edit.py`'s five commands each end in `_finish`, which parses the edited TOML, calls `resolving` with the TOML as one
  of its `writes`, and prints the tree. A no-op edit returns before `_finish`. `resolve.py` calls `resolving` directly.
- `update.py` owns the review code: `HEADER`, `_diff_target` (the file's refusals), `_print_diff` (the **Hull diff**
  lines over the old and new **Hulls**' hashes, views only for `+` and `~`), `_deployed_diff` and `_source_line`, and
  the dry run's `Cache(tmp, cache)` over a temporary folder. `pipeline/deployed.py` holds the views, `summary`, `diff`,
  `quote`.
- The lock records each **Skill**'s **Skill ID**, **Deployed name** (`deployed`, when it is not the name), upstream
  folder and hash; `lock.recorded` reads the hashes, `lock.deployed_names` the names. `check_copies` has already found
  each copy's hash equal to the lock's, in the folder `vendor.pending` names.
- `explain.tree(hull)` returns the `cargo tree` text. `cli.py` prunes the cache after every command but `init` and
  `update --dry-run`.

## Goals / Non-Goals

**Goals:**

- One review mechanism for every command that writes the lock: the same file rules, text rules, header first line and
  marked tree as `update`'s.

**Non-Goals:**

- Changing `update`'s before side (the **Hull** at the current **Refs**) to the **Vendored copies**: a follow-up.
- `--expect` on these commands: they move no **Ref**.
- A review of everything since the last `build`: git's diff of the committed **Package** covers it.

## Decisions

### A `commands/review.py` the four modules import

Move `HEADER`'s first line (`review.FIRST`, each command's header built by `review.header(compared)`), `_diff_target`,
the **Hull diff** lines (`review.print_diff`) and the file assembly (`review.deployed_diff`: header, marked tree,
per-**Skill** sections) out of `update.py` into `commands/review.py`, with `_fetch_hint`. Its old side is one small
object, `review.Before`: each **Skill**'s hash by **Skill ID**, its view on demand, its upstream folder for the source
line, and each git **Source**'s **Ref**. `update` builds it from its old **Hull** (`upstream`, `roots`,
`deployed_files`), as today; `edit` and `resolve` from the lock and the copies (`review.vendored`). `update.py`,
`edit.py` and `resolve.py` import it; it imports `explain` for the tree and `transaction` for the copies' folder, and
none of the three, so siblings stay one way. Rejected: `edit` importing `update`, a cycle, as `update` already imports
`edit`.

`_diff_target` splits in two: `review.check_target`, the refusals, run before anything else, and `review.clear`, the
removal of an earlier file it wrote, run when the command is past its no-op check.
`review.fetch_hint(error, tmp, fetch)` takes the text to show: for `edit` and `resolve`, to run the command line without
`--dry-run` to keep what it fetched; `update`'s text stays "run `update` without `--dry-run` to fetch the tip".

### The before side is the Vendored copies

The old hashes are the lock's (`lock.recorded`), which `check_copies` found equal to the copies, its upstream folders
the lock's `upstream`, and its **Refs** the lock's `[sources]`. A copy is read only through the entries of the folder
`vendor.pending` names (`transaction.pending`, which `check_copies` uses too), matched by name to the lock's **Deployed
names** (`lock.deployed_name`): the lock's `deployed` string is never joined onto a path, so a crafted lock cannot point
the old side outside `.apm/skills/`. Only a **Skill** with such an entry is on the old side, with its hash: one the lock
records without a copy is not, so it is `+` while in the **Hull**, and a removed one is `-` only when it had a copy. A
**Skill** renamed since keeps its **Skill ID**, so it is `~`; its bytes always change, as `rename.set_name` writes the
**Deployed name** into `SKILL.md`'s `name:`. No lock: the old side is empty. A removed **Skill**'s ID comes from the
lock, which nothing restricts, so its `-` line and `# - <skill id>` are quoted with `deployed.quote`.

A source line names the **Ref** the copies came from and the one the command would vendor, `old -> new` when a hand edit
moved it, as `update`'s does. The old one is the lock's, which nothing checks, so it is quoted with `deployed.quote`;
with none recorded, the line names only the new one.

### The dry run

Each of the six commands opens, at its top, `review.running(command, dry_run, diff, written)`: an `ExitStack` holding,
when dry, a `tempfile.TemporaryDirectory` and a `Cache(tmp, cache)` over the real one, as `update.update` does, so
`rename`'s and `bind`'s `compute.known`, which reads a **Source** before `_finish`, fetches into the temporary folder
too. It yields a `review.Run`: the cache, `--diff`'s target, and the lines a dry run prints last. `Run.proceed()`
registers the `review:` hint and the `dry run:` line on that stack only once the command is past its no-op check, so a
no-op edit prints only its notices; they then print last on stdout, the hint first, after `add`'s and `remove`'s notices
on stderr. The hint's arguments are quoted with `shlex.quote`, as `update`'s are. A `PatchError` in a dry run goes
through `review.fetch_hint`. `_finish(scope, warnings, document, run)` and `resolve` pass `write=not run.dry_run` to
`resolving`. `cli.py` skips the prune for every dry run.

`--diff`'s `<file>` is refused, if bad, before anything else; an earlier file it wrote is removed once the command is
past its no-op check, before resolving, and when the command fails before `resolving` has written everything, so a no-op
edit leaves it and a run that fails leaves none, as `update`'s "Failed run" says; a failure after, such as printing the
tree to a closed pipe, keeps the file of what was written (`Run.committed`).

The **Hull diff** is printed with `--dry-run` or `--diff`, as `update` prints it on every run, never on a plain edit,
whose output stays as it is. `review.stage(run, …)` prints it inside the `resolving` block, while the patched copies
exist, before the tree, from `lock.skill_hashes(hull)`, which also becomes `resolution.hashes`, so `lock.render` hashes
nothing twice. The file is built there too, and appended to `resolution.writes` before the TOML in a real run, so the
undo removes it; in a dry run `review.finish(run)` writes it last, after the tree.

### The marked tree

`explain.tree` takes an optional `marks: dict[SkillId, str]` and prefixes each line with its target's mark or two
spaces; without it the output is unchanged. `explain.tree_lines` returns those lines unjoined, as a reference could hold
a line feed, and `tree` joins them. The file starts every tree line with `#` and a space, then one `# - <skill id>` line
per removal. Each tree line is escaped as the diff body escapes a line (`deployed.escape`) before it goes into the file.
No tree line can hold a control character today: an edge's text is rebuilt from the name (`Skill(x)`, `/x`), and names,
aliases, prefixes and deployed names all match `NAME`; the escape guards the file should that change.

### Header lines

The first line stays as it is, so `review.check_target` accepts a file any command wrote; the second is the command's:
`update`'s current one; for the editing commands "the Vendored copies against what the edited config would vendor"; for
`resolve` "the Vendored copies against what `skill-graft.toml` as it stands would vendor".

## Risks / Trade-offs

- \[Moving `update`'s review code risks changing its output\] → `tests/commands/test_update.py` pins it; the move is a
  refactor task of its own, green before and after.
- \[A dry run reads a **Skill** once to print and again for a real run\] → A path **Source** file saved in between is
  vendored as saved, not as shown. Accepted: the user's own text, and the next command's copy check names any drift.
- \[Two commands can disagree on what before means: `update` the old **Refs**, the others the copies\] → Equal but for
  path **Source** text edited since the lock, which `update` names; unified in the follow-up.

## Migration Plan

None: new flags, and new lines in the diff file. A **Deployed diff** from an earlier version still starts with the same
first line, so `--diff` replaces it.
