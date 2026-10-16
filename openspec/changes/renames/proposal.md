# Proposal

## Why

Two **Skills** from different **Sources** often share a name, and some names (`code-review`) are already taken by
the harness. Today such a **Hull** cannot be built at all. A **Rename** gives a **Skill** a new **Deployed name**
and carries it into every **Reference**, so the agent never reads a stale name; and prose **References** must
follow, or a rename leaves the text pointing at a name that no longer exists (ADR 0002).

## What Changes

- **Renames**: a new `[rename]` table, `"<skill id>" = "<deployed name>"`. `build` writes the renamed **Skill**
  to `.apm/skills/<deployed name>/`, sets its `SKILL.md` `name:` to it (APM requires `name:` to equal the folder),
  and rewrites every slash, Skill tool and prose **Reference** to it in every Markdown file of every **Hull**
  **Skill**. A rename that names no **Hull** **Skill** is a warning.
- **Bound References follow too**: a **Reference** whose written name differs from its target's **Deployed
  name**, renamed or bound (`"mp/grilling" = "own/grill"`), is rewritten to that **Deployed name**. Today a bound
  `/grilling` deploys pointing at nothing.
- **Prose References**: a backticked name (`` `grilling` ``) or a bare hyphenated one (`diagnosing-bugs`).
  It resolves only in its own **Source**, **Binds** applied, and never extends the **Hull**. Inside the **Hull**
  it is an edge of kind `prose` and is rewritten on rename; outside it `resolve` suggests adding the **Skill** to
  `entries`; matching nothing, it is no **Reference** (no warning).
- **Reserved names**: a list skill-graft ships (the built-in commands and bundled skills of Claude Code and Codex,
  such as `code-review`) gives a warning with the `[rename]` line that would avoid it; the user's new top-level
  `reserved = [...]` gives an error. **Deployed names**, after renames, stay unique across the **Hull** (ignoring
  case); a clash error now names a `[rename]` line too.
- **Lock and tree**: the lock records each renamed **Skill**'s `deployed` name, `prose` edges, and the prose
  suggestions; hashes cover the rewritten files, the same for `resolve` and `build`. The tree marks renamed
  **Skills** (`mp/grilling as mp-grilling (/grilling)`) and shows the prose edges it rewrites; `resolve` lists the
  suggestions after it.

Out of scope: **Patches**, `why` and `tree`, the `add` and `rename` commands (until `add` exists, a suggestion
says to add the **Skill ID** to `entries`), and any finer escape than a `false` **Bind** for a false prose match.

## Capabilities

### New Capabilities

- `renames`: **Deployed names**: rewriting folder, `name:` and **References**; **Reserved names**; uniqueness.

### Modified Capabilities

- `config`: `[rename]` and `reserved` become supported.
- `hull`: prose **References**: detection, own-**Source** resolution, **Binds**, used-**Bind** accounting.
- `resolve`: lock records renames, prose edges and suggestions; tree marks renames and lists suggestions.
- `build`: vendors under **Deployed names**; the uniqueness requirement moves to `renames`.

## Impact

- New: `src/skill_graft/rename.py` (**Deployed names**, reserved list, rewrites), with tests.
- Changed: `config.py` (`[rename]`, `reserved`), `references.py` (prose form, spans), `hull.py` (prose
  resolution, suggestions, every resolved occurrence kept for rewriting), `resolve.py` (name checks move to
  `rename.py`), `vendor.py` (deployed folder, rewritten files), `lock.py` (deployed, prose, suggestions, hash of
  the rewritten copy, tree), `cli.py` (suggestions printed; `build` no longer hashes the copies), `update.py`
  (lock and hull diff hash the rewritten bytes).
- `docs/design.md`, `README.md`: renames and prose built; the reserved list.
- Behavior: a bound **Reference** naming a different **Skill** name is now rewritten in the vendored copy, so
  lock hashes of such **Skills** change once. A **Skill** whose name is in the shipped reserved list now warns on
  every `resolve` and `build`.
