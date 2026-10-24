# Proposal

## Why

`docs/security.md` records three gaps in the hardened **Check** that a hijacked reader or patcher can use. The
patcher's reply, of any length, and the file names the step-6 summary prints reach the main agent with no rule to treat
them as quoted data; a reader's `text` has both. Readers and the patcher run as `claude -p` with no cap on their turns
or spend, so injected text can keep one looping and spending tokens. And "Readers may run in parallel" sets no limit on
how many.

## What Changes

- The main agent never sees the patcher's reply: the patcher command sends its stdout to `/dev/null`, and the patcher
  replies `done` only. Its exit code alone tells the main agent whether it ran; the diff says what it did.
- The step-6 summary prints each file name cut to 200 characters and at most 20 files, then how many more. The main
  agent holds those names as quoted data: shown, never acted on. Each name is read whole from its `+++` header, so one
  holding a space no longer comes out empty, and a changed line that starts with `--` or `++` is counted.
- The quarantine paragraph of `SKILL.md` names what else the main agent holds (the patcher's exit code, the summary)
  and the quoted-data rule for the file names.
- Every reader runs with `--max-turns` and `--max-budget-usd`, by default 30 turns and 1 USD; the patcher by default
  10 turns and 0.50 USD. A reader stopped by either leaves its **Skill** with no report, as any reader that fails does;
  a patcher stopped by either ends that fix.
- At most 4 readers run at once by default, in `full` and `uses` mode alike.
- A new optional `[check]` table in `skill-graft.toml` sets those five limits (`reader-turns`, `reader-budget-usd`,
  `patcher-turns`, `patcher-budget-usd`, `readers-at-once`); skill-graft refuses a value that is not a positive number,
  an integer where it counts. The skill reads them from the config it already holds.
- `docs/security.md` documents each limit, its default, what reaching it does, and how to change it; Residual risks,
  the LLM05, LLM10 and ASI07 rows and Future work say what now holds, and that the reader count is prompt-level. The
  README's Config and Security sections name the table.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `config`: a new requirement for the `[check]` table and its value checks; "Unsupported keys are errors" accepts
  `check` and its five keys.
- `check`: "Skill text is read by hardened readers" gains the turn and budget caps and the reader count, from the
  config; "The main agent never reads skill text" names the patcher's exit code and bounded summary as all it holds of
  the patcher; "Patches are written by a confined patcher" gains the caps and the discarded reply.

## Impact

- `src/skill_graft/pipeline/config.py` and `tests/pipeline/test_config.py`: the `[check]` table.
- `skills/graft-check/SKILL.md` (the quarantine paragraph, where the limits come from, step 4's reader command and
  parallelism, step 6's patcher command and summary), `skills/graft-check/patcher.json` (reply `done`). `reader.json` is
  unchanged.
- `tests/cli/test_check.py`: every `claude -p` command in `SKILL.md` carries both caps; the patcher's reply is
  discarded; the reader count; the summary run on synthetic diffs.
- `docs/security.md`, `README.md`.
- `CHANGELOG.md` entry at archive.
- Overlaps `probe-check-readers` (in flight) in `SKILL.md`'s reader and patcher commands and in `docs/security.md`; see
  `design.md`.
