# Tasks

Apply with the `tdd` skill: each task red-green-refactor (failing test first, then code), one commit, and
`pre-commit run --all-files` green. New words go into `.cspell.yaml`. Tests set `HOME` to `tmp_path/home`, run in
`tmp_path`, and build synthetic **Skills**, projects and git repositories. Each group updates `README.md` for what
it ships.

## 1. Scope discovery

- [ ] 1.1 `conftest.py`: the autouse `home` fixture also `monkeypatch.chdir(tmp_path)`, so no test's working
  folder lies in the developer's real home. Verify: every existing test green, unchanged.
- [ ] 1.2 `paths.discover(start)` and the module-level root (`paths.use(root)`, `paths.root()`,
  `paths.scope()`); `package()` derives from the root; `cli.main` sets it from the working folder for every
  command but `init`. Verify: inside-a-project (from a subfolder), project-without-a-package, nested-projects,
  package-above-the-home-folder, working-folder-outside-home, project-build (`--no-install` writes only under the
  project), not-initialized names the user scope's `skill-graft.toml`.

## 2. APM per scope

- [ ] 2.1 Fake `apm` in `conftest.py`: without `-g`, lists `<arg>` under `dependencies.apm` in `./apm.yml` in its
  working folder, creating it as APM does, and logs its working folder. `paths.manifest()` per scope; `apm.install()`
  runs `apm install ./.apm/skill-graft` with `cwd=root` in project scope; `registered()` resolves relative entries
  against the manifest's folder. Verify: project-build-from-a-subfolder, project-package-not-registered, every
  user-scope deploy test unchanged, and `build --no-install` in project scope reads no `apm.yml`.
- [ ] 2.2 Real-APM integration test (skipped without `apm`): a project with `.claude/`, `init --project`, a path
  **Source**, `build`; the skill lands in `<project>/.claude/skills/`, `<project>/apm.yml` lists
  `./.apm/skill-graft`, and nothing under `~/.apm/` changes. `docs/design.md`: the measured project-scope APM
  behavior beside the user-scope list. Verify: the test passes with `uv run --group dev pytest`.

## 3. Init --project

- [ ] 3.1 `init --project`: creates `<cwd>/.apm/skill-graft/` and registers it; refuses an existing folder and
  the home folder; retry hint `in <root>, run: apm install ./.apm/skill-graft`; `init`'s help describes the flag.
  Verify: project-package, project-registration-succeeds, no-harness-in-the-project (fake APM exits 2),
  project-folder-exists, project-init-at-home, project-init-inside-another-project, and the user-scope init tests
  unchanged. README: a project-scope section, recommending committing the whole **Package** (vendored skills
  included), `apm.yml` and `apm.lock.yaml`, so teammates need only APM.

## 4. Overlap checks

- [ ] 4.1 `paths.deploy_folders()` adds `PROJECT_DEPLOY_FOLDERS` under the root in project scope, beside the
  user ones. Verify: source-is-the-project's-deploy-folder, project-source-is-a-user-deploy-folder,
  source-contains-the-project-package, and the user-scope overlap tests unchanged.

## 5. Naming the package

- [ ] 5.1 `cli.main` prints `skill-graft: package: <absolute package>` via `errors.notice` before dispatching
  `init`, `resolve`, `build`, `update`, `add`, `remove` and `rename`; not for `tree`, `why` or `help`. Top-level
  and per-command help texts say the **Package** is the nearest `.apm/skill-graft/`, else `~/.apm/skill-graft/`.
  Verify: build-names-the-package (project), user-scope line, printed when the command fails (no config),
  read-only-command (`tree`, `why`), help text tests updated.

## 6. Wrap-up

- [ ] 6.1 `docs/design.md` paths and commands mention both scopes; ADR 0003 note and ADR 0004 already written.
  Verify: `pre-commit run --all-files` green and `openspec validate project-scope --strict` passes.
