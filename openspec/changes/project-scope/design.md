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
- **The root is fixed once per invocation.** `paths` gains a module-level root that `cli.main` sets after
  parsing, inside its `SkillGraftError` handling: `paths.discover(Path.cwd())` for every command but `init`
  (a deleted working folder becomes an error, not a traceback), which sets the home folder or, with
  `--project`, the working folder. `paths.scope()` says `user` when the root is the home folder. The existing
  functions keep their signatures and derive from the root. Rejected: threading a root argument through every
  caller (about twenty call sites, no behavior gained); discovering on every call (`init --project` would then
  need another override anyway).
- **Discovery** walks `cwd` and its parents, resolved, returning the first holding `.apm/skill-graft/` as a
  folder, and stops after the home folder; none found means the home folder. Only the folder's presence counts,
  so a missing `skill-graft.toml` is reported for the right **Package**: `config.text()` suggests
  `init --project` in project scope.
- **APM per scope.** User scope: unchanged, `apm install -g <absolute>`, manifest `~/.apm/apm.yml`. Project
  scope: `apm install ./.apm/skill-graft` with `cwd=root`, manifest `<root>/apm.yml`. The relative argument keeps
  the committed `apm.yml` portable. `registered()` resolves a relative entry against the manifest's folder,
  not the working folder; at user scope this changes nothing, since APM rejects relative paths there.
- **Deploy folders.** User scope keeps `DEPLOY_FOLDERS`. Project scope adds `PROJECT_DEPLOY_FOLDERS`
  (`.agents/skills`, `.claude/skills`, `.grok/skills`, `.kiro/skills`) under the root, to the user ones.
- **Package line.** `cli.main` prints `skill-graft: package: <absolute package>` to stderr through
  `errors.notice` for the writing commands only, after parsing and before dispatch; `init --project` prints it
  only after its home-folder check passes.
- **Failed `init --project` removes its folder** (`shutil.rmtree` of what it created), because a kept folder would
  be found by every later command below it. User scope keeps the folder and the `apm install -g` retry hint,
  since discovery never finds the user package by accident.
- **Lock paths.** `upstream` is written relative to its **Source**'s root (the cache export or the path
  **Source**'s folder) in both scopes; the absolute folder stays in memory, where `update`'s error filter and the
  patch messages use it. In project scope a path **Source** inside the root is written relative to the package
  folder, else absolute. Rejected: per-scope `upstream` (a branch for no reader of the absolute cache path).
- **Discovery skips every `.apm/skill-graft`**, besides the resolved package: vendored copies in a committed
  project **Package** must never be read back as a **Source**'s **Skills**, wherever the **Source** points.

## Risks / Trade-offs

- \[Tests run with the working folder inside the developer's real home, while `HOME` points at `tmp_path/home`;
  the walk up would find the real `~/.apm/skill-graft` as a project\] → `conftest.py`'s autouse `home` fixture
  also changes into `home` (`monkeypatch.chdir`), where the walk stops at once; tests needing a project build it
  under `home`. Changing into `tmp_path` would not do: `home` is below it, so the walk would pass on to `/`.
- \[Implicit discovery acts on an unexpected **Package**\] → writing commands name it; errors name it.
- [APM changes its project-scope folders or harness detection] → measured list in `docs/design.md`; the real-APM
  integration test covers `.claude/skills`.
- \[The fake `apm` diverges from the real one\] → it mimics only the measured behavior: without `-g`, it appends
  the argument verbatim to `./apm.yml` in its working folder.
- \[APM writes its own state under `~/.apm` even at project scope (seen while measuring)\] → tests assert only that
  `~/.apm/skill-graft/` is absent and `~/.apm/apm.yml`, if any, does not list the project package.

## Migration Plan

None: user scope behaves as before, except the new `package:` line on stderr and relative `upstream` in the
lock, which nothing reads.
