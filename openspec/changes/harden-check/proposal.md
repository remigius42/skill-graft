# Proposal

## Why

Skills come from other people's repositories and are written to steer agents, so their text can carry prompt injection,
some of it invisible. The **Check** reads that text on purpose, in an agent with a shell, file writes and network, often
in a mode that asks no one before a command; a hijacked **Check** can exfiltrate, or write a **Patch** that the next
`build` deploys. Nothing blocks it today: `build --into` never runs APM, whose install refuses **Hidden characters**,
and the skill's front matter restricts no tool (ADR 0007).

## What Changes

- Resolution fails when a **Hull** **Skill** holds a **Hidden character**, in its **Upstream** text, a file name, or its
  patch files, naming each file, line and character class; one run reports every **Skill**. A Markdown file that is not
  UTF-8 now fails too, where it only warned. Invisible characters common as copy-paste debris (zero-width, soft hyphen,
  bidi marks) only warn. `resolve`, `build` (`--into` too), `update` and the editing commands fail writing nothing;
  `why` and `tree` print the **Hull**, then fail. **BREAKING** for a **Hull** holding one, whose `build` failed in APM
  already, now `resolve` fails too; and for one holding Markdown that is not UTF-8, which resolved with a warning.
- On Claude Code the **Check** reads **Skill** text only through headless readers, `claude -p --restricted`, limited to
  `Read`, `Grep` and `Glob`, without MCP servers, and confined to that **Skill**'s folders. Its main agent never opens a
  **Skill**'s **Upstream** text, vendored copy or patch files: it holds CLI output and the readers' reports, whose
  quoted text it shows and never acts on. Judging **References** resolved to the wrong **Skill**, and whether a **Bind**
  fits every use of a name, moves into the readers.
- A **Patch** is written by a headless patcher confined to a temporary folder, without shell or network; the user reads
  its diff before it goes into the **Package**.
- A fix's arguments must come from CLI output or the config; others are reported without a fix.
- Where it cannot start a hardened reader (another harness, no `claude`, a `claude` without those flags), the **Check**
  says it is unhardened and why, and reads in-session only on the user's yes.
- `README.md` gains a Security section, linking `docs/security.md`: what APM and skill-graft block, what the **Check**
  enforces and only on Claude Code, running it sandboxed and outside auto mode, the residual risks, and that other
  harnesses are likely not secure.

## Capabilities

### New Capabilities

- `hidden-characters`: which invisible characters fail resolution or warn, where they are looked for, and how they are
  reported.

### Modified Capabilities

- `hull`: a Markdown file that is not UTF-8 fails resolution instead of warning.
- `check`: reading through hardened readers, the main agent's inputs, the patcher and the user's review, fix arguments,
  and the unhardened fallback.

## Impact

- `src/skill_graft/pipeline/`: a scan in the **Hull** walk, over each **Skill**'s **Upstream** folder and patched copy;
  errors in `infra/errors.py`'s style.
- `skills/graft-check/`: `SKILL.md` rewritten, plus the reader and patcher definitions beside it, vendored with it.
- `tests/`: the scan at the pipeline and CLI layers; `tests/cli/test_check.py` for the skill's files.
- `evals/graft-check/`: scenarios for an injected **Skill** and for the unhardened fallback.
- `README.md`, `docs/security.md`, `docs/design.md`, `CHANGELOG.md` (at archive).
- Depends on Claude Code's `claude -p --restricted --tools --strict-mcp-config`; a spike confirms their behavior first.
