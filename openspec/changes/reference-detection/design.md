# Design

## Context

`references.scan` runs one combined pattern, `REFERENCE`, over each Markdown file and maps its named groups to
kinds (`FORMS`): `slash`, `tool` (`Skill(name)`), and `code`/`prose`, both kind `prose`. A **Reference** records
its name's span, which renames rewrite, and its text as written, which the tree and `why` show. Measured on
`mattpocock/skills` at `49dd158`: 13 skills say "Skill tool", always as "call the Skill tool with/for" and the
names in `"…"` or `` `…` ``; the slash false positives were `fetch('/orders', …)` in a fenced TypeScript block and
`` `package.json`/build-tool `` in prose.

## Goals / Non-Goals

**Goals:**

- One scan still yields every **Reference** with one kind; a name found by the sentence form is never also prose.

**Non-Goals:**

- Natural-language parsing: no negation, no tense, no "skill" without "tool".
- Changing prose detection or the `cd /tmp` decision (slash references count in code blocks).

## Decisions

- **Sentence form as a second pass in `scan`**, before the `REFERENCE` loop: find each `Skill tool`, take the text
  up to the sentence end (`[.!?]` then whitespace or end of text, or a blank line), and in it each `"name"` or
  `` `name` `` whose whole content matches the name pattern. Each becomes a `skill-tool` **Reference** with text
  `Skill tool "name"` (or with backticks, as written). Their spans are kept, and the `REFERENCE` loop skips a
  prose match on the same span, so `` `writing-for-agents` `` or a quoted `domain-modeling` is one call, not also
  prose. Rejected: folding it into `REFERENCE` (a variable-length sentence in one alternation would be unreadable
  and could not yield several names per match).
- **Only names after `Skill tool`**: the measured phrasing always puts them after; a name before it ("For `x`,
  use the Skill tool") stays prose. Single quotes are not counted: apostrophes in English prose would pair up.
- **Slash lookbehinds**: two more negative lookbehinds on the slash alternative, `(?<![(\[]["'])` and
  `` (?<![\w.)\]]`) ``. Rejected: ignoring a quote before `/` only inside fenced blocks (needs fence tracking,
  and `'/grilling'` in a fence is as likely a call as not); blocking `(` plus a backtick (it would drop
  `` (`/grilling`) ``, common in prose, to catch a template literal path, which a following `/` mostly excludes
  already).
- **Announcement**: `cli` (for `build`) and `update` print
  `skill-graft: <n> prose suggestion(s): run skill-graft resolve` through `errors.notice`, after the run's warnings,
  when `hull.suggestions` is non-empty; `update` uses the hull at the new tips. `resolve` is unchanged.

## Risks / Trade-offs

- \[A sentence mentions the Skill tool without calling it ("never call the Skill tool with `x`")\] → the target is
  vendored and visible in `tree` and `why`; `[bind] "mp/x" = false` turns it off.
- [A missing sentence end (a list item without a period) runs into the next item] → a blank line or the next
  `Skill tool` bounds it; at worst a later quoted name that matches a real **Skill** is pulled in, visibly.
- [Existing hull and lock tests depend on today's classification] → the new forms need text no fixture has (the
  words "Skill tool", a closing backtick before `/`, `(` plus a quote before `/`); run the full suite per task.
