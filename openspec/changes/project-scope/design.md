# Design

## Context

Every path skill-graft uses comes from `paths.py`, built from `Path.home()`: `package()`, `config_file()`,
`skills()`, `manifest()`, `deploy_folders()`, `cache()`. `apm.py` runs `apm install -g <absolute package>` and
scans `~/.apm/apm.yml`. The decisions behind scope selection are in ADR 0004; the reasons for driving APM rather
than editing its manifest are in ADR 0003.

Measured with APM 0.33.0, `HOME` a scratch folder, in a scratch git repository:

- `apm install ./.apm/skill-graft` in the project root creates `apm.yml` if missing, lists `./.apm/skill-graft`
  under `dependencies.apm` (relative, unlike user scope, where relative paths fail), writes `apm.lock.yaml` and
  `apm_modules/`, and adds `apm_modules/` to `.gitignore`. Repeating it adds no second line.
- APM takes the working folder as the project root: the same install run in a subfolder fails.
- Without a harness marker (`.claude/`, `.github/copilot-instructions.md`, `.cursor/`, …) and without `targets:`,
  it exits 2 with "No harness detected" and a fix, and removes the `apm.yml` it created.
- With every target, skills land in `.agents/skills`, `.claude/skills`, `.grok/skills` and `.kiro/skills`.
- A skill removed from the package is pruned on the next `apm install`.
- Vendoring into the project's own `.apm/skills/` instead needs the project's own `apm.yml`, and `build`
  replaces `.apm/skills/` whole, which would delete the project's own skills.

## Goals / Non-Goals

**Goals:**

- One code path for both scopes: user scope is the project-scope rule with the home folder as root.

**Non-Goals:**

- A flag forcing user scope from inside a project, picking APM targets, or detecting harnesses.
- Sharing git caches or locks between scopes beyond what already happens (the cache is per user).

## Decisions

- **A subpackage, `<root>/.apm/skill-graft/`**, not the project's own `.apm/`: the same layout in both scopes,
  and skill-graft never owns files the project has. Rejected: vendoring into `<root>/.apm/skills/` (see Context).
- **The root is fixed once per invocation.** `paths` gains a module-level root that `cli.main` sets before
  dispatch: `paths.discover(Path.cwd())` for every command but `init`, which sets the home folder or, with
  `--project`, the working folder. `paths.scope()` says `user` when the root is the home folder. The existing
  functions keep their signatures and derive from the root. Rejected: threading a root argument through every
  caller (about twenty call sites, no behavior gained); discovering on every call (`init --project` would then
  need another override anyway).
- **Discovery** walks `cwd` and its parents, resolved, returning the first holding `.apm/skill-graft/` as a
  folder, and stops after the home folder; none found means the home folder. Only the folder's presence counts,
  so a missing `skill-graft.toml` still yields "run `skill-graft init`" for the right **Package**.
- **APM per scope.** User scope: unchanged, `apm install -g <absolute>`, manifest `~/.apm/apm.yml`. Project
  scope: `apm install ./.apm/skill-graft` with `cwd=root`, manifest `<root>/apm.yml`. The relative argument keeps
  the committed `apm.yml` portable. `registered()` resolves a relative entry against the manifest's folder,
  not the working folder; at user scope this changes nothing, since APM rejects relative paths there.
- **Deploy folders.** User scope keeps `DEPLOY_FOLDERS`. Project scope adds `PROJECT_DEPLOY_FOLDERS`
  (`.agents/skills`, `.claude/skills`, `.grok/skills`, `.kiro/skills`) under the root, to the user ones.
- **Package line.** `cli.main` prints `skill-graft: package: <absolute package>` to stderr through `errors.notice`
  for the writing commands only, before dispatch.
- **Retry hint** for `init --project` names the folder and the command: `in <root>, run: apm install ./.apm/skill-graft`.

## Risks / Trade-offs

- \[Tests run with the working folder inside the developer's real home, while `HOME` points at `tmp_path`; the
  walk up would find the real `~/.apm/skill-graft` as a project\] → `conftest.py`'s autouse `home` fixture also
  changes into `tmp_path` (`monkeypatch.chdir`), so no test walks outside it. Added before any discovery code.
- \[Implicit discovery acts on an unexpected **Package**\] → writing commands name it; errors name it.
- [APM changes its project-scope folders or harness detection] → measured list in `docs/design.md`; the real-APM
  integration test covers `.claude/skills`.
- \[The fake `apm` diverges from the real one\] → it mimics only the measured behavior: without `-g`, it appends
  the argument verbatim to `./apm.yml` in its working folder.

## Migration Plan

None: user scope behaves as before, except the new `package:` line on stderr.
