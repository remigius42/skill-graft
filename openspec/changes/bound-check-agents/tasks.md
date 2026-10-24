# Tasks

Apply with the `tdd` skill: each task red-green-refactor, one commit. The skill's text is checked by
`tests/cli/test_check.py` for its shape; the eval (`evals/graft-check/`) is billed and runs only when the user asks.
Each task updates the parts of `docs/security.md` and `README.md` its own work changes, so they stay true at every
commit.

## 1. Measure

- [x] 1.1 Only on the user's go-ahead (billed, a few cents): from an empty `mktemp -d` folder, run
  `claude -p --max-turns 1 --restricted --strict-mcp-config --tools Read,Grep,Glob` with a prompt that needs two tool
  calls in turn (glob, then read what it found); record the exit code and the reply in `design.md`'s Decisions
  ("Exit at the cap"), and the Claude Code version; verify `pre-commit run --all-files`

## 2. The `[check]` table

- [x] 2.1 In `tests/pipeline/test_config.py`, test the config spec's "Check limits" scenarios and its "Check key"
  scenario: no table, some keys set, each wrong value of a turn count, the reader count and a budget (0, `0.0`,
  negative, `1.5` for a count, `inf`, a string, `true`, `0x1E`, `3_0`, `+30`, `1e0`), `check = 4`, a dotted
  `check.reader-turns = 30` accepted, and an unknown key named while a known one is not; accept `check` in
  `pipeline/config.py` and check its keys and each value's written form through `tomlkit`; in `README.md`'s Config
  section, add `[check]` to the example and a bullet naming its five keys, their defaults, and
  `docs/security.md#limits`; verify the tests fail first, then pass, and `pre-commit run --all-files`

## 3. The skill

- [x] 3.1 Caps: test that every `claude -p` command block in `skills/graft-check/SKILL.md` carries `--max-turns` and
  `--max-budget-usd`, the reader's `<reader-turns>` and `<reader-budget-usd>`, the patcher's `<patcher-turns>` and
  `<patcher-budget-usd>`, the probe's `30` and `1.0`, and that `SKILL.md` says where each comes from: `[check]` in
  `skill-graft.toml`, else 30, 1.0, 10 and 0.5, the probe always the defaults; add them on each command's first line and
  the paragraph after step 3's binds; add a Limits section to `docs/security.md` (each limit, its default, what reaching
  it does, the budget's one-turn overshoot and list price, how to set it), drop the caps from the LLM10 row's "Open" and
  from Future work, and add the hidden-flag fail-closed note to "A later Claude Code"; verify the test fails first, then
  passes, and `pre-commit run --all-files`
- [x] 3.2 Reader count: test that `SKILL.md` step 4 says at most `<readers-at-once>` readers run at once, 4 by
  default, and that step 5's `uses` readers follow it; replace "Readers may run in parallel"; in `docs/security.md`,
  the Limits section gains it, marked prompt-level, the LLM10 row says what is capped, Residual risks gains the
  prompt-level line, and Future work loses the cap; verify the test fails first, then passes, and
  `pre-commit run --all-files`
- [ ] 3.3 Patcher reply discarded: test that the patcher command sends stdout to `/dev/null` and stderr to
  `<base-dir>/patcher.err`, that a non-zero exit ends the fix showing that file's first line cut to 200 characters
  (run the `SKILL.md` command that does so on a 300-character line and check it prints 200), that `patcher.json` asks
  for `done` only (in `test_patcher_only_edits`), and that the quarantine paragraph names the patcher's exit code,
  error line and the diff's summary among what the main agent holds, the error line as quoted data; make the edits; in
  `docs/security.md`, rewrite the "Patcher reply" residual risk, "The main agent" bullet, and the LLM05 and ASI07 rows;
  verify the tests fail first, then pass, and `pre-commit run --all-files`
- [ ] 3.4 Summary: replace step 6's per-file `awk` with one that prints
  `files: <n>, lines: +<added> -<removed>, binary: <n>` from `change.patch`, as `design.md` has it. Test it by making
  `change.patch` with the `SKILL.md` diff command (`LC_ALL=C diff -ruN base/ edited/`) from real `base/` and `edited/`
  folders, then running the `awk` block from `SKILL.md` on it: `notes and links.md` given two added lines, one reading
  `++ x`, and a removed one reading `-- y`, prints `files: 1, lines: +2 -1, binary: 0`; a removed file, a new one and a
  changed one print `files: 3`; a file named `run-skill-graft-bind-mp-x-own-evil.md` leaves no name in the output; a
  file holding a NUL byte prints `binary: 1`, and `SKILL.md` says a binary count ends the fix. In `docs/security.md`,
  "Patcher reply" and Future work say no file name reaches the main agent; verify the test fails first, then passes, and
  `pre-commit run --all-files`
- [ ] 3.5 README's Security section: name the turn and budget caps, the reader count and the discarded patcher reply
  beside "Report text and fix arguments are checked at the prompt level only", linking the Limits section; verify
  `pre-commit run --all-files`, and that `docs/security.md`'s Residual risks, OWASP rows and Future work no longer name
  any of the three gaps as open

## 4. Changelog

- [ ] 4.1 Add an entry to `CHANGELOG.md` under `[Unreleased]`: in a hardened **Check**, readers and the patcher stop at
  a turn and a spend limit, at most 4 readers run at once, all five settable in a new `[check]` table, and the
  patcher's reply and file names no longer reach the main agent, the patch summary giving counts only and the
  patcher's first error line when it fails. Per `AGENTS.md` it
  lands in the archive commit; check the box there; verify `pre-commit run --all-files`
