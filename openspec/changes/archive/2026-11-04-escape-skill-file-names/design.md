# Design

## Context

Errors reach the user through `cli.py`, which prints `skill-graft: {error}` for a `SkillGraftError` or `OSError` (three
places), and warnings and notices through `infra/errors.warn` and `notice`. Messages are built all over the pipeline
with file names interpolated raw: `files.check_files`, `hidden.scan`, `patch.apply`'s copy failure (shutil's
`SpecialFileError` included), `_failures` and git's stderr it passes on. A few messages hold intentional line breaks:
`PatchFailed` and `PatchError` join lines, `init_package`, `transaction` and `explain` append a hint or another error
after `\n`.

`pipeline/hidden.show` already escapes each hidden or unprintable character as Python would, and is how hidden-character
findings name files. `cli.py` may import only `infra.errors` from below `commands`.

graft-check runs `LC_ALL=C diff -ruN base/ edited/ > change.patch` in section 6, its error output visible, and handles
exit 0 and 1 only. Section 7 runs `diff -rq <folder>/.apm/skills <package>/.apm/skills` and reads its output, which
names the differing files. `tests/cli/test_check.py` guards section 6's command as a constant `DIFF` it asserts
`SKILL.md` holds, then runs.

## Goals / Non-Goals

**Goals:**

- No unprintable character or **Hidden character** in any error, warning or notice reaches stderr raw, whichever message
  carries it, nor in the one line of standard output that carries an error's text.
- The main agent decides section 7, and whether section 6's diff worked, from an exit code only.

**Non-Goals:**

- The rest of standard output: `why`, `tree` and the hull summary print **Skill IDs**, whose names discovery limits to
  safe segments; the hull summary's file names are quoted as git's `core.quotePath` quotes them (`deployed.quote`), and
  the Deployed diff has its own escaping. The one exception, `update`'s `no previous hull to compare (…)`, whose reason
  holds an error's text, is escaped as stderr is.
- argparse's own usage errors, which echo what the user typed.
- Telling an escaped `\n` from a file name holding a backslash and `n`: both print the same; neither forges a line.
- Rejecting such file names: a name with a space or a line break is still vendored.
- Other invisible characters `isprintable()` passes, such as BMP variation selectors (debris to the `hidden-characters`
  capability) or U+3164: they make two names look alike, but forge no line and control no terminal. Escaping them would
  change how every hidden-character finding prints too.

## Decisions

- **Escape at the sink, not at each message.** One function prints every error, warning and notice; a message built
  anywhere, git's included, is covered. Alternative: escaping each interpolated name, rejected after two reviews each
  found paths it missed.
- **`SkillGraftError(*lines)` keeps its lines.** `str(error)` stays `"\n".join(lines)`, so the tests matching messages
  keep passing; the printer escapes each line, then joins them. A `\n` inside a line is then one an author wrote, and
  prints as `\n`. The multi-line sites pass their lines as arguments; one wrapping another error passes `*other.lines`.
  An `OSError` prints as one line. A missed multi-line site would print `\n` literally, which the existing tests of
  those messages catch. `PatchError`'s other error is a list of lines too. A notice of a failure prints a notice per
  line.
- **Text from outside put on one line with a semicolon and a space.** git's error output, of any number of lines, is
  joined so in `git.run`, as `patch._failures` already joins git's message; git itself writes each control character but
  the line feed as `?`. `update`'s reason joins an error's lines the same way.
- **Move `show` and the hidden-character table to a new `infra/text.py`.** `errors.py` and `pipeline/hidden.py` import
  it, and `deployed._escaped` builds its ranges with `text.ranges`. Alternative: put them in `errors.py`, rejected: the
  table is the hidden-character capability's, not errors'.
- **`cli.py` prints errors through a function in `errors.py`**, as the import contract allows `cli` that module alone.
- **Section 7 by exit code.** `diff -rq … >/dev/null 2>&1`: exit 0 means the same, anything else, a missing
  `<package>/.apm/skills` or trouble reading the throwaway deploy included (exit 2), means they differ. Telling the user
  to deploy once too often is harmless. Alternative: `| wc -l`, rejected: a count adds nothing the decision uses.
- **Section 6's diffs with `2>/dev/null`, exit 2 ending the fix.** GNU and BSD `diff` exit 2 on trouble, such as a
  dangling link, and name the file on stderr. The unhardened path's diff too, though its agent reads skill text anyway:
  its `>` writes into the **Package**, so a failed diff leaves a broken patch file there, which it deletes.
- **Commands guarded as constants.** Section 7's command (`CLOSE`) and the unhardened diff (`UNHARDENED`) join `DIFF` as
  constants in `test_check.py`, placeholders included, each asserted verbatim in `SKILL.md`, with its `>` and `2>`, and
  run as asserted.

## Risks / Trade-offs

- [A message's own tab or carriage return now prints escaped] → None is written on purpose today; the suite shows any.
- [An escaped name is harder to read] → Only names with hidden or unprintable characters change.
