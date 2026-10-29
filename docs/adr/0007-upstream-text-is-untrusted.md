# Upstream text is untrusted

Skills come from other people's repositories and are written to steer agents, so their text can carry prompt injection.
skill-graft fails resolution on **Hidden characters** in a **Skill**, **Upstream** or patched: the **Check** reads both,
so a **Patch** cannot clear them. The **Check** reads **Skill** text only through headless `claude -p --restricted`
readers and a patcher, confined to their folders, without shell or network, and a person reviews every **Patch**. Its
main agent sees CLI output and reports only. `claude` enforces the readers' and the patcher's confinement wherever a
working Claude Code is installed, in any harness; the probe reader that must answer before any **Skill** text is read,
and the main agent's quarantine, are steps of the skill, held at the prompt level by the harness's model. Elsewhere the
**Check** says it is unhardened and runs only on the user's yes.

## Considered Options

- A read-only agent that skill-graft deploys through APM: Codex drops its `tools:` and Kiro rejects them, it can still
  read any path, and it widens what skill-graft ships.
- `disallowed-tools` and read-only subagents: prompt-level, not enforced.
- An OS jail around a headless CLI per harness: portable, but needs a jail tool and one CLI per harness.
