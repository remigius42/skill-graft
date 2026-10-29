# Spec Delta

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
  `update a --expect <digest> --diff review.diff`
- **THEN** `update` exits non-zero suggesting `skill-graft update a b --dry-run --diff review.diff` either way, and
  `skill-graft.toml` is unchanged

#### Scenario: No default branch

- **WHEN** `mp` has no `branch` and the remote's `HEAD` names no existing branch
- **THEN** `update` exits non-zero naming `mp` and suggesting a `branch` key

#### Scenario: Tip already cached

- **WHEN** the tip of `mp`'s branch is already in the cache
- **THEN** `update` asks the remote only for its branches' tips, and fetches nothing
