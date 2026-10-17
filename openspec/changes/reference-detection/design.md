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
- Changing prose detection beyond giving way to the sentence form, or the `cd /tmp` decision (slash references
  count in code blocks).

## Decisions

- **Sentence form as a second pass in `scan`, merged by span.** Find each `Skill tool`; its window runs to the
  first of: the next `Skill tool`, a blank line, a line opening a list item (`-`, `*`, `+`, `1.`) or heading
  (`#`), or `[.!?]` (a closing `"` or `` ` `` allowed after it) followed by whitespace and an uppercase letter,
  or the end of the text. In the window, each `"name"` or `` `name` `` whose content matches the name pattern,
  one trailing `.` dropped, is a candidate. Windows never overlap, so a name is a candidate once. The
  `REFERENCE` matches and the candidates are then merged by span: a candidate inside a `Skill(...)` or slash
  match is dropped (the call keeps it); a prose match on a candidate's span is dropped (the candidate keeps it).
  The result is sorted by offset, so `scan` still returns references in file order. Rejected: folding the
  sentence into `REFERENCE` (a variable-length window in one alternation is unreadable and cannot yield several
  names per match); ending sentences at any `.` plus whitespace (`e.g. "x"` would end early).
- **Candidates are calls only when they resolve.** A candidate is a `skill-tool` **Reference** with text
  `Skill tool "name"` (backticks kept as written) and a `sentence` flag; `hull.walk` resolves it like any
  Skill tool **Reference** but drops it silently when nothing matches, instead of warning. A sentence often
  quotes non-skill words (`"fast"`, `` `true` ``); warning on each would be noise, while one that matches a
  **Skill** is almost certainly the call. Rejected: warning like `Skill(name)` (noise on every build).
- **Only names after `Skill tool`**, double quotes and backticks only: the measured phrasing always puts the
  names after; single quotes would pair with apostrophes.
- **Slash exclusions**: a lookbehind drops `/` after `}` (`${id}/orders`) and after `"` or `'` right after `(`
  or `[` (a first argument or list item); `scan` drops one after a backtick that closes a code span, an odd
  number of backticks before it on its line. Rejected: also after `, "` (it dropped real calls in prose lists,
  `Run "/tdd", "/grilling"`, silently, while a later path argument only warns and a bind silences it); a backtick
  after a word character (it dropped `` 运行`/grilling` ``); ignoring quotes only in fenced blocks (needs fence
  tracking); blocking `(` plus a backtick (drops `` (`/grilling`) ``).
- **Announcement**: `cli` (for `build`) and `update` print
  `skill-graft: <n> prose suggestion(s): run skill-graft resolve` through `errors.notice`, after the run's warnings,
  when `hull.suggestions` is non-empty; `update` uses the hull at the new tips. `resolve` is unchanged.

## Risks / Trade-offs

- **A sentence mentions the Skill tool without calling it** ("never call the Skill tool with `x`"). The target is
  vendored and visible in `tree` and `why`; `[bind] "mp/x" = false` turns it off.
- **A word quoted in a Skill tool sentence happens to name a Skill** (`"review"`). It is vendored, visibly in
  `tree` and `why`; a **Bind** to `false` turns it off.
- **A sentence whose next one starts lowercase runs on** (`… "x". then …`). A blank line, a list item, a heading
  or the next `Skill tool` bounds it, and a later quoted name only counts if it names a **Skill**.
- **Existing hull and lock tests depend on today's classification and order.** Sorting by offset keeps file
  order; the new forms need text no fixture has; run the full suite per task.
