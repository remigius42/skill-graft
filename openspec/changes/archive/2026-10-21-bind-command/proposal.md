# Proposal

## Why

`add`, `remove` and `rename` edit `skill-graft.toml` only once the result resolves, but a **Bind** is still written by
hand, so a typo shows up only at the next `resolve`. The coming `graft-check` skill proposes **Binds** as fixes and
should apply each one through a command that refuses what does not resolve, not by editing the TOML itself.

## What Changes

- `skill-graft bind <alias>/<name> <skill-id>`: sets `[bind]."<alias>/<name>"` to the **Skill ID**, so every
  **Reference** to `<name>` from **Source** `<alias>` resolves to it.
- `skill-graft bind <alias>/<name> false`: sets it to `false`, so `<name>` from that **Source** is no **Reference**.
- `skill-graft unbind <alias>/<name>`: deletes the key, so the default resolution applies again.
- Both behave as `rename` does: resolve the edited config in memory, and only if that succeeds write the TOML in place
  (comments and formatting kept), then the lock, and print the tree. Neither builds. `bind` with the value already set
  is a notice and writes nothing; `unbind` of a key not in `[bind]` is an error, as `remove` of a non-**Entry** is.
- The unmatched-**Reference** warning and the ambiguity error suggest the `bind` command instead of a `[bind]` line to
  write by hand.
- Resolution checks the target of every **Bind**, not only of those a **Reference** uses, so a hand-written typo fails
  the next `resolve` even when the **Bind** is unused.
- Both are listed in the help and print the `package:` line, as the other writing commands do.

Out of scope: the `graft-check` skill itself (a later change), and commands for **Patches**.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `edit`: adds **Bind** and unbind to the commands that edit `skill-graft.toml` after resolving.
- `cli`: the top-level help lists `bind` and `unbind`.
- `scope`: `bind` and `unbind` name the **Package** as the other writing commands do.
- `hull`: the unmatched-**Reference** warning and the ambiguity error suggest `skill-graft bind`; every **Bind**'s
  target is checked, used or not.

## Impact

- `src/skill_graft/edit.py`, `src/skill_graft/cli.py`, `src/skill_graft/hull.py` (messages, target check); tests in
  `tests/test_edit.py`, `tests/test_cli.py`, `tests/test_hull.py` and those pinning the messages.
- `docs/design.md`: the command list, the passage that says no command edits binds, the no-op edits, and the
  unmatched-**Reference** warning's text.
- `README.md` and `docs/design.md` command lists; `.cspell.yaml` gets `unbind`.
- No change to the config format or the lock. A config with an unused **Bind** to a missing **Skill**, which resolved
  with a warning, now fails.
