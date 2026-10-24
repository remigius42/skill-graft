# Tasks

Apply with the `tdd` skill where code is testable: each task red-green-refactor, one commit. The skill's text is
checked by `tests/cli/test_check.py` for its shape and by the eval for its behavior.

## 1. Probe mode

- [x] 1.1 In `skills/graft-check/reader.json`, add `probe` to `mode`: reply `reader-ok` and nothing else, reading
  nothing, ahead of the Report section's `findings: none`; test in `tests/cli/test_check.py` that the prompt names
  `probe` and `reader-ok`, and that the Report section's replies apply to `full` and `uses` modes only; verify it
  passes

## 2. The skill

- [x] 2.1 Rewrite step 1 of `skills/graft-check/SKILL.md`: `command -v claude`; outside Claude Code (`CLAUDECODE` unset),
  say the readers and patcher run on the user's Claude Code account and go on only on a yes; then the probe as the
  design has it, hardened on exit 0 and `reader-ok`; otherwise unhardened, naming the error (no `claude`, the account
  declined, or the first line of the probe's output, at most 200 characters, with `claude auth login` advised for
  "Not logged in"), and the yes-or-no as today. Drop the `--help` test. Name
  `reader.json` and `patcher.json` by absolute path in the skill's folder, `${CLAUDE_SKILL_DIR}` in Claude Code;
  verify `pre-commit run --all-files`
- [x] 2.2 In `evals/graft-check/run.sh` and its README, make `unhardened` a `claude` wrapper whose calls with
  `--agent` print `Not logged in · Please run /login` on stdout and exit 1, the outer session passing through; check
  it says unhardened, names `Not logged in`, advises `claude auth login`, starts no reader after the probe, reads no
  **Skill**, and leaves the package unchanged. Add `older-claude`, a wrapper whose calls with `--restricted` print
  `error: unknown option '--restricted'` on stderr and exit 1: check it names `--restricted` and reads no **Skill**.
  Run `run.sh unhardened older-claude injected clean` and verify every check is `ok`

## 3. Docs

- [x] 3.1 Update `docs/security.md` (hardened wherever a working Claude Code is installed; the probe; the account
  question; the `CLAUDE_CODE_OAUTH_TOKEN` case now caught by the probe), the README's Security section, and ADR 0007's
  "enforced on Claude Code only", edited in place; verify `pre-commit run --all-files`
- [x] 3.2 Run `/graft-check` once by hand in OpenCode (a free model: one small package, one or two **Skills**; Gemini
  CLI's Google sign-in no longer serves individuals): verify the account question, the probe, and a reader per
  **Skill**; record the OpenCode version and model in `docs/security.md`

## 4. Changelog

- [x] 4.1 Add an entry to `CHANGELOG.md` under `[Unreleased]`: the **Check** is hardened in any harness with a working
  Claude Code, asking first outside Claude Code, and falls back to unhardened, naming why, when a probe reader fails.
  Per `AGENTS.md` it lands in the archive commit; check the box there; verify `pre-commit run --all-files`
