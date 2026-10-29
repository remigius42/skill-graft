# hull Specification

## Purpose

Finds the slash, Skill tool and prose **References** in each **Skill**, resolves them to **Skills**, and spans the
**Hull**: the **Entries** plus every **Skill** the slash and Skill tool ones reach.

## Requirements

### Requirement: Slash references

A slash **Reference** SHALL be `/` then a name, the longest run of `[A-Za-z0-9._-]` starting with a letter or digit,
trailing `.` dropped, standing as its own token: not preceded by a letter, digit, `/`, `.`, `-`, `~`, `:`, `\`, `<`,
`@`, `}`, `](`, `="` or `='`, nor by `"` or `'` right after `(` or `[`, nor by a backtick that closes a code span (an
odd number of backtick runs before it on its line), and not followed by `/`, or `:` and a letter or digit. It SHALL
count anywhere, code blocks included.

#### Scenario: Standalone token

- **WHEN** a **Skill**'s Markdown holds `run /grilling.`, `` `/grilling` ``, `(/grilling)`, `` (`/grilling`) ``,
  `run '/grilling'`, `**/grilling**`, `Run "/tdd", "/grilling"`, `` 运行`/grilling` `` or ``` ``/grilling`` ```
- **THEN** each is a slash **Reference** to `grilling`

#### Scenario: Paths and URLs

- **WHEN** it holds `/usr/bin`, `src/grilling`, `https://x.org/grilling`, `~/grilling`, `</grilling>`,
  `/plugin:grilling`, `/my-dir/file`, `/tmp.d/x`, `[docs](/docs)`, `href="/about"` or `"@/utils"`
- **THEN** none is a **Reference**, nor is any prefix of a name in them

#### Scenario: Path arguments

- **WHEN** it holds `fetch('/orders')`, `open("/grilling")`, `["/a"]` or `${id}/orders`
- **THEN** none is a slash **Reference**

#### Scenario: After a code span

- **WHEN** it holds `` its `package.json`/build-tool scripts `` or `` `lint`/check ``
- **THEN** neither `build-tool` nor `check` is a slash **Reference**

### Requirement: Skill tool references

A Skill tool **Reference** SHALL be the call form `Skill(<name>)`: the name first, optionally quoted with `"` or `'`,
optionally given as `skill=<name>` or `skill: <name>`, then `)` or `,` and further arguments, with optional whitespace
inside the parentheses. It SHALL also be each name in double quotes or backticks, the whole quoted text a name (one
trailing `.` dropped), between `Skill tool` (or `` `Skill` tool ``, as words of their own) and the end of its sentence,
when it resolves to a **Skill**; one that resolves to none, to several, or to a **Skill** whose name cannot be read is
no **Reference**: no edge, no warning, no error. A name inside a `Skill(...)` call is that call's only. The sentence
form uses the rules below.

The sentence SHALL end at the next `Skill tool`; at a blank line; at a line opening a list item, heading, code fence or
table row; or at `.`, `!` or `?` (not the `.` of `e.g.` or `i.e.`), closing quotes, backticks, `*`, `)` or `]` allowed
after it, then whitespace and an uppercase letter, a quote, a backtick, `*`, `(` or `[`, or the end of the file. A line
break alone SHALL NOT end it. The SKILL.md front matter's own `name:` line holds no such name.

#### Scenario: Call forms

- **WHEN** a **Skill**'s Markdown holds `Skill(grilling)`, `Skill("grilling")`, `Skill(skill: "grilling")` or
  `Skill(skill: "grilling", args: "x")`
- **THEN** each is a Skill tool **Reference** to `grilling`

#### Scenario: Sentence form

- **WHEN** it holds `Call the Skill tool twice, for "grilling" and "domain-modeling".`, and its **Source** has both
- **THEN** it holds one Skill tool **Reference** each to `grilling` and `domain-modeling`

#### Scenario: Backticked name in a sentence

- **WHEN** it holds `` Call the Skill tool with `writing-for-agents` for the style guide. ``
- **THEN** it is a Skill tool **Reference** to `writing-for-agents`, and no prose **Reference**

#### Scenario: Sentence across lines

- **WHEN** it holds `call the Skill tool with` at the end of one line and `"codebase-design" for the vocabulary.` on the
  next
- **THEN** it is a Skill tool **Reference** to `codebase-design`, and no prose **Reference**

