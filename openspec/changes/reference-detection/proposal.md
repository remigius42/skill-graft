# Proposal

## Why

The first real build, of `mattpocock/skills`' `tdd`, `grill-with-docs` and `retro`, missed every dependency they
have: those skills write a Skill tool call in English ("Call the Skill tool twice, for "grilling" and
"domain-modeling"."), which skill-graft reads as prose or not at all, so `grilling`, `domain-modeling`,
`codebase-design` and `writing-for-agents` were never vendored and the deployed skills point at nothing. Three of
them were found as prose suggestions, but only `resolve` shows those, and the user ran `update` and `build`. The
same build also took two paths for slash calls: `fetch('/orders')` in a code example and
`` `package.json`/build-tool `` in prose.

## What Changes

- **Skill tool sentences**: in a sentence that names the `Skill tool`, each name after it in double quotes or
  backticks is a Skill tool **Reference**: it extends the **Hull**, resolves across **Sources**, and is rewritten
  by a **Rename**, like `Skill(name)`.
- **Tighter slash references**: `/name` is no **Reference** right after `(` or `[` and `'` or `"` (a path
  argument, `fetch('/orders')`), nor right after a backtick that closes a code span (`` `package.json`/x ``).
  `` `/grilling` ``, `` (`/grilling`) ``, `'/grilling'` in prose and `cd /tmp` still count.
- **Suggestions are announced**: `build` and `update` print one line on stderr when prose names **Skills** outside
  the **Hull**, pointing to `skill-graft resolve`, which still prints them.
- `CONTEXT.md`: the **Reference** entry names the sentence form (done with this proposal).

Out of scope: negated sentences ("do not call the Skill tool with `x`"), which a **Bind** to `false` handles;
single-quoted names in a Skill tool sentence (apostrophes); prose detection.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `hull`: the Skill tool **Reference** gains the sentence form; the slash **Reference** excludes path arguments
  and a `/` after a closing code span.
- `resolve`: `build` and `update` announce prose suggestions in one line instead of staying silent.

## Impact

- `references.py` (the reference pattern and a sentence scan), `cli.py` and `update.py` (the announcement).
- Tests: synthetic skills reproducing each form; the existing reference tests stay green.
- Docs: `CONTEXT.md` (done), `docs/design.md` (reference forms), `README.md` (status line).
