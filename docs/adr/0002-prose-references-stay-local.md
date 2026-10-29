# Prose references stay in their own source

Only slash and Skill tool references extend the hull and look across sources. A prose reference (a backticked or
hyphenated name) resolves only in its own source and never pulls a skill in: whether `review` means a skill or the
action cannot be told from the text, and no pack author writes prose hoping a word happens to match a skill from someone
else's pack. Prose still matters for renames, so inside the hull it is rewritten, and outside it skill-graft suggests
the skill rather than adding it.

## Considered Options

- Follow prose like slash references: pulls in skills on false positives (`pre-commit`, `red-green-refactor`).
- Ignore prose entirely: a rename leaves stale names in the text the agent reads.