#### Scenario: Sentence ends

- **WHEN** it holds `` Use the Skill tool. Then see "grilling" and `notes`. ``,
  `` (Use the Skill tool.) Then `notes`. ``, or the sentence's line is followed by a list item `` - `grilling` `` or a
  code fence
- **THEN** `grilling` in quotes is no **Reference**, and the backticked names are prose **References**

#### Scenario: Not a sentence end

- **WHEN** it holds `Call the Skill tool, e.g. with "grilling" or "domain-modeling."`
- **THEN** it holds Skill tool **References** to `grilling` and `domain-modeling`

#### Scenario: Unresolved name

- **WHEN** it holds `Call the Skill tool with "grilling" and set mode to "fast".`, and no **Source** has `fast`, or two
  other **Sources** both have it
- **THEN** it holds a Skill tool **Reference** to `grilling` only, and no warning or error names `fast`

#### Scenario: One reference per name

- **WHEN** it holds `If the Skill tool fails, call the Skill tool again with "grilling".` or
  `Call the Skill tool: Skill("grilling").`
- **THEN** it holds exactly one Skill tool **Reference** to `grilling`

#### Scenario: Unquoted name

- **WHEN** it holds `call the Skill tool with grilling.`, `MySkill tool with "grilling".` or
  `Skill tooling with "grilling".`
- **THEN** it holds no Skill tool **Reference**

#### Scenario: Renamed

- **WHEN** `mp/tdd` holds `Call the Skill tool with "grilling".`, and `mp/grilling` is renamed to `mp-grilling`
- **THEN** the vendored `mp/tdd` reads `Call the Skill tool with "mp-grilling".`

### Requirement: Names match exactly

A **Reference** name SHALL match a **Skill** name, and a **Bind** key, case-sensitively.

#### Scenario: Different case

- **WHEN** `mp/tdd` calls `/Grilling`, and the only **Skill** of that name in any **Source** is `grilling`
- **THEN** the command warns that no declared source has a skill `Grilling`

### Requirement: Every Markdown file

**References** SHALL be read from every file ending in `.md` (any case) in the **Skill**'s folder, at any depth, `.git`
excepted, once the **Skill**'s symlinks are checked and any file that is not a regular file, folder or symlink (a FIFO,
socket or device) is refused as an error naming it. A Markdown file that is not UTF-8 SHALL fail resolution, naming it,
as the `hidden-characters` capability says. One that cannot be read at all, a dangling link included, SHALL be an error
naming it. A **Reference** that resolves, **Binds** applied, to the referencing **Skill** SHALL give no edge, and is
still rewritten as the `renames` capability says.

#### Scenario: Reference in a sibling file

- **WHEN** `mp/tdd`'s `refs/loop.md` holds `/grilling`, and its `SKILL.md` does not
- **THEN** `mp/grilling` is in the **Hull**

#### Scenario: Not UTF-8

- **WHEN** a **Hull** **Skill**'s `notes.md` holds invalid UTF-8
- **THEN** the command exits non-zero naming `notes.md` as not UTF-8, and writes nothing

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
- **THEN** `own/tdd` is pulled in, and the command exits non-zero as `mp/tdd` and `own/tdd` share a **Deployed name**

### Requirement: Resolve in the own source first

A slash or Skill tool **Reference** from a **Skill** in **Source** `a` SHALL resolve to `a/<name>` when `a` has a
**Skill** of that name, whatever other **Sources** hold.

#### Scenario: Own source wins

- **WHEN** `mp/tdd` calls `/grilling`, and both `mp` and `own` have a **Skill** `grilling`
- **THEN** `mp/grilling` is in the **Hull** and `own/grilling` is not

### Requirement: Else exactly one other source

When the own **Source** lacks the name, the **Reference** SHALL resolve in the one other declared **Source** having it.
Several SHALL be an error naming the referencing **Skill**, the **Reference**, the matching **Skill IDs**, and the
`skill-graft bind` command that would settle it. A **Source** has a name when a **Skill** there is named so, or one
whose name cannot be read sits in a folder so named; a name read but invalid never counts.

#### Scenario: One other source

- **WHEN** `mp/tdd` calls `/notes`, `mp` has no `notes`, and only `own` has one
- **THEN** `own/notes` is in the **Hull**

#### Scenario: Invalid name does not count

