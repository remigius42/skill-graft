# Spec Delta

## MODIFIED Requirements

### Requirement: Slash references

A slash **Reference** SHALL be `/` then a name, the longest run of `[A-Za-z0-9._-]` starting with a letter or
digit, trailing `.` dropped, standing as its own token: not preceded by a letter, digit, `/`, `.`, `-`, `~`, `:`,
`\`, `<`, `@`, `](`, `="` or `='`, nor by `(` or `[` and `"` or `'`, nor by a backtick that follows a letter,
digit, `.`, `)` or `]`, and not followed by `/`, or `:` and a letter or digit. It SHALL count anywhere, code
blocks included.

#### Scenario: Standalone token

- **WHEN** a **Skill**'s Markdown holds `run /grilling.`, `` `/grilling` ``, `(/grilling)`, `` (`/grilling`) ``,
  `'/grilling'` or `**/grilling**`
- **THEN** each is a slash **Reference** to `grilling`

#### Scenario: Paths and URLs

- **WHEN** it holds `/usr/bin`, `src/grilling`, `https://x.org/grilling`, `~/grilling`, `</grilling>`,
  `/plugin:grilling`, `/my-dir/file`, `/tmp.d/x`, `[docs](/docs)`, `href="/about"` or `"@/utils"`
- **THEN** none is a **Reference**, nor is any prefix of a name in them

#### Scenario: Path arguments

- **WHEN** it holds `fetch('/orders', x)`, `open("/grilling")` or `["/a", "/b"]`
- **THEN** none is a slash **Reference**

#### Scenario: After a code span

- **WHEN** it holds `` its `package.json`/build-tool scripts `` or `` `lint`/`check` ``
- **THEN** neither `build-tool` nor `check` is a slash **Reference**

### Requirement: Skill tool references

A Skill tool **Reference** SHALL be the call form `Skill(<name>)`: the name first, optionally quoted with `"` or
`'`, optionally given as `skill=<name>` or `skill: <name>`, then `)` or `,` and further arguments, with optional
whitespace inside the parentheses. It SHALL also be each name in double quotes or backticks, the whole quoted
text a name, that follows `Skill tool` in the same sentence. A sentence ends at `.`, `!` or `?` followed by
whitespace or the end of the file, or at a blank line; a line break alone does not end it.

#### Scenario: Call forms

- **WHEN** a **Skill**'s Markdown holds `Skill(grilling)`, `Skill("grilling")`, `Skill(skill: "grilling")` or
  `Skill(skill: "grilling", args: "x")`
- **THEN** each is a Skill tool **Reference** to `grilling`

#### Scenario: Sentence form

- **WHEN** it holds `Call the Skill tool twice, for "grilling" and "domain-modeling".`
- **THEN** it holds Skill tool **References** to `grilling` and `domain-modeling`

#### Scenario: Backticked name in a sentence

- **WHEN** it holds `` Call the Skill tool with `writing-for-agents` for the style guide. ``
- **THEN** it is a Skill tool **Reference** to `writing-for-agents`, and no prose **Reference**

#### Scenario: Sentence across lines

- **WHEN** it holds `call the Skill tool with` at the end of one line and `"codebase-design" for the vocabulary.`
  on the next
- **THEN** it is a Skill tool **Reference** to `codebase-design`

#### Scenario: Outside the sentence

- **WHEN** it holds `` Use the Skill tool. Then see "grilling" and `notes`. ``
- **THEN** `grilling` is no **Reference**, and `` `notes` `` is a prose **Reference**

#### Scenario: Unquoted name

- **WHEN** it holds `call the Skill tool with grilling.`
- **THEN** it holds no Skill tool **Reference**

#### Scenario: Renamed

- **WHEN** `mp/tdd` holds `Call the Skill tool with "grilling".`, and `mp/grilling` is renamed to `mp-grilling`
- **THEN** the vendored `mp/tdd` reads `Call the Skill tool with "mp-grilling".`
