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

- [ ] 2.1 In `tests/pipeline/test_config.py`, test the config spec's "Check limits" scenarios and its "Check key"
  scenario: no table, some keys set, each wrong value of a turn count, the reader count and a budget (0, negative,
  `1.5` for a count, `inf`, a string, `true`), `check = 4`, and an unknown key named while a known one is not; accept
  `check` in `pipeline/config.py` and check its keys and values; in `README.md`'s Config section, add `[check]` to the
  example and a bullet naming its five keys, their defaults, and `docs/security.md#limits`; verify the tests fail first,
  then pass, and `pre-commit run --all-files`

## 3. The skill

- [ ] 3.1 Caps: test that every `claude -p` command block in `skills/graft-check/SKILL.md` carries `--max-turns` and
  `--max-budget-usd`, the reader's `<reader-turns>` and `<reader-budget-usd>`, the patcher's `<patcher-turns>` and
  `<patcher-budget-usd>`, and that `SKILL.md` says where each comes from: `[check]` in `skill-graft.toml`, else 30,
  1.0, 10 and 0.5; add them on each command's first line and the paragraph after step 3's binds; add a Limits section
  to `docs/security.md` (each limit, its default, what reaching it does, the budget's one-turn overshoot and list price,
  how to set it), drop the caps from the LLM10 row's "Open" and from Future work, and add the hidden-flag fail-closed
  note to "A later Claude Code"; verify the test fails first, then passes, and `pre-commit run --all-files`
- [ ] 3.2 Reader count: test that `SKILL.md` step 4 says at most `<readers-at-once>` readers run at once, 4 by
  default, and that step 5's `uses` readers follow it; replace "Readers may run in parallel"; in `docs/security.md`,
  the Limits section gains it, marked prompt-level, the LLM10 row says what is capped, Residual risks gains the
  prompt-level line, and Future work loses the cap; verify the test fails first, then passes, and
  `pre-commit run --all-files`
- [ ] 3.3 Patcher reply discarded: test that the patcher command sends stdout to `/dev/null`, that a non-zero exit ends
  the fix, that `patcher.json` asks for `done` only (in `test_patcher_only_edits`), and that the quarantine paragraph
  names the patcher's exit code and the diff's summary among what the main agent holds; make the edits; in
  `docs/security.md`, rewrite the "Patcher reply" residual risk, "The main agent" bullet, and the LLM05 and ASI07 rows;
  verify the tests fail first, then pass, and `pre-commit run --all-files`
- [ ] 3.4 Summary: a test that takes the `awk` block from `SKILL.md` step 6 and runs it on synthetic `change.patch`
  files: 50 new files, one name 300 characters long, print 20 lines of `<name>: +<n> -<n>`, each name at most 200
  characters, then `30 more files`; a two-file diff prints both lines and no count; `notes and links.md` given two added
  lines, one reading `++ x`, and a removed line reading `-- y`, prints `notes and links.md: +2 -1`; make the change, and
  add the quoted-data rule for those names to the quarantine paragraph; in `docs/security.md`, "Patcher reply" and
  Future work say the names are bounded and quoted; verify the test fails first, then passes, and
  `pre-commit run --all-files`
- [ ] 3.5 README's Security section: name the turn and budget caps, the reader count and the discarded patcher reply
  beside "Report text and fix arguments are checked at the prompt level only", linking the Limits section; verify
  `pre-commit run --all-files`, and that `docs/security.md`'s Residual risks, OWASP rows and Future work no longer name
  any of the three gaps as open

## 4. Changelog

- [ ] 4.1 Add an entry to `CHANGELOG.md` under `[Unreleased]`: in a hardened **Check**, readers and the patcher stop at
  a turn and a spend limit, at most 4 readers run at once, all five settable in a new `[check]` table, and the
  patcher's reply no longer reaches the main agent; the patch summary names a file holding a space. Per `AGENTS.md` it
  lands in the archive commit; check the box there; verify `pre-commit run --all-files`