- **WHEN** `mp/tdd` calls `/grilling`, `mp`'s folder `grilling/` has `name: "Grilling Tool"`, and `own` has `grilling`
- **THEN** `own/grilling` is in the **Hull**

#### Scenario: Several other sources

- **WHEN** `mp/tdd` calls `/notes`, `mp` has no `notes`, and both `own` and `x` have one
- **THEN** the command exits non-zero naming `mp/tdd`, `/notes`, `own/notes`, `x/notes` and
  `skill-graft bind mp/notes <source>/<name>`, and writes nothing

### Requirement: Unmatched references warn

A slash or Skill tool **Reference** matching no **Skill** in any declared **Source**, and no **Bind**, SHALL be a
warning `` `<skill id>` calls `<reference>`: no declared source has a skill `<name>` ``, the **Reference** as first
written (`/<name>` or `Skill(<name>)`), ending with the `skill-graft bind` command that would ignore it, once per
referencing **Skill** and name, and the command SHALL proceed.

#### Scenario: No such skill

- **WHEN** `mp/tdd` calls `/foo` twice, and no **Source** has a **Skill** `foo`
- **THEN** the command prints `` `mp/tdd` calls `/foo`: no declared source has a skill `foo` `` and
  `skill-graft bind mp/foo false` once, and succeeds

#### Scenario: Skill tool form named

- **WHEN** `mp/tdd` holds only `Skill(foo)`, and no **Source** has `foo`
- **THEN** the warning says `` `mp/tdd` calls `Skill(foo)` ``

### Requirement: Binds to nothing

A **Bind** `"<a>/<name>" = false` SHALL make `<name>` from any **Skill** in **Source** `a` no **Reference**: it adds no
**Skill** or edge and gives no warning, whether a **Skill** of that name exists or not.

#### Scenario: Path in a code block

- **WHEN** `mp/tdd` holds `cd /tmp` in a fenced block, and `[bind]` has `"mp/tmp" = false`
- **THEN** the command prints no warning about `tmp`

#### Scenario: Unwanted match

- **WHEN** `mp/tdd` calls `/tmp`, `own` has a **Skill** `tmp`, and `[bind]` has `"mp/tmp" = false`
- **THEN** `own/tmp` is not in the **Hull**

### Requirement: Binds override resolution

A **Bind** `"<a>/<name>" = "<b>/<target>"` SHALL make every slash, Skill tool and prose **Reference** to `<name>` from a
**Skill** in **Source** `a` resolve to `b/<target>`, whatever the default would give, error or no match included. The
target of every **Bind**, whether a **Reference** uses it or not, SHALL be found as an **Entry** is; a missing or
ambiguous one is an error naming the **Bind**. A bound prose **Reference** still never extends the **Hull**.

#### Scenario: Bind across sources

- **WHEN** `mp/tdd` calls `/grilling`, `mp` has `grilling`, and `[bind]` has `"mp/grilling" = "own/grill"`
- **THEN** `own/grill` is in the **Hull** and `mp/grilling` is not

#### Scenario: Bind settles ambiguity

- **WHEN** `/notes` from `mp` would match `own/notes` and `x/notes`, and `[bind]` has `"mp/notes" = "x/notes"`
- **THEN** `x/notes` is in the **Hull**, and the command succeeds

#### Scenario: Bind to a missing skill

- **WHEN** `[bind]` has `"mp/grilling" = "own/nope"`, a **Hull** **Skill** in `mp` calls `/grilling`, and `own` has no
  `nope`
- **THEN** the command exits non-zero naming `mp/grilling` and `own/nope`

#### Scenario: Unused bind to a missing skill

- **WHEN** `[bind]` has `"mp/grill" = "own/nope"`, no **Hull** **Skill** in `mp` calls `/grill`, and `own` has no `nope`
- **THEN** the command exits non-zero naming `mp/grill` and `own/nope`, and writes nothing

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

- **WHEN** `[bind]` has `"mp/grill" = "own/grilling"`, `own` has `grilling`, and no **Hull** **Skill** in `mp` calls
  `/grill`
- **THEN** the command warns that `mp/grill` binds no **Reference**, and succeeds

#### Scenario: Used by prose only

- **WHEN** `[bind]` has `"mp/notes" = "own/notes"` and a **Hull** **Skill** in `mp` only mentions `` `notes` ``
- **THEN** the command gives no warning about that **Bind**

### Requirement: The hull is transitive

