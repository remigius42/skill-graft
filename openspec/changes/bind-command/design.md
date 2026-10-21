# Design

## Context

`edit.py` already holds `add`, `remove` and `rename`, each reading the TOML with `tomlkit`, changing one value,
and handing the document to `_finish`, which resolves it in memory and writes the TOML and the lock only on
success. `config._binds` already parses `[bind]`: keys through `parse_skill_id` (alias declared, one segment
each), values a **Skill ID** or `false`. Resolution already fails, naming the **Bind**, on a target that is
missing or ambiguous, and warns about an unused **Bind**.

## Goals / Non-Goals

**Goals:**

- `bind` and `unbind` as two more functions in `edit.py`, on the same `read` / `_finish` path as `rename`.

**Non-Goals:**

- Changing what a **Bind** means, the config format, or the lock.
- Binding several names in one call.

## Decisions

- **`false` is a word on the command line.** A **Skill ID** always holds a `/`, so the bare word `false` cannot
  be one; it is written as the TOML boolean. Alternative: a `--none` flag. Rejected: the command line would then
  differ from the TOML the user reads.
- **The target is checked before resolving**, with `resolve.known` as `rename` checks its **Skill**, so the error
  names the target the user typed, not the **Bind** key. As in `rename`, the check comes before the no-op test, so
  `bind` with a value already set but whose target is gone upstream is an error, not a notice. The key's `<name>` is
  only parsed, not looked up: `mp/tmp` binds a word that is no **Skill**.
- **`unbind`, not `bind --clear` or a default value.** `rename` undoes itself by taking the default name, but a
  **Bind** has no value that means "resolve by default". A separate command mirrors `add`/`remove`, and `remove`
  is already about **Entries**.
- **`unbind` of an unknown key is an error**, as `remove` of a non-**Entry** is: a typo should not pass as
  success. An emptied `[bind]` table stays, as `[rename]` does after an undone **Rename**.
- **A no-op `bind` is a notice** and writes nothing, as with `rename`. Comparison is on the parsed value, so
  `"own/grill"` and `own/grill` count as equal however the file quotes it. The key must also be present:
  `Config.binds` holds `false` as `None`, so `binds.get(key) == target` alone would take a missing key as
  already bound to `false`.
- **Messages suggest the command.** The unmatched-**Reference** warning ends with
  `skill-graft bind <key> false`, and the ambiguity error with `skill-graft bind <key> <source>/<name>`, so
  the fix they propose is checked when applied.
- **Every Bind's target is checked**, in `hull.walk` after the walk, with `discovery.find` on the indexes it
  already holds: no extra I/O. Rejected: a warning for an unused one. A used **Bind** to a missing **Skill** is
  already an error, and an unused one is the typo `bind` exists to catch.
- **`resolve.known` fetches only its Source.** It calls `resolve.folders` on a config narrowed to that one
  **Source**, so `rename` and `bind` no longer fetch every declared **Source** twice.
- **`unbind` parses its key** as `bind` does, so a malformed key or undeclared alias gets the same error, not
  "not bound".

## Risks / Trade-offs

- \[`unbind` can break resolution when the default is ambiguous\] → `_finish` already refuses to write, and the
  error names the ambiguous **Reference**, so the user sees why the **Bind** was there.
- \[`resolve.known` fetches and indexes the target's **Source**, and `_finish` does so again\] → accepted: the
  second fetch hits the cache, and one index is cheap next to resolving the **Hull**.
- \[A stale unused **Bind** (its target removed upstream) now stops `resolve` and `build`\] → the error names the
  **Bind**, and `skill-graft unbind` removes it.
