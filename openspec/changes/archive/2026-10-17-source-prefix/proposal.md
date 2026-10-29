# Proposal

## Why

The common **Rename** namespaces a whole **Source**: this repository's own `skill-graft.toml` holds nine of the form
`"mp/tdd" = "mp-tdd"`. Worse, a **Skill** that `update` pulls into the **Hull** later deploys under its upstream name
until the user notices and adds one more key; that is how `research` and `prototype` arrived unprefixed. A **Prefix**
states the rule once per **Source** and covers every **Skill** of it, future dependencies included (ADR 0005).

## What Changes

- **Prefix**: a new source key, `prefix = "mp-"` under `[sources.mp]`, on path and git **Sources**. Every **Hull**
  **Skill** of that **Source**, **Entry** or dependency, deploys as the prefix followed by its name, carried into its
  folder, `name:` and every **Reference** (prose included) exactly as a **Rename** is. The prefix is a name
  (`[A-Za-z0-9][A-Za-z0-9._-]*`), used as written: no `-` is added.
- **Precedence**: a `[rename]` key for the **Skill** wins over its **Source**'s **Prefix**.
- **Checks on the result**: uniqueness and **Reserved names** check the prefixed **Deployed names**, so two **Sources**
  with one prefix can clash. Hints treat a prefixed name as one the user chose: they suggest a `[rename]` key only for a
  **Skill** with neither key nor **Prefix**, else name the `[rename]` value or the `prefix` to change; a prefixed
  **Skill** on a shipped **Reserved name** gets no suggestion.
- **`skill-graft rename`**: the key is removed when the new name is what the **Skill** deploys as without a key (its
  **Source**'s **Prefix** plus its name, else its name), and written otherwise. **BREAKING** only under a **Prefix**:
  `rename mp/tdd tdd` now writes `"mp/tdd" = "tdd"`, an explicit opt-out, where it used to remove the key. Without a
  **Prefix** nothing changes.

Unchanged: **Skill IDs**, **Binds** and **Patches** keep upstream names; the lock's `deployed`, the tree's
`as <deployed>` and `why`'s lookup by **Deployed name** already follow any **Deployed name** that differs from the name.
A `[rename]` key equal to the prefixed name is harmless and not warned about. No command sets a **Prefix**; the user
writes it by hand.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `config`: `prefix` becomes a supported source key, validated as a name.
- `renames`: the **Deployed name** takes the **Source**'s **Prefix** when no **Rename** names the **Skill**; clash and
  reserved-name hints account for it.
- `edit`: `rename` removes the key only when the new name is the **Skill**'s **Deployed name** without a key.

## Impact

- Changed: `config.py` (`prefix` on both source kinds, `deployed`), `rename.py` (hints), `edit.py` (`rename`'s removal
  rule), `cli.py` (`rename`'s description), `init.py` (template comment), with tests.
- `docs/design.md`, `README.md`: **Prefix** in the TOML example, the names section and `rename`.
- Once this lands, the user can replace the nine `[rename]` keys in their own `skill-graft.toml` with `prefix = "mp-"`
  and `prefix = "hl-"`; that edit is not part of this change.
