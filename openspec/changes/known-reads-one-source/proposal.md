# Proposal

## Why

`compute.known` checks that a **Skill ID** names a **Skill** of its **Source**, yet it reads every declared **Source**
to do so: `_folders` checks every git **Source**'s `ref` and checks each one out, fetching any commit the cache lacks.
`rename` and `bind` call it to check the **Skill ID** they are given, so a typo in it is reported only after every other
**Source** is fetched, and only if every one has a `ref` and can be fetched; a no-op `bind` or `rename`, which never
resolves, still fails on a **Source** it has nothing to do with.

## What Changes

- `known` reads only the **Source** of the **Skill ID** it checks: that **Source**'s `ref` checked, it alone checked
  out, fetched only if its commit is missing from the cache. A git **Source** of that **Skill** without a `ref` is the
  error `build` gives, naming every git **Source** without one and the one `update` command.
- `rename` and `bind` report a **Skill** missing from its **Source** before any other **Source**'s missing `ref` or
  failed fetch; `bind` checks its target this way for a new key too, not only for one already bound. The edit then
  resolves as before, which still needs every `ref`.
- A no-op `rename` (the current **Deployed name**) or `bind` (the current value) reads no other **Source**: it exits 0
  with its notice even when another git **Source** has no `ref` or cannot be fetched.
- `why` keeps calling `known` for a **Skill ID** outside the **Hull**: the **Hull** is computed first, so nothing it
  prints changes; the lookup now reads one **Source** instead of all.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `edit`: a new requirement that `rename` and `bind` check the **Skill ID** they are given by reading only its
  **Source**, fixing the error order and the no-op case.
- `renames`: "Deployed names are unique" says `rename` and `bind` read the given **Skill ID**'s **Source** before an
  **Entries** clash is reported, not every **Source**.

## Impact

- `src/skill_graft/pipeline/compute.py`: `known`, and `_folders` split so one **Source**'s folder can be had alone.
- `src/skill_graft/commands/edit.py`: `bind` calls `known` on every target but `false`; `commands/explain.py` unchanged.
- Tests: `tests/commands/test_edit.py` gains the scenarios; `tests/commands/test_explain.py` a test that `why` of a
  **Skill ID** outside the **Hull** still errors as before.
- `docs/design.md`: the `rename`/`bind` bullets say only the given **Skill ID**'s **Source** is read.
- `CHANGELOG.md`, in the archive commit: users see the error order and the no-op edits change.
