# Proposal

## Why

`build` vendors only the **Entries**, so a skill that calls `/grilling` deploys without `grilling`. Following
slash and Skill tool **References** to the **Hull** is skill-graft's core value: the user names what they want,
and gets what it needs.

## What Changes

- **References**: found in every Markdown file of a **Skill**, in two forms: slash (`/grilling`, a standalone
  token, never part of a path or URL) and the Skill tool form (`Skill(grilling)`). Prose **References** stay out
  of scope.
- **Resolution**: a **Reference** resolves in its own **Source** first, else in exactly one other declared
  **Source**. Several other **Sources** is an error naming them, until a **Bind** settles it. One matching no
  **Skill** in any declared **Source** is a warning naming the `false` **Bind** that would silence it; the
  command proceeds.
- **Binds**: a new `[bind]` table in `skill-graft.toml`, keyed `<referencing source>/<reference name>`, whose
  value is a **Skill ID** or `false` (not a **Reference**). It overrides the default for every slash and Skill
  tool **Reference** to that name from that **Source**. A **Bind** no **Reference** uses is a warning.
- **Hull**: the **Entries** plus every **Skill** reachable through slash and Skill tool **References**.
  **Deployed names** (still the names, no **Renames** yet) are unique across the **Hull**.
- New `skill-graft resolve`: computes the **Hull**, writes `skill-graft.lock` (each **Source**'s resolved
  commit or folder, the **Hull**, every edge with its kind, a hash per **Skill**), and prints a `cargo tree`
  style tree, one line per edge naming the **Reference**, repeats marked `(*)`, then the warnings. It reads git
  **Sources** at their **Ref**, fetching only a missing **Ref**.
- `build` resolves first, vendors the **Hull**, and writes the lock. The lock is output only: never read back.
- `update` resolves the **Hull** at the new tips, prints the **Hull** diff (added, removed, changed **Skills**),
  and writes the lock with the TOML.

Out of scope: prose **References**, **Renames**, **Reserved names**, **Patches**, `why` and `tree`, `add` and
`rename`.

## Capabilities

### New Capabilities

- `hull`: finding slash and Skill tool **References**, resolving them (own **Source**, one other, **Binds**),
  and the **Hull** they span.
- `resolve`: the `resolve` command, `skill-graft.lock`, and the tree and warnings it prints.

### Modified Capabilities

- `config`: `[bind]` becomes a supported table.
- `build`: vendors the **Hull** rather than the **Entries**; **Deployed names** unique across it; writes the
  lock.
- `update`: resolves the **Hull**, prints its diff, writes the lock.

## Impact

- New: `src/skill_graft/references.py` (finding **References**), `hull.py` (resolution and **Hull**),
  `lock.py` (lock and tree), with tests.
- Changed: `config.py` (`[bind]`), `resolve.py` (every **Source**'s folder; resolution of the **Hull**),
  `discovery.py` (`find` errors not worded for **Entries** only), `vendor.py` (copies the **Hull**), `update.py`
  (diff, lock), `cli.py` (`resolve`; `build` writes the lock).
- `docs/design.md`: the lock format and the Skill tool form, once settled.
- Every declared **Source** is now read, used by an **Entry** or not: a reference may resolve in any of them. So
  `build` now fails on an unused git **Source** whose `ref` is uncached and cannot be fetched.
