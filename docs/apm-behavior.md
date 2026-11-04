# Measured APM behavior

What APM does, measured rather than read from its docs, since skill-graft drives it as a command
([ADR 0003](adr/0003-drive-apm-never-edit-its-manifest.md)). Remeasure on an APM upgrade.

## User scope

APM 0.35.0, `apm install -g -t claude`, with `HOME` pointed at a scratch directory:

- A local package without `apm.yml` is rejected with exit code 1, for both `skills/<name>/` and `.apm/skills/<name>/`:
  `not a valid APM package (no apm.yml, SKILL.md, or plugin.json)`; 0.33.0 said
  `no apm.yml, SKILL.md, or plugin.json found`. With a two-line `apm.yml`, every `.apm/skills/<name>/` deploys to
  `~/.claude/skills/`, sibling files included.
- `path: ./skill-graft` in `~/.apm/apm.yml`, once `~/.apm/apm.lock.yaml` exists, fails whatever the working directory,
  with exit code 1; without the lock file it exits 0, ending in "No changes -- install state already up to date", and
  deploys nothing. `~/.apm/skill-graft` and absolute paths work.
- Removing a skill and reinstalling prunes it from `~/.claude/skills/` ("3 stale files cleaned"). 0.35.0 also warns
  "Historical dependency claims retained", with `-v` naming the removed skill's files, and prunes all the same.
- `apm install -g <absolute path>` creates `~/.apm/apm.yml` if missing and lists the package under `dependencies.apm` as
  an absolute path, never with `~`. Repeating it changes nothing and redeploys; 0.33.0 also printed "updated ref in
  apm.yml". A package of just the two-line `apm.yml`, with no skills yet, registers too.
- Without `-t` and without `targets:` in `~/.apm/apm.yml`, skills deploy to `~/.agents/skills/`.
- With each of the 21 values of `-t`, 18 targets and the aliases `agy` (of `antigravity`), `agents` and `vscode` (of
  `copilot`): `claude` deploys to `~/.claude/skills/`, `grok-build` to `~/.grok/skills/`, `kiro` to `~/.kiro/skills/`,
  `opencode` to `~/.config/opencode/skills/`, `antigravity` to `~/.gemini/antigravity-cli/skills/`, `hermes` to
  `~/.hermes/skills/`, `grok-bot`, new in 0.35.0, to `~/agent-data/workflows/`, and `agent-skills`, `codex`, `copilot`,
  `cursor`, `gemini` and `windsurf` to `~/.agents/skills/`. `intellij`, `openclaw` without an existing `~/.openclaw`,
  and the experimental `copilot-app`, `copilot-cowork` and `grok-cloud` deploy no skill and exit 0. `-t all` leaves out
  the explicit-only `agent-skills`, `antigravity`, `grok-bot`, `hermes` and `intellij` and the experimental targets, and
  deploys to the `.agents`, `.claude`, `.config/opencode`, `.grok` and `.kiro` folders.

## Project scope

APM 0.35.0 at project scope, `apm install ./.apm/skill-graft` in a scratch repository, `HOME` a scratch directory:

- In the project root it creates `apm.yml` if missing and lists `./.apm/skill-graft` under `dependencies.apm`, relative;
  repeating it adds no second line. It also writes `apm.lock.yaml` and `apm_modules/`, adds `apm_modules/` to
  `.gitignore`, and creates `~/.apm` for its own state.
- It takes the working directory as the project root: run in a subfolder, it fails.
- Without a harness marker (`.claude/`, `.cursor/`, `.github/copilot-instructions.md`, …) and without `targets:`, it
  exits 2 with "No harness detected" and removes the `apm.yml` it had created. With markers of two harnesses it exits 2
  with "Multiple harnesses detected".
- It deploys only to the detected harness; with `-t all`, skills land in `.agents/skills`, `.claude/skills`,
  `.grok/skills` and `.kiro/skills` under the project root.
- With each of the 21 values of `-t`: `claude` deploys to `.claude/skills`, `grok-build` to `.grok/skills`, `kiro` to
  `.kiro/skills`, `grok-bot`, new in 0.35.0, to `agent-data/workflows`, and every other target that deploys skills to
  `.agents/skills`, under the project root. `openclaw` and the experimental `copilot-app`, `copilot-cowork` and
  `grok-cloud` deploy no skill and exit 0.
- Removing a skill from the package and reinstalling prunes it. 0.35.0 also warns "Historical dependency claims
  retained", and prunes all the same.
