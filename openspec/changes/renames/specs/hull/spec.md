# Spec Delta

## ADDED Requirements

### Requirement: Prose references

A prose **Reference** SHALL be a code span whose whole content is a name (`` `grilling` ``), or a bare hyphenated
token `[a-z0-9]+(-[a-z0-9]+)+` standing as its own token: not preceded by a letter, digit, `_`, `/`, `.`, `-`,
`~`, `:`, `\`, `<`, `@`, `#`, `=`, `?`, `&`, `$` or `](`, and not followed by a letter, digit, `_`, `/`, `-`, or
`.` or `:` and a letter or digit. It SHALL count anywhere, code blocks included, except the value of `SKILL.md`'s
front matter `name:`, and never inside a slash or Skill tool **Reference**.

#### Scenario: Backticked and hyphenated

- **WHEN** a **Skill**'s Markdown holds `` use `grilling` ``, `then diagnosing-bugs.`, or `pre-commit run` in a
  fenced block
- **THEN** `grilling`, `diagnosing-bugs` and `pre-commit` are prose **References**

#### Scenario: Not prose

- **WHEN** it holds `grilling` unquoted, `` `grilling --fast` ``, `` `mp/grilling` ``, `--dry-run`,
  `refs/red-green.md`, `x-ray.png`, `[see](my-skill)`, `[x](#my-skill)`, `id="my-skill"`, `foo_my-skill`,
  `?q=my-skill` or `https://x.org/my-skill`
- **THEN** none is a prose **Reference**

#### Scenario: Own name line

- **WHEN** `mp/code-review`'s `SKILL.md` front matter has `name: code-review`, and `[bind]` has
  `"mp/code-review" = "own/review"`
- **THEN** that line is no **Reference**, and the vendored `name:` stays `code-review`

#### Scenario: Slash form wins

- **WHEN** it holds `` `/grilling` `` or `Skill(diagnosing-bugs)`
- **THEN** each is one slash or Skill tool **Reference**, and no prose **Reference**

### Requirement: Prose resolves in its own source only

A prose **Reference** from a **Skill** in **Source** `a`, unless a **Bind** decides it, SHALL resolve to `a/<name>`
only when exactly one **Skill** in `a` is named `<name>`, and no **Skill** there with an unreadable name sits in a
folder so named; otherwise it is no **Reference**:
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

#### Scenario: Ambiguous in its own source

- **WHEN** `mp/tdd` mentions `diagnosing-bugs`, and `mp` has two **Skills** named `diagnosing-bugs`
- **THEN** it is no **Reference**: no edge, no suggestion, no warning

#### Scenario: Matches nothing

- **WHEN** `mp/tdd` mentions `red-green-refactor`, and no **Source** has such a **Skill**
- **THEN** the command prints nothing about it

## MODIFIED Requirements

### Requirement: Every Markdown file

**References** SHALL be read from every file ending in `.md` (any case) in the **Skill**'s folder, at any depth,
`.git` excepted, once the **Skill**'s symlinks are checked and any file that is not a regular file, folder or
symlink (a FIFO, socket or device) is refused as an error naming it. A Markdown file that is not UTF-8 SHALL be skipped
with a warning naming it; it is still vendored. One that cannot be read at all, a dangling link included, SHALL be
an error naming it. A **Reference** that resolves, **Binds** applied, to the referencing **Skill** SHALL give no
edge, and is still rewritten as the `renames` capability says.

#### Scenario: Reference in a sibling file

- **WHEN** `mp/tdd`'s `refs/loop.md` holds `/grilling`, and its `SKILL.md` does not
- **THEN** `mp/grilling` is in the **Hull**

#### Scenario: Not UTF-8

- **WHEN** a **Hull** **Skill**'s `notes.md` holds invalid UTF-8
- **THEN** the command warns naming `notes.md`, finds no **References** in it, and succeeds

#### Scenario: Symlink to a device

- **WHEN** a **Skill** reached from an **Entry** holds `x.md` as a symlink to `/dev/zero`
- **THEN** the command exits non-zero naming `x.md` as pointing outside the **Skill**, without reading it

#### Scenario: Dangling link

- **WHEN** a **Hull** **Skill** holds `notes.md` as a symlink to a missing `gone.md` inside it
- **THEN** the command exits non-zero naming `notes.md`, without a traceback, and writes nothing

#### Scenario: Special file

- **WHEN** a **Hull** **Skill** holds a FIFO named `pipe`
- **THEN** `resolve` and `build` exit non-zero naming `pipe` as not a regular file, without reading it

#### Scenario: Self-reference

- **WHEN** `mp/tdd` holds `/tdd`, and no **Bind** names `mp/tdd`
- **THEN** the **Hull** gets no edge from `mp/tdd` to itself

#### Scenario: Bound self-reference

- **WHEN** `mp/tdd` holds `/tdd`, and `[bind]` has `"mp/tdd" = "own/tdd"`
- **THEN** `own/tdd` is pulled in, and the command exits non-zero as `mp/tdd` and `own/tdd` share a **Deployed
  name**

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