The **Hull** SHALL be the **Entries** plus every **Skill** reachable from them through resolved slash and Skill tool
**References**, followed from each **Skill** reached, cycles included. A **Skill** reached SHALL be found as an
**Entry** is (unique within its **Source**, readable name, symlinks inside it), errors naming the referencing **Skill**.

#### Scenario: Two hops

- **WHEN** `mp/tdd` calls `/grilling`, and `mp/grilling` calls `Skill(notes)`, found only in `own`
- **THEN** the **Hull** is `mp/tdd`, `mp/grilling` and `own/notes`

#### Scenario: Cycle

- **WHEN** `mp/a` calls `/b`, `mp/b` calls `/a`, and `mp/a` is the only **Entry**
- **THEN** the **Hull** is `mp/a` and `mp/b`, and the command terminates

#### Scenario: Ambiguous target

- **WHEN** `mp/tdd` calls `/grilling` and `mp` holds two **Skills** named `grilling`
- **THEN** the command exits non-zero naming `mp/tdd`, `/grilling` and both folders

### Requirement: Every declared source is read

Resolution SHALL read every declared **Source**, whether an **Entry** uses it or not: git **Sources** at their `ref`,
fetched only when that commit is missing from the cache.

#### Scenario: Source with no entry

- **WHEN** no **Entry** is in `own`, and `mp/tdd` calls `/notes`, found only in `own`
- **THEN** `own/notes` is in the **Hull**

### Requirement: Prose references

A prose **Reference** SHALL be a code span whose whole content is a name (`` `grilling` ``), or a bare hyphenated token
`[a-z0-9]+(-[a-z0-9]+)+` standing as its own token: not preceded by a letter, digit, `_`, `/`, `.`, `-`, `~`, `:`, `\`,
`<`, `@`, `#`, `=`, `?`, `&`, `$` or `](`, and not followed by a letter, digit, `_`, `/`, `-`, `%`, `+`, or `.` or `:`
and a letter or digit; nor a YAML key, first on its line (past indent or a list dash) and followed by `:`. It SHALL
count anywhere, code blocks included, except the value of `SKILL.md`'s front matter `name:`, and never inside a slash or
Skill tool **Reference**, whose arguments on that line belong to it, nor at a name that is a Skill tool **Reference** in
the sentence form, on whatever line.

#### Scenario: Backticked and hyphenated

- **WHEN** a **Skill**'s Markdown holds `` use `grilling` ``, `then diagnosing-bugs.`, or `pre-commit run` in a fenced
  block
- **THEN** `grilling`, `diagnosing-bugs` and `pre-commit` are prose **References**

#### Scenario: Not prose

- **WHEN** it holds `grilling` unquoted, `` `grilling --fast` ``, `` `mp/grilling` ``, `--dry-run`, `refs/red-green.md`,
  `x-ray.png`, `[see](my-skill)`, `[x](#my-skill)`, `id="my-skill"`, `foo_my-skill`, `?q=my-skill`, `my-skill%20x`,
  `allowed-tools: Bash` or `https://x.org/my-skill`
- **THEN** none is a prose **Reference**

#### Scenario: Own name line

- **WHEN** `mp/code-review`'s `SKILL.md` front matter has `name: code-review`, and `[bind]` has
  `"mp/code-review" = "own/review"`
- **THEN** that line is no **Reference**, and the vendored `name:` stays `code-review`

#### Scenario: Slash form wins

- **WHEN** it holds `` `/grilling` ``, `Skill(diagnosing-bugs)` or `Skill(skill: "grilling", args: "x-y")`
- **THEN** each is one slash or Skill tool **Reference**, and no prose **Reference**

### Requirement: Prose resolves in its own source only

A prose **Reference** from a **Skill** in **Source** `a`, unless a **Bind** decides it, SHALL resolve to `a/<name>` only
when exactly one **Skill** in `a` is named `<name>`, and no **Skill** there with an unreadable name sits in a folder so
named; otherwise it is no **Reference**: no edge, no warning, no error. It SHALL never extend the **Hull**: when its
target is in the **Hull** it is an edge of kind `prose`, otherwise a suggestion.

#### Scenario: Inside the hull

- **WHEN** `mp/tdd` calls `/grilling` and mentions `` `notes` ``, and `mp` has `grilling` and `notes`, with `mp/notes`
  an **Entry**
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
