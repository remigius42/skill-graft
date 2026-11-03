# Spec Delta

## ADDED Requirements

### Requirement: Error output shows no hidden characters

Every error line, warning and notice skill-graft prints on standard error, and the reason `update` prints on standard
output when it has no previous **Hull** to compare, SHALL write each unprintable character and each **Hidden character**
escaped as in a Python string literal: a line feed as `\n`, an escape as `\x1b`, a bidi override as `\u` and its code
point. Only the line breaks skill-graft itself puts between the lines of one message SHALL be printed as line breaks.
Text that holds none of them SHALL print as before.

#### Scenario: Terminal escape in a link name

- **WHEN** a **Hull** **Skill** holds a symlink named `a`, a line feed, then `\x1b[31mok` (an escape), leading outside
  the **Skill**, and the user runs `skill-graft resolve`
- **THEN** the command exits non-zero, its error one line naming `a\n\x1b[31mok` as pointing outside the **Skill**, with
  no line feed in the name and no escape character

#### Scenario: Unreadable file named with a line break

- **WHEN** a **Hull** **Skill** holds an unreadable file named `a`, a line feed, then `skill-graft: done`
- **THEN** the command exits non-zero, its error one line naming `a\nskill-graft: done`

#### Scenario: git's message passed on

- **WHEN** a **Patch** changes a file whose name holds an escape, which the **Upstream** folder no longer has, so git
  refuses it whole
- **THEN** the error passes on git's message, holding no escape character

#### Scenario: Lines of one message kept

- **WHEN** two of a patch's three hunks no longer apply
- **THEN** the error prints `patches do not apply:` and each failing hunk on a line of its own, as before

#### Scenario: No previous hull to compare

- **WHEN** a git **Source**'s locked ref holds a symlink named `a`, a line feed, then `\x1b[31mok`, leading to no file,
  and a later commit removes it, and the user runs `skill-graft update`
- **THEN** its line `no previous hull to compare (…)` is one line naming `a\n\x1b[31mok`, with no escape character

#### Scenario: Safe names unchanged

- **WHEN** a **Hull** **Skill** in a path **Source** under `My Skills` holds `notes.md` as a symlink leading outside it
- **THEN** the error names `My Skills` and `notes.md` as they are
