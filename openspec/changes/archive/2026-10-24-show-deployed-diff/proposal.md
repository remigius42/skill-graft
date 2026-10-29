# Proposal

## Why

`update` moves a git **Source**'s **Ref** to a commit nobody has vetted. Its **Hull diff** marks a **Skill** `~` when
its deployed text changed, but not what changed, so vetting a **Source** means rereading every changed **Skill** in
full, or trusting it. `docs/security.md` lists this as Future work: "`update` shows each changed **Skill**'s text diff,
so vetting covers only what changed." Printing **Skill** text to the console is no answer: it is untrusted, and escape
sequences in it could rewrite what the terminal shows.

## What Changes

- `update --diff <file>` writes the **Deployed diff**: for each **Skill** the **Hull diff** marks `~` or `+`, a unified
  diff of its text as deployed, **Patches** and **Renames** applied, at the current **Refs** against the new ones; a `+`
  **Skill** as all added. A header says it is the text as deployed, not what the **Source** changed; each **Skill**
  names its **Source**'s old and new **Ref** and its upstream folder, as data, for the user to inspect upstream. Every
  file is shown as text, undecodable bytes escaped, and each character an editor could take for a line break, or the
  **Hidden character** check reports, is escaped, so no line can hide or pass for another.
- `--diff` works with `--dry-run`, the intended use. It writes only a new file or a regular file it wrote before, named
  `*.diff`, never inside an `.apm` folder or a **Skill**'s folder; a failed run leaves none.
- `update --expect <digest>` refuses, writing neither config, lock nor diff file, unless the new **Hull**'s **Hull
  digest** is `<digest>`. A dry run that showed every change ends with `apply: skill-graft update … --expect <digest>`,
  so nothing changed between vetting and updating can slip in: a push, a path **Source**'s edit, a **Patch**, a
  **Rename**.
- Under each `~` and `+` line of the **Hull diff**, the console names each changed file, quoted so it is printable ASCII
  and never alike, with `(new)`, `(removed)` or `(changed)`, its sizes and executable bit. No **Skill** text reaches the
  console. A dry run that found changes, without `--diff`, hints `update … --dry-run --diff <file>` instead of the
  `apply:` line.
- `update` reads the lock's hashes: a **Skill** whose old side differs from them, edited since the lock was written, is
  named, and no `apply:` line is printed, as its earlier text was never shown. With no previous **Hull**, such as after
  **Patches** redone for the new tips, the file shows every **Skill** as added. An old **Ref** not in the cache is
  reported with its likely causes, not as a bare "not cached".
- `docs/security.md` drops the item from Future work and adds "verify the lock's hash at build" there; the README and
  `docs/design.md` describe `--diff` and `--expect`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `update`: "Dry run writes nothing" lets `--diff` write its file; "Report the hull diff" gains the per-file summary,
  the edited-since-the-lock line, the hint and the reworded reason; new requirements for the **Deployed diff**'s file
  and content, and updating to the **Hull** vetted.

## Impact

- `src/skill_graft/commands/update.py`: keep both **Hulls** open to compare; the summary, the lock check, the hint, the
  closing line; write the file.
- A new `src/skill_graft/pipeline/deployed.py`: the summary and the **Deployed diff** of two **Skill** folders as
  deployed, the diff a Myers diff on a step budget; no git.
- `src/skill_graft/cli.py`: the `--diff` and `--expect` options. `src/skill_graft/pipeline/lock.py`: the **Hull
  digest**, reading the lock. `src/skill_graft/pipeline/hidden.py`: its decoding shared with `deployed.py`.
- Tests in `tests/commands/test_update.py`, `tests/pipeline/test_deployed.py`, `tests/pipeline/test_lock.py`,
  `tests/cli/`.
- `CONTEXT.md` already defines **Hull diff**, **Deployed diff** and **Hull digest** (this branch's first commit).
- `docs/security.md`, `README.md`, `docs/design.md`; `CHANGELOG.md` entry at archive.
