# Proposal

## Why

`build` re-resolves and overwrites `skill-graft.lock` and the **Vendored copies**: the lock's hashes record what was
deployed, but nothing checks them (`docs/security.md`, LLM03 and Future work). In project scope a lock reviewed in a
pull request says nothing about what a later `build` deploys, and an edit to a **Vendored copy** is lost without a word.
ADR 0009 records the decision: `build` deploys what the lock records.

## What Changes

- **BREAKING** `build` deploys only what the lock records. It refuses, naming `skill-graft resolve`:
  - a git **Source**'s **Skill** whose hash differs from the lock's (the config or a **Patch** edited by hand, an edited
    cache export, a skill-graft upgrade that rewrites differently), listing each;
  - any change to the **Hull**'s shape: a **Skill** joining or leaving, a **Deployed name**, edge, suggestion or
    **Source** changing, whatever the cause;
  - a missing lock, or one it cannot read or of another `version`.
- An edited path **Source** whose **Hull** keeps its shape: `build` deploys each changed **Skill**, writes its new hash
  into the lock, then names it. Where a path **Source** lives is no difference either, so a committed project lock
  recording another machine's folder still builds.
- A path **Source** **Skill** with **Patches** is checked as a git one's: a **Patch** edited by hand is refused.
- A lock that is missing, unreadable or of another `version` beside existing copies: the error says the copies cannot be
  checked, and to delete `.apm/skills/` and run `resolve`.
- Every command that vendors writes `.apm/skill-graft/.gitattributes`, if missing, so git keeps the committed copies'
  and **Patches**' bytes: a teammate's `core.autocrlf` would otherwise make every copy an edit.
- `init`'s advice after APM fails says `resolve`, then `build`; the `graft-check` skill runs `resolve` after a **Patch**
  fix.
- **BREAKING** `resolve`, `update` and `add`, `remove`, `rename`, `bind`, `unbind` vendor `.apm/skills/` too, written
  together with the lock: on any failure both stay as they were. `update --dry-run` still writes nothing.
- Every command that vendors first checks `.apm/skills/` against the lock and refuses, writing nothing, on a **Vendored
  copy** whose hash differs from the lock's or a folder the lock does not list, saying to move the edit into a **Patch**
  or delete the folder. A copy the lock lists that is missing is vendored again without a word.
- `build --into <dir>` checks the **Hull** against the **Package**'s lock as `build` does, and has no copies to check.
- `CONTEXT.md` gains **Vendored copy**; ADR 0009; `docs/security.md`'s LLM03 row and Future work, `docs/design.md`, and
  `README.md`'s workflow follow.

Not in scope: making cache exports read-only (a later change), and `apm install` run outside skill-graft, which deploys
`.apm/skills/` unchecked.

## Capabilities

### New Capabilities

### Modified Capabilities

- `build`: **Build resolves first** becomes **Build deploys the lock** (the refusals, the path **Source** notice);
  **Build into a folder** checks the **Package**'s lock; new **Vendored copies match the lock** and **Vendored copies
  keep their bytes in git**.
- `resolve`: **Resolve command** vendors; **The lock is output only** is removed.
- `edit`: **Resolve before writing** vendors.
- `update`: **Resolve before writing** vendors; **Dry run writes nothing** reports the copy check's errors too, before
  contacting any remote.
- `init`: **Init registers the package with APM** says to run `resolve`, then `build`, after APM fails.
- `check`: **Fixes only once accepted** runs `resolve` after a **Patch**; **A failed fix is undone** runs it again;
  **Never deploys** no longer expects copies behind the lock.

## Impact

- `src/skill_graft/commands/transaction.py`: `resolving` checks the copies against the lock, vendors, and writes the
  copies with the lock, restoring both on failure.
- `src/skill_graft/pipeline/vendor.py`: vendoring split so the swap of `.apm/skills/` commits with the lock or undoes,
  and a killed run is recovered by which copies match the lock.
- `src/skill_graft/pipeline/lock.py`: compare a rendered lock with the lock file; the copies' check; the header.
- `src/skill_graft/commands/build.py`: the check against the lock and the path **Source** notice.
- `src/skill_graft/commands/resolve.py`, `edit.py`, `update.py`: vendoring through `resolving`; `update` checks the
  copies before fetching.
- `src/skill_graft/commands/init_package.py`: the message when APM fails after registering.
- `skills/graft-check/SKILL.md`: `resolve` after a **Patch** fix and after undoing one; the close.
- Tests: the `build` helper in `tests/conftest.py` and every test that builds from a hand-written config run `resolve`
  first; new tests in `tests/commands/test_build.py`, `test_transaction.py`, `tests/pipeline/test_lock.py`,
  `tests/pipeline/test_vendor.py`.
- `CONTEXT.md`, `docs/adr/0009-build-deploys-the-lock.md`, `docs/security.md`, `docs/design.md`, `README.md`;
  `CHANGELOG.md` at archive.
