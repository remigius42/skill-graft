# Regexes over Upstream text run in linear time

**Upstream** text is untrusted (ADR 0007), and a regex that backtracks lets a **Source** stall every command that reads
it: a `name:` line holding 100 000 spaces once took the comment pattern 26 s. So every regex skill-graft runs over
**Upstream** text runs in linear time in its input, by construction: possessive quantifiers and atomic groups where a
run must not be given back, a lookbehind so a try starts only where a run starts, and no nested quantifier over text
that two branches can both match. `tests/cli/test_linear_time.py` keeps it: an entry per pattern times the call the code
makes on inputs of about 100 000 characters shaped to make it backtrack, under one second, and a guard fails on a
module-level pattern of those modules without an entry, and on an entry naming no pattern. A pattern compiled inside a
function the guard cannot see; it gets its entry by hand, as `deployed._escaped` does. The **Deployed diff**'s 1 MB cap
stays: it bounds the diff's own work, not a pattern's.

## Considered Options

- Size caps on the files or lines patterns read: users see them, and they hide a quadratic pattern rather than remove
  it.
- The `regex` module's match timeout: a second runtime dependency.
- A subprocess per match, with a timeout: costly, and a timeout is still a failure the user sees.
