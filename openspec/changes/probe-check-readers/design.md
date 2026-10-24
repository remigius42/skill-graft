# Design

## Context

Step 1 of `skills/graft-check/SKILL.md` decides hardened from `printenv CLAUDECODE`, `command -v claude` and the text
of `claude --help`. Readers run as
`claude -p --restricted --strict-mcp-config --tools Read,Grep,Glob --agents ${CLAUDE_SKILL_DIR}/reader.json --agent reader`;
a reader that fails is a **Skill** with no report. `docs/security.md`
already records one such failure: a session authenticated only by `CLAUDE_CODE_OAUTH_TOKEN` gives readers that report
"Not logged in". The confinement is in those flags, whatever harness starts the process.

## Goals / Non-Goals

**Goals:**

- Hardened means a reader demonstrably runs, confined, before any **Skill** text is read.
- Any harness whose agent can run shell commands gets the hardened **Check** when a working Claude Code is installed.
- No `claude` process, and so no charge to the user's Claude account, from another harness without their yes.

**Non-Goals:**

- Readers on another harness's CLI (`codex exec`, `gemini -p`, `opencode run`): a later change, once their
  confinement is measured.
- Probing the patcher separately: it is the same `claude` with the same login; a patcher that fails writes nothing,
  which already ends that fix.

## Decisions

- **The probe is a reader.** Same command, same `reader.json`, same flags, from a new empty `mktemp -d` folder with no
  `--add-dir`, prompt `mode: probe` on stdin. `reader.json` gains: in `probe` mode, reply `ready` and nothing else.
  Success is exit 0 and a reply of `ready`. A reply alone proves login, a working account and accepted flags; `ready`
  also proves the agent definition loaded, which `--agents` with a broken path would not show by exit code.
  Alternatives: `claude auth status` (proves login only, not flags or agent, and a subcommand the skill would depend
  on); `claude --help` text (proves flags only, today's gap).
- **Account question before the probe, outside Claude Code only.** The probe itself is a billed request. In Claude Code
  the session already runs on that account, so asking adds nothing. Outside, `CLAUDECODE` is unset; the skill asks
  once, and a no goes to the unhardened question as a failed probe does. Two questions for one decline is accepted:
  the user may still want an unhardened **Check**.
- **The probe's error is shown as is.** Its stderr, first line, held to 200 characters: it comes from `claude`, not
  from **Skill** text, since the probe's folder is empty.
- **Locating the agent files.** The skill names `reader.json` and `patcher.json` as files in its own folder, by
  absolute path, with `${CLAUDE_SKILL_DIR}` as how Claude Code spells that folder. Another harness's agent finds it
  from where it loaded the skill.

## Risks / Trade-offs

- [Another harness's agent cannot find its skill folder, or passes a wrong path] → the probe fails, as `ready` never
  comes: unhardened, with the error. Safe, not silent.
- [The probe passes and a later reader still fails (rate limit, quota mid-run)] → that **Skill** has no report, as
  today.
- [The account question is prompt-level] → a hijacked main agent is not the threat here: no **Skill** text is read
  before the probe. The question protects the user's quota, not the confinement.
- [Harnesses other than Claude Code are not in the eval] → the eval runs headless Claude Code only; one run by hand in
  another harness checks this change, recorded in `docs/security.md` like the Claude Code version.
