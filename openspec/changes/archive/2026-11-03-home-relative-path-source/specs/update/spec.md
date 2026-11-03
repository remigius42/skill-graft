## MODIFIED Requirements

### Requirement: Update to the hull vetted

`update --expect <hull-digest>` SHALL exit non-zero, writing neither `skill-graft.toml`, the lock nor `--diff-file`'s
file, and saying the **Hull** is not the one reviewed and how to review it again, unless the **Hull digest** of the
**Hull** it resolves is `<hull-digest>`: one SHA-256 over each of its **Skills**' **Skill ID**, **Deployed name** and
hash as the lock records it. A `<hull-digest>` that is not 64 lowercase hex digits SHALL be refused before any fetch.

A dry run that succeeds SHALL print, once its diff file is written and before its `dry run:` line,
`apply: skill-graft update --expect <hull-digest>` with the **Sources** it was given and its **Hull**'s digest, exactly
when it printed no `review:` hint, named no **Skill** as edited since the lock was written, and has something to apply.
With no previous **Hull**, the lock check SHALL be skipped: the **Deployed diff** shows every **Skill** in full.

A dry run has nothing to apply when no `ref` moves and the lock it would write records, as TOML, what the current lock
records, whatever its line endings or formatting, and whatever path each path **Source** is recorded at. It SHALL then
print `nothing to apply` in place of its `apply:` line, before its `dry run:` line.

#### Scenario: Nothing to apply

- **WHEN** `mp`'s tip is its `ref`, nothing else changed since the lock was written, and the user runs
  `update mp --dry-run`
- **THEN** it prints `mp <sha> (unchanged)`, `hull unchanged`, `nothing to apply`, then its `dry run:` line, and no
  `apply:` line

#### Scenario: Lock with other line endings

- **WHEN** nothing changed since `deploy`, an editor added a comment to the lock and turned its line endings into CRLF,
  and the user runs `update --dry-run`
- **THEN** it prints `nothing to apply`

#### Scenario: Path source recorded elsewhere

- **WHEN** nothing changed since the lock was written, except that it records path **Source** `own` at another machine's
  folder, and the user runs `update --dry-run`
- **THEN** it prints `nothing to apply`

#### Scenario: Unrelated push still applies

- **WHEN** `mp`'s tip moved to a commit that changes no **Skill** of the **Hull**, and the user runs
  `update mp --dry-run`
- **THEN** it prints `hull unchanged` and an `apply:` line, not `nothing to apply`

#### Scenario: Apply line

- **WHEN** `mp/tdd` changes at the new tip and the user runs `update mp --dry-run --diff-file review.diff`
- **THEN** it prints `apply: skill-graft update mp --expect <hull-digest>`, then its `dry run:` line

#### Scenario: No apply line before a review

- **WHEN** `mp/tdd` changes at the new tip and the user runs `update --dry-run` without `--diff-file`
- **THEN** it prints the `review:` hint and no `apply:` line

#### Scenario: Apply line without a previous hull

- **WHEN** `mp`'s `ref` is not in the cache and the user runs `update --dry-run --diff-file review.diff`
- **THEN** `review.diff` shows every **Skill** as all added, and it prints an `apply:` line

#### Scenario: Hint without a previous hull

- **WHEN** `mp`'s `ref` is not in the cache and the user runs `update --dry-run` without `--diff-file`
- **THEN** it prints the `review:` hint and no `apply:` line

#### Scenario: No apply line after an edit

- **WHEN** a path **Source**'s `own/notes` changed since the lock was written, and the user runs
  `update --dry-run --diff-file review.diff`
- **THEN** it names `own/notes` as edited since the lock was written and prints neither an `apply:` line nor
  `nothing to apply`

#### Scenario: Changed by resolution only

- **WHEN** `mp` moves, and `own/notes`, of a path **Source** unedited since the lock was written, now deploys another
  name for one of its **References**, and the user runs `update mp --dry-run --diff-file review.diff`
- **THEN** it prints an `apply:` line, and running it writes the lock with `own/notes`' new hash

#### Scenario: Tip moved after vetting

- **WHEN** the user runs `update mp --dry-run --diff-file review.diff` at tip B, upstream then pushes C changing
  `mp/tdd`, and the user runs the `apply:` line
- **THEN** it exits non-zero naming both digests and the review command, and `skill-graft.toml` and the lock keep their
  bytes

#### Scenario: Path source edited after vetting

- **WHEN** after `update mp --dry-run --diff-file review.diff`, `own/notes`' `SKILL.md`, of a path **Source**, changes,
  and the user runs the `apply:` line
- **THEN** it exits non-zero, and `skill-graft.toml` and the lock keep their bytes

#### Scenario: Patch edited after vetting

- **WHEN** after `update mp --dry-run --diff-file review.diff`, a **Patch** of `mp/tdd` changes, and the user runs the
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

- **WHEN** the user runs `update --expect <hull-digest> --diff-file review.diff` and the digest does not match
- **THEN** `review.diff` does not exist

#### Scenario: Malformed digest

- **WHEN** the user runs `update --expect abc123`
- **THEN** it exits non-zero naming the digest and asking for 64 hex digits, before any fetch

#### Scenario: Placeholder named for the hull digest

- **WHEN** the user runs `update --help`, or an `--expect` value does not match
- **THEN** the usage shows `--expect hull-digest`, and the mismatch error reads `its hull digest is <hull-digest>`
