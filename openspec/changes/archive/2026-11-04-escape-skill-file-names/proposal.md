# Proposal

## Why

The names of files inside a **Skill** are chosen by its author, and skill-graft's errors pass them on unescaped: a
refused symlink or special file, a file that cannot be read or copied, a failing hunk, git's own message. A name holding
a line break or terminal escape can forge output lines or recolor the user's terminal. Escaping message by message
misses paths, so the escaping belongs where the output is printed. graft-check's closing `diff -rq`, and the error
output of its patch diff, show file names to the main agent, which by the `check` capability must never hold text an
author or the patcher chose.

## What Changes

- Every error line, warning and notice on standard error writes each unprintable character and **Hidden character**
  escaped, as in a Python string literal (`\n`, `\x1b`, or `\u` and four hex digits). Line breaks between the lines of
  one multi-line message stay; git's error output, of any number of lines, prints on one.
- `update`'s `no previous hull to compare (…)` on standard output, whose reason holds an error's text, is escaped the
  same way.
- graft-check's closing comparison of the first throwaway deploy with the **Package** reads only `diff -rq`'s exit code,
  a failure counting as a difference.
- graft-check's patch diff shows the main agent no error output, and a diff that fails ends that fix, unhardened too.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cli`: a new requirement, "Error output shows no hidden characters".
- `check`: "The main agent never reads skill text": the closing comparison returns no file name. "Patches are written by
  a confined patcher": the diff's error output never reaches the main agent, and a failing diff ends the fix.
  "Unhardened only on the user's yes": a failing unhardened diff ends the fix, its patch file deleted.

## Impact

- `src/skill_graft/infra/errors.py`: `SkillGraftError` keeps its message's lines; the error line, `warn` and `notice`
  print them escaped.
- A new `src/skill_graft/infra/text.py`: the hidden-character table and `show`, moved from `pipeline/hidden.py`.
- `src/skill_graft/cli.py`: prints its error lines through `errors`.
- `src/skill_graft/infra/git.py`: git's error output on one line.
- `src/skill_graft/commands/review.py` and `commands/update.py`: the reason for no previous **Hull**, escaped and on one
  line.
- The multi-line errors pass their lines: `pipeline/patch.py`, `pipeline/hull.py`, `commands/init_package.py`,
  `commands/transaction.py`, `commands/explain.py`.
- `skills/graft-check/SKILL.md`: section 6's patch diffs, hardened and not, and section 7's comparison.
- Tests: `tests/infra/test_errors.py`, `tests/infra/test_git.py`, `tests/commands/test_update.py`,
  `tests/commands/test_transaction.py`, a new `tests/cli/test_error_output.py`, and `tests/cli/test_check.py`; existing
  tests keep passing.
