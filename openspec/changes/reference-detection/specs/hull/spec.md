# Spec Delta

## MODIFIED Requirements

### Requirement: Slash references

A slash **Reference** SHALL be `/` then a name, the longest run of `[A-Za-z0-9._-]` starting with a letter or
digit, trailing `.` dropped, standing as its own token: not preceded by a letter, digit, `/`, `.`, `-`, `~`, `:`,
`\`, `<`, `@`, `}`, `](`, `="` or `='`, nor by `"` or `'` right after `(` or `[`, nor by a backtick that closes a
code span (an odd number of backticks before it on its line), and not followed by `/`, or `:` and a letter or
digit. It SHALL count anywhere, code blocks included.

#### Scenario: Standalone token

- **WHEN** a **Skill**'s Markdown holds `run /grilling.`, `` `/grilling` ``, `(/grilling)`, `` (`/grilling`) ``,
  `run '/grilling'`, `**/grilling**`, `Run "/tdd", "/grilling"` or `` 运行`/grilling` ``
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

A Skill tool **Reference** SHALL be the call form `Skill(<name>)`: the name first, optionally quoted with `"` or
`'`, optionally given as `skill=<name>` or `skill: <name>`, then `)` or `,` and further arguments, with optional
whitespace inside the parentheses. It SHALL also be each name in double quotes or backticks, the whole quoted text
a name (one trailing `.` dropped), between `Skill tool` (or `` `Skill` tool ``, as words of their own) and the
end of its sentence, when it resolves to a **Skill**; one that resolves to none, to several, or to a **Skill**
whose name cannot be read is no **Reference**: no edge, no warning, no error. A name inside a `Skill(...)` call
is that call's only. The sentence form uses the rules below.

The sentence SHALL end at the next `Skill tool`; at a blank line; at a line opening a list item, heading, code
fence or table row; or at `.`, `!` or `?` (not the `.` of `e.g.` or `i.e.`), closing quotes, backticks, `*`, `)`
or `]` allowed after it, then whitespace and an uppercase letter, a quote, a backtick, `*`, `(` or `[`, or the end of the
file. A line break alone SHALL NOT end it. The SKILL.md front matter's own `name:` line holds no such name.

#### Scenario: Call forms

- **WHEN** a **Skill**'s Markdown holds `Skill(grilling)`, `Skill("grilling")`, `Skill(skill: "grilling")` or
  `Skill(skill: "grilling", args: "x")`
- **THEN** each is a Skill tool **Reference** to `grilling`

#### Scenario: Sentence form

- **WHEN** it holds `Call the Skill tool twice, for "grilling" and "domain-modeling".`, and its **Source** has
  both
- **THEN** it holds one Skill tool **Reference** each to `grilling` and `domain-modeling`

#### Scenario: Backticked name in a sentence

- **WHEN** it holds `` Call the Skill tool with `writing-for-agents` for the style guide. ``
- **THEN** it is a Skill tool **Reference** to `writing-for-agents`, and no prose **Reference**

#### Scenario: Sentence across lines

- **WHEN** it holds `call the Skill tool with` at the end of one line and `"codebase-design" for the vocabulary.`
  on the next
- **THEN** it is a Skill tool **Reference** to `codebase-design`, and no prose **Reference**

#### Scenario: Sentence ends

- **WHEN** it holds `` Use the Skill tool. Then see "grilling" and `notes`. ``,
  `` (Use the Skill tool.) Then `notes`. ``, or the sentence's line is followed by a list item `` - `grilling` ``
  or a code fence
- **THEN** `grilling` in quotes is no **Reference**, and the backticked names are prose **References**

#### Scenario: Not a sentence end

- **WHEN** it holds `Call the Skill tool, e.g. with "grilling" or "domain-modeling."`
- **THEN** it holds Skill tool **References** to `grilling` and `domain-modeling`

#### Scenario: Unresolved name

- **WHEN** it holds `Call the Skill tool with "grilling" and set mode to "fast".`, and no **Source** has `fast`,
  or two other **Sources** both have it
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

### Requirement: Prose references

A prose **Reference** SHALL be a code span whose whole content is a name (`` `grilling` ``), or a bare hyphenated
token `[a-z0-9]+(-[a-z0-9]+)+` standing as its own token: not preceded by a letter, digit, `_`, `/`, `.`, `-`,
`~`, `:`, `\`, `<`, `@`, `#`, `=`, `?`, `&`, `$` or `](`, and not followed by a letter, digit, `_`, `/`, `-`,
`%`, `+`, or `.` or `:` and a letter or digit; nor a YAML key, first on its line (past indent or a list dash) and
followed by `:`. It SHALL count anywhere, code blocks included, except the value of `SKILL.md`'s front matter
`name:`, and never inside a slash or Skill tool **Reference**, whose arguments on that line belong to it, nor at
a name that is a Skill tool **Reference** in the sentence form, on whatever line.

#### Scenario: Backticked and hyphenated

- **WHEN** a **Skill**'s Markdown holds `` use `grilling` ``, `then diagnosing-bugs.`, or `pre-commit run` in a
  fenced block
- **THEN** `grilling`, `diagnosing-bugs` and `pre-commit` are prose **References**

#### Scenario: Not prose

- **WHEN** it holds `grilling` unquoted, `` `grilling --fast` ``, `` `mp/grilling` ``, `--dry-run`,
  `refs/red-green.md`, `x-ray.png`, `[see](my-skill)`, `[x](#my-skill)`, `id="my-skill"`, `foo_my-skill`,
  `?q=my-skill`, `my-skill%20x`, `allowed-tools: Bash` or `https://x.org/my-skill`
- **THEN** none is a prose **Reference**

#### Scenario: Own name line

- **WHEN** `mp/code-review`'s `SKILL.md` front matter has `name: code-review`, and `[bind]` has
  `"mp/code-review" = "own/review"`
- **THEN** that line is no **Reference**, and the vendored `name:` stays `code-review`

#### Scenario: Slash form wins

- **WHEN** it holds `` `/grilling` ``, `Skill(diagnosing-bugs)` or `Skill(skill: "grilling", args: "x-y")`
- **THEN** each is one slash or Skill tool **Reference**, and no prose **Reference**
