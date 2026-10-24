# Tasks

Apply with the `tdd` skill where code is testable: each task red-green-refactor, one commit. The skill's text is
checked by `tests/cli/test_check.py` for its shape and by the eval for its behavior.

## 1. Probe mode

- [ ] 1.1 In `skills/graft-check/reader.json`, add `probe` to `mode`: reply `ready` and nothing else, reading nothing;
  test in `tests/cli/test_check.py` that the reader's prompt names `probe` and `ready`; verify it passes

## 2. The skill

- [ ] 2.1 Rewrite step 1 of `skills/graft-check/SKILL.md`: outside Claude Code (`CLAUDECODE` unset), say the readers
  and patcher run on the user's Claude Code account and go on only on a yes; then the probe as the design has it,
  hardened on exit 0 and `ready`; otherwise unhardened, naming the error (no `claude`, the account declined, or the
  probe's first stderr line, at most 200 characters), and the yes-or-no as today. Drop the `--help` test. Name
  `reader.json` and `patcher.json` by absolute path in the skill's folder, `${CLAUDE_SKILL_DIR}` in Claude Code;
  verify `pre-commit run --all-files`
- [ ] 2.2 In `evals/graft-check/run.sh` and its README, make `unhardened` a `claude` wrapper whose calls with
  `--agent` print `Not logged in` and exit 1, the outer session passing through; check it says unhardened, names
  `Not logged in`, starts no reader after the probe, reads no **Skill**, and leaves the package unchanged; run
  `run.sh unhardened injected clean` and verify every check is `ok`

## 3. Docs

- [ ] 3.1 Update `docs/security.md` (hardened wherever a working Claude Code is installed; the probe; the account
  question; the `CLAUDE_CODE_OAUTH_TOKEN` case now caught by the probe), the README's Security section, and ADR 0007's
  "enforced on Claude Code only"; verify `pre-commit run --all-files`
- [ ] 3.2 Run `/graft-check` once by hand in another installed harness (opencode or Gemini CLI) on a small package:
  verify the account question, the probe, and a reader per **Skill**; record the harness and version in
  `docs/security.md`

## 4. Changelog

- [ ] 4.1 Add an entry to `CHANGELOG.md` under `[Unreleased]`: the **Check** is hardened in any harness with a working
  Claude Code, asking first outside Claude Code, and falls back to unhardened, naming why, when a probe reader fails.
  Per `AGENTS.md` it lands in the archive commit; check the box there; verify `pre-commit run --all-files`
