## MODIFIED Requirements

### Requirement: Selection errors

An alias naming a path **Source** or no declared **Source**, an unselected git **Source** without `ref` (it cannot be
resolved), a `branch` that is not a valid branch name (revision syntax such as `main~3` included), a `branch` the remote
lacks (including one deleted since an earlier fetch), and a remote that reports no default branch when `branch` is
absent SHALL be errors naming the alias, and `update` SHALL then write nothing. The first three SHALL be reported before
any remote is contacted. An unselected git **Source** without `ref` SHALL be reported in one error naming every
unselected git **Source** without `ref`, suggesting the command run again with those added, each alias once and in
config order, keeping `--dry-run` and `--diff`, and replacing `--expect` with `--dry-run`.

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
  `update a --expect <hull-digest> --diff review.diff`
- **THEN** `update` exits non-zero suggesting `skill-graft update a b --dry-run --diff review.diff` either way, and
  `skill-graft.toml` is unchanged

#### Scenario: No default branch

- **WHEN** `mp` has no `branch` and the remote's `HEAD` names no existing branch
- **THEN** `update` exits non-zero naming `mp` and suggesting a `branch` key

#### Scenario: Tip already cached

- **WHEN** the tip of `mp`'s branch is already in the cache
- **THEN** `update` asks the remote only for its branches' tips, and fetches nothing

### Requirement: Update to the hull vetted

`update --expect <hull-digest>` SHALL exit non-zero, writing neither `skill-graft.toml`, the lock nor `--diff`'s file,
and saying the **Hull** is not the one reviewed and how to review it again, unless the **Hull digest** of the **Hull**
it resolves is `<hull-digest>`: one SHA-256 over each of its **Skills**' **Skill ID**, **Deployed name** and hash as the
lock records it. A `<hull-digest>` that is not 64 lowercase hex digits SHALL be refused before any fetch.

A dry run that succeeds SHALL print, once its diff file is written and before its `dry run:` line,
`apply: skill-graft update --expect <hull-digest>` with the **Sources** it was given and its **Hull**'s digest, exactly
when it printed no `review:` hint, named no **Skill** as edited since the lock was written, and has something to apply.
With no previous **Hull**, the lock check SHALL be skipped: the **Deployed diff** shows every **Skill** in full.

A dry run has nothing to apply when no `ref` moves and the lock it would write records, as TOML, what the current lock
records, whatever its line endings or formatting. It SHALL then print `nothing to apply` in place of its `apply:` line,
before its `dry run:` line.

#### Scenario: Nothing to apply

- **WHEN** `mp`'s tip is its `ref`, nothing else changed since the lock was written, and the user runs
  `update mp --dry-run`
- **THEN** it prints `mp <sha> (unchanged)`, `hull unchanged`, `nothing to apply`, then its `dry run:` line, and no
  `apply:` line

#### Scenario: Lock with other line endings

- **WHEN** nothing changed since `build`, the lock's line endings were turned into CRLF, and the user runs
  `update --dry-run`
- **THEN** it prints `nothing to apply`

#### Scenario: Unrelated push still applies

- **WHEN** `mp`'s tip moved to a commit that changes no **Skill** of the **Hull**, and the user runs
  `update mp --dry-run`
- **THEN** it prints `hull unchanged` and an `apply:` line, not `nothing to apply`

#### Scenario: Apply line

- **WHEN** `mp/tdd` changes at the new tip and the user runs `update mp --dry-run --diff review.diff`
- **THEN** it prints `apply: skill-graft update mp --expect <hull-digest>`, then its `dry run:` line

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
- **THEN** it names `own/notes` as edited since the lock was written and prints neither an `apply:` line nor
  `nothing to apply`

#### Scenario: Changed by resolution only

- **WHEN** `mp` moves, and `own/notes`, of a path **Source** unedited since the lock was written, now deploys another
  name for one of its **References**, and the user runs `update mp --dry-run --diff review.diff`
- **THEN** it prints an `apply:` line, and running it writes the lock with `own/notes`' new hash

#### Scenario: Tip moved after vetting

- **WHEN** the user runs `update mp --dry-run --diff review.diff` at tip B, upstream then pushes C changing `mp/tdd`,
  and the user runs the `apply:` line
- **THEN** it exits non-zero naming both digests and the review command, and `skill-graft.toml` and the lock keep their
  bytes

#### Scenario: Path source edited after vetting

- **WHEN** after `update mp --dry-run --diff review.diff`, `own/notes`' `SKILL.md`, of a path **Source**, changes, and
  the user runs the `apply:` line
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

- **WHEN** the user runs `update --expect <hull-digest> --diff review.diff` and the digest does not match
- **THEN** `review.diff` does not exist

#### Scenario: Malformed digest

- **WHEN** the user runs `update --expect abc123`
- **THEN** it exits non-zero naming the digest and asking for 64 hex digits, before any fetch

#### Scenario: Placeholder named for the hull digest

- **WHEN** the user runs `update --help`, or an `--expect` value does not match
- **THEN** the usage shows `--expect hull-digest`, and the mismatch error reads `its hull digest is <hull-digest>`
