# Proposal

## Why

In a hardened **Check**, a reader's reply reaches the main agent whole, as the output of the Bash call that ran it. The
report shape and the 200-character bound on `text` and `vendored` are rules of the reader's own prompt, kept by the one
agent that reads injected text: a hijacked reader can send any length and any lines, and `docs/security.md` lists it as
a residual risk "at the prompt level only". The patcher's reply already goes to a file the main agent never opens; the
readers' should be held to their shape by code too.

## What Changes

- Each reader's stdout and stderr go to their own `mktemp` files, outside its working folder; the main agent never opens
  either. This holds for step 4's readers and step 5's `uses` readers alike; the probe is unchanged.
- On exit 0, a new `skills/graft-check/report-filter.sh`, run as
  `sh <report-filter.sh> <mode> <skill id> <name>… < <reply file>`, prints the report it admits, or exits 1. Only it
  reads the reply.
- It admits `key: value` lines in the report shape, in the order `reader.json` asks for: a finding (`skill`, `file`,
  `text`, `vendored` when the build caused it, `kind`, `why`), in `full` mode only; a use (`use`, `file`, `line`,
  `text`, `means`); and `findings: none` and `uses: none`, on lines of their own; at most 100 findings and 200 uses,
  caps `reader.json` states. A finding's `skill` must be the **Skill ID** that reader was given, a use's name one of the
  `names` it was given, as written there, `kind` one of the five, `line` at most 6 digits, `means` a **Skill ID** or
  `none`.
- Every value is printable ASCII, at most 200 characters. In `text`, `vendored`, `why` and `file`, each non-ASCII
  character becomes `?`, each control character too, and a longer value becomes its first 197 and `...`.
- A reply with any other line, key or value is not in the report shape: that **Skill** is named as having no report,
  with the fixed reason `not in the report shape`, and no part of the reply is shown. A filter exiting otherwise than 0
  or 1 ends the **Check**, naming its exit code.
- A reader that exits non-zero leaves its **Skill** with no report, as before, and the skill now shows why: the first
  line of its stderr, else of its stdout, in printable ASCII, at most 200 characters, as quoted text, as it does for the
  patcher.
- `reader.json` writes a use's name as `names` gives it, and states both caps. Step 6's patcher prompt says a `?` in a
  report's `file` or `text` may stand for a replaced character.
- `docs/security.md`: Residual risks and the LLM05 row say that report text is held to its shape and bound in code, and
  that visible injection in a quoted value, short and shown, still reaches the main agent. The probe, which reads no
  **Skill** text, and an unhardened **Check**, which reads in the main agent's own session, are unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `check`: new requirements "Reader replies pass a report filter" and "A failed reader shows why"; "The main agent never
  reads skill text" holds of each reader only what the filter admits or its error line, and never opens its output.

## Impact

- `skills/graft-check/report-filter.sh` (new), `skills/graft-check/SKILL.md` (the quarantine paragraph, the shipped
  files, steps 4, 5 and 6), `skills/graft-check/reader.json` (the spelling of `use`, the caps).
- `tests/cli/test_check.py`: the filter run on hostile and well-formed replies; step 4's and step 5's readers send their
  output to files; the skill installs alone in its **Hull** with the new file.
- `docs/security.md`, the README's Security section.
- `CHANGELOG.md` entry at archive.
