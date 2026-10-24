# Tasks

Apply with the `tdd` skill: each task red-green-refactor, one commit. The skill's text is checked by
`tests/cli/test_check.py` for its shape; the eval (`evals/graft-check/`) is billed and runs only when the user asks.
Each task updates the parts of `docs/security.md` its own work changes, so the page stays true at every commit.

## 1. Measure

- [x] 1.1 Only on the user's go-ahead (billed, a few cents): from an empty `mktemp -d` folder, run
  `claude -p --max-turns 1 --restricted --strict-mcp-config --tools Read,Grep,Glob` with a prompt that needs two tool
  calls in turn (glob, then read what it found); record the exit code and the reply in `design.md`'s Decisions
  ("Exit at the cap"), and the Claude Code version; verify `pre-commit run --all-files`

## 2. The skill

- [ ] 2.1 Turn caps: test that every `claude -p` command block in `skills/graft-check/SKILL.md` carries `--max-turns`,
  the reader's `30` and the patcher's `10`; add them on each command's first line; in `docs/security.md`, drop the
  turn cap from the LLM10 row's "Open" and from Future work, and add the hidden-flag fail-closed note to "A later
  Claude Code"; verify the test fails first, then passes, and `pre-commit run --all-files`
- [ ] 2.2 Parallelism cap: test that `SKILL.md` step 4 says at most 4 readers run at once and step 5's `uses` readers
  follow it; replace "Readers may run in parallel"; in `docs/security.md`, the LLM10 row says what is capped and that
  the reader count is prompt-level, Residual risks gains that line, and Future work loses the cap; verify the test fails
  first, then passes, and `pre-commit run --all-files`
- [ ] 2.3 Patcher reply discarded: test that the patcher command sends stdout to `/dev/null`, that a non-zero exit ends
  the fix, that `patcher.json` asks for `done` only (in `test_patcher_only_edits`), and that the quarantine paragraph
  names the patcher's exit code and the diff's summary among what the main agent holds; make the edits; in
  `docs/security.md`, rewrite the "Patcher reply" residual risk, "The main agent" bullet, and the LLM05 and ASI07 rows;
  verify the tests fail first, then pass, and `pre-commit run --all-files`
- [ ] 2.4 Bounded summary: a test that takes the `awk` block from `SKILL.md` step 6 and runs it on a synthetic
  `change.patch` of 50 new files, one name 300 characters long: it prints 20 lines of `<name>: +<n> -<n>`, each name at
  most 200 characters, then `30 more files`; on a two-file diff both lines and no count; a file `notes and links.md`
  given two added lines, one reading `++ x`, as `notes and links.md: +2 -0`; make the change, and add
  the quoted-data rule for those names to the quarantine paragraph; in `docs/security.md`, "Patcher reply" and Future
  work say the names are bounded and quoted; verify the test fails first, then passes, and `pre-commit run --all-files`
- [ ] 2.5 README's Security section: name the turn caps and the discarded patcher reply alongside "Report text and fix
  arguments are checked at the prompt level only", adding the reader count; verify `pre-commit run --all-files` and that
  `docs/security.md`'s Residual risks, OWASP rows and Future work no longer name any of the three gaps as open

## 3. Changelog

- [ ] 3.1 Add an entry to `CHANGELOG.md` under `[Unreleased]`: in a hardened **Check**, readers and the patcher stop
  after a fixed number of turns, at most 4 readers run at once, and the patcher's reply no longer reaches the main
  agent. Per `AGENTS.md` it lands in the archive commit; check the box there; verify `pre-commit run --all-files`
