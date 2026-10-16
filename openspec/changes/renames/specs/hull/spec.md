# Spec Delta

## ADDED Requirements

### Requirement: Prose references

A prose **Reference** SHALL be a code span whose whole content is a name (`` `grilling` ``), or a bare hyphenated
token `[a-z0-9]+(-[a-z0-9]+)+` standing as its own token: not preceded by a letter, digit, `/`, `.`, `-`, `~`,
`:`, `\`, `<` or `@`, and not followed by a letter, digit, `/`, `-`, or `.` or `:` and a letter or digit. It
SHALL count anywhere, code blocks included, and never inside a slash or Skill tool **Reference**.

#### Scenario: Backticked and hyphenated

- **WHEN** a **Skill**'s Markdown holds `` use `grilling` ``, `then diagnosing-bugs.`, or `pre-commit run` in a
  fenced block
- **THEN** `grilling`, `diagnosing-bugs` and `pre-commit` are prose **References**

#### Scenario: Not prose

- **WHEN** it holds `grilling` unquoted, `` `grilling --fast` ``, `` `mp/grilling` ``, `--dry-run`,
  `refs/red-green.md`, `x-ray.png` or `https://x.org/my-skill`
- **THEN** none is a prose **Reference**

#### Scenario: Slash form wins

- **WHEN** it holds `` `/grilling` `` or `Skill(diagnosing-bugs)`
- **THEN** each is one slash or Skill tool **Reference**, and no prose **Reference**

### Requirement: Prose resolves in its own source only

A prose **Reference** from a **Skill** in **Source** `a`, unless a **Bind** decides it, SHALL resolve to `a/<name>`
only when `a` has a **Skill** whose name is read, valid and equal to `<name>`; otherwise it is no **Reference**:
no edge, no warning, no error. It SHALL never extend the **Hull**: when its target is in the **Hull** it is an
edge of kind `prose`, otherwise a suggestion.

#### Scenario: Inside the hull

- **WHEN** `mp/tdd` calls `/grilling` and mentions `` `notes` ``, and `mp` has `grilling` and `notes`, with
  `mp/notes` an **Entry**
- **THEN** the **Hull** has a `prose` edge `mp/tdd` → `mp/notes`

#### Scenario: Outside the hull

- **WHEN** `mp/tdd` mentions `diagnosing-bugs`, `mp` has `diagnosing-bugs`, and nothing calls it
- **THEN** `mp/diagnosing-bugs` is not in the **Hull**, and is suggested as mentioned by `mp/tdd`

#### Scenario: Only another source has it

- **WHEN** `mp/tdd` mentions `` `notes` ``, `mp` has no `notes`, and `own` has one
- **THEN** it is no **Reference**: no edge, no suggestion, no warning

#### Scenario: Matches nothing

- **WHEN** `mp/tdd` mentions `red-green-refactor`, and no **Source** has such a **Skill**
- **THEN** the command prints nothing about it

## MODIFIED Requirements

### Requirement: Binds override resolution

A **Bind** `"<a>/<name>" = "<b>/<target>"` SHALL make every slash, Skill tool and prose **Reference** to `<name>`
from a **Skill** in **Source** `a` resolve to `b/<target>`, whatever the default would give, error or no match
included. Its target SHALL be found as an **Entry** is; a missing or ambiguous one is an error naming the
**Bind**. A bound prose **Reference** still never extends the **Hull**.

#### Scenario: Bind across sources

- **WHEN** `mp/tdd` calls `/grilling`, `mp` has `grilling`, and `[bind]` has `"mp/grilling" = "own/grill"`
- **THEN** `own/grill` is in the **Hull** and `mp/grilling` is not

#### Scenario: Bind settles ambiguity

- **WHEN** `/notes` from `mp` would match `own/notes` and `x/notes`, and `[bind]` has `"mp/notes" = "x/notes"`
- **THEN** `x/notes` is in the **Hull**, and the command succeeds

#### Scenario: Bind to a missing skill

- **WHEN** `[bind]` has `"mp/grilling" = "own/nope"`, a **Hull** **Skill** in `mp` calls `/grilling`, and `own`
  has no `nope`
- **THEN** the command exits non-zero naming `mp/grilling` and `own/nope`

#### Scenario: Bound prose

- **WHEN** `mp/tdd` mentions `` `notes` ``, `mp` has no `notes`, `[bind]` has `"mp/notes" = "own/notes"`, and
  `own/notes` is in the **Hull**
- **THEN** the **Hull** has a `prose` edge `mp/tdd` → `own/notes` with `bind = true`

#### Scenario: Bound prose outside the hull

- **WHEN** `mp/tdd` only mentions `` `notes` ``, and `[bind]` has `"mp/notes" = "own/notes"`
- **THEN** `own/notes` is not in the **Hull**, and is suggested

#### Scenario: Prose bound to nothing

- **WHEN** `mp/tdd` holds `pre-commit run`, `mp` has `pre-commit`, and `[bind]` has `"mp/pre-commit" = false`
- **THEN** it is no **Reference**: no edge and no suggestion

### Requirement: Unused binds warn

A **Bind** that no **Reference** from a **Hull** **Skill** uses, prose included, SHALL be a warning naming its key.

#### Scenario: Typo in a bind

- **WHEN** `[bind]` has `"mp/grill" = "own/grilling"` and no **Hull** **Skill** in `mp` calls `/grill`
- **THEN** the command warns that `mp/grill` binds no **Reference**, and succeeds

#### Scenario: Used by prose only

- **WHEN** `[bind]` has `"mp/notes" = "own/notes"` and a **Hull** **Skill** in `mp` only mentions `` `notes` ``
- **THEN** the command gives no warning about that **Bind**
