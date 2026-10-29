# Design

## Context

`commands/update.py`'s `_update` prints the `apply:` line whenever a dry run showed no `review:` hint and named no
edited **Skill** (`elif not edited`). "Hull unchanged" there means only that the skill hashes match the previous
**Hull** (`previous[1] == hashes`). The lock also records `ref`s, edges and suggestions, so the hashes alone can't tell
whether `apply` would write anything. `resolve.resolving` renders the lock after the caller's body, because the caller
sets `resolution.hashes` in it, and on a dry run it returns before rendering. `_update` decides on `apply:` after the
`with resolving` block, so a text `resolving` stores is there in time.

`--expect` shipped in 0.2.2. Renaming its placeholder changes only help and error text, not the flag, so nothing breaks;
it gets a Changed entry.

## Goals / Non-Goals

**Goals:**

- A dry run that would write nothing says so and prints no `--expect` value.
- The placeholder uses the glossary term **Hull digest**.

**Non-Goals:**

- Changing what `update` without `--dry-run` prints or writes. It still rewrites the lock, with the same content.
- Changing what the hull diff reports (`hull unchanged` stays hash-based).
- The false-positive reference warnings (`/tmp`, `/architecture-review-`): a separate change.

## Decisions

- **Nothing to apply = no `ref` moves and the rendered lock parses to what the lock file parses to.** `resolving`
  renders the lock before its `if not write: return` and stores the text on `Resolution` (`lock_text`). The check runs
  only in the `not edited` branch: there the lock was already read and parsed, so an unreadable lock never gets this far
  (it marks every skill edited). `_update` loads the lock once, `lock.load` (`lock.read` split into `load` and
  `recorded`, the hashes), for both the edited check and this one, and compares `tomllib.loads(lock_text)` with it; a
  lock `load` cannot read (`None`), reachable only with an empty old **Hull**, counts as something to apply. Parsed, not
  text: a lock reformatted by an editor would otherwise get the `apply:` line this change removes. Line endings alone
  would not (text mode reads CRLF as LF); the lock is read as bytes and `tomllib` takes CRLF too. The one render is the
  one a real update writes, so the comparison can't drift from it. Rejected: "hull unchanged and no ref moved", which
  misses a change only in edges, suggestions or a path **Source**'s recorded folder. Rejected: a second `lock.render`
  call in `_update`, which duplicates its arguments.
- **`nothing to apply` replaces the `apply:` line only.** No ref moving means the previous **Hull** is resolved at the
  same refs, so nothing shows as changed and the `review:` hint can't appear. It goes to stdout, where `apply:` goes,
  before `dry run:`. A `--diff` file is still written as today (it holds `# hull unchanged`).
- **Suggestions line**: `announce_suggestions(hull, dry_run=not write and bool(moved))`. Whether `resolve` sees these
  tips depends only on whether a ref moves: an edited path **Source** with no ref moving still gets the plain line.
- **Placeholder `hull-digest`**, lowercase kebab like `skill-id`. The metavar `DIGEST` → `hull-digest`, `--expect`'s own
  help `update only if the new hull's digest is DIGEST, …` → `update only if the new hull has this hull digest, …`,
  `update`'s description `--expect <hull-digest>`, the mismatch error `its hull digest is …`. The malformed error
  `--expect <value>: expected 64 hex digits, as an apply: line gives` stays (it names the value, not a placeholder).

## Risks / Trade-offs

- `resolving` now renders on a dry run too, once → negligible next to the git work.
- `update` (no `--dry-run`) with nothing to apply still prints no notice → acceptable: it prints the `(unchanged)` lines
  and `hull unchanged`, and rewriting the same content is harmless.
