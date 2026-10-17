# Tasks

Apply with the `tdd` skill: each task red-green-refactor (failing test first, then code), one commit, and
`pre-commit run --all-files` green. New words go into `.cspell.yaml`. Tests set `HOME` to `tmp_path/home`, run in
it, and build synthetic **Skills**, projects (under `home`) and git repositories. Each group updates `README.md`
for what it ships.

## 1. Scope discovery

- [x] 1.1 `conftest.py`: the autouse `home` fixture also `monkeypatch.chdir(home)`, so the walk up stops at once
  and never reaches the developer's real home. Verify: every existing test green, unchanged.
- [x] 1.2 `paths.discover(start)` and the module-level root (`paths.use(root)`, `paths.root()`,
  `paths.scope()`); `package()` derives from the root, the home folder while unset; `cli.main` sets it after
  parsing, inside its error handling, by discovery for every command but `init` (which gets the home folder),
  and unsets it in a `finally`. Verify: inside-a-project (from a subfolder), project-without-a-package,
  nested-projects, package-above-the-home-folder, working-folder-outside-home (a **Package** at its working
  folder, so no walk leaves `tmp_path`), root unset after `main` returns, project-build (`--no-install`
  leaves `~/.apm/skill-graft/` absent), not-initialized, deleted-working-folder.
- [x] 1.3 `config.text()`: in project scope a missing `skill-graft.toml` names `skill-graft init --project` and
  not plain `init`. Verify: project-package-without-config, and the user-scope not-initialized test unchanged.

## 2. APM per scope

- [x] 2.1 Fake `apm` in `conftest.py`: without `-g`, lists `<arg>` under `dependencies.apm` in `./apm.yml` in its
  working folder, creating it as APM does, and logs its working folder. `paths.manifest()` per scope;
  `apm.install()` runs `apm install ./.apm/skill-graft` with `cwd=root` in project scope; `registered()` resolves
  relative entries against the manifest's folder. Verify: project-build-from-a-subfolder,
  project-package-not-registered, every user-scope deploy test unchanged, and `build --no-install` in project
  scope reads no `apm.yml`.
- [x] 2.2 Real-APM integration test (skipped without `apm`): a project with `.claude/`, `init --project`, a path
  **Source**, `build`; the skill lands in `<project>/.claude/skills/`, `<project>/apm.yml` lists
  `./.apm/skill-graft`, `~/.apm/skill-graft/` is absent, and `~/.apm/apm.yml`, if any, does not list the project
  package. `docs/design.md`: the measured project-scope APM behavior beside the user-scope list. Verify: the test
  passes with `uv run --group dev pytest`.

## 3. Init --project

- [x] 3.1 `init --project`: creates `<cwd>/.apm/skill-graft/` and registers it; refuses an existing folder and the
  home folder (compared resolved, before the package line); when APM leaves the package unlisted, removes
  `.apm/skill-graft/` and any `.apm/` it created and says to rerun `skill-graft init --project`, else keeps it and
  says to run `skill-graft build`; `init`'s help describes the flag. Verify:
  project-package, project-registration-succeeds, no-harness-in-the-project (fake APM exits 2; `.apm/` gone), apm-fails-after-registering,
  project-folder-exists, project-init-at-home (also through a symlink), project-init-inside-another-project, and
  the user-scope init tests unchanged. README: a project-scope section, recommending committing the whole
  **Package** (vendored skills included), `apm.yml` and `apm.lock.yaml`, so teammates need only APM.

## 4. Overlap checks and discovery

- [x] 4.1 `config.py`: a **Source** inside or containing either scope's **Package** is an error;
  `paths.deploy_folders()` adds `PROJECT_DEPLOY_FOLDERS` under the root in project scope, beside the user ones.
  Verify: source-is-the-project's-deploy-folder, project-source-is-a-user-deploy-folder,
  source-contains-the-project-package, project-source-contains-the-user-package, and the user-scope overlap
  tests unchanged.
- [x] 4.2 `discovery.py` skips every folder that resolves to `.apm/skill-graft`. Verify: another-project's-package,
  symlink-to-another-project's-package, symlink-into-the-package unchanged.

## 5. Portable lock

- [x] 5.1 `why <skill>` prints `upstream: <absolute folder>` after the tree. README's patch recipe takes the base
  from it instead of the lock. Verify: path-source and remote-source upstream lines, existing `why` tests updated.
- [ ] 5.2 `lock.render`: `upstream` relative to its **Source**'s root (`.` for a **Skill** at the root), in both
  scopes. Verify: upstream-recorded, skill-at-the-source-root, patch-changes-the-hash, every lock test updated to
  the relative form, and `update`'s and the patch errors still name absolute folders.
- [ ] 5.3 In project scope, a path **Source** inside the project root is written relative to the **Package**.
  Verify: project-source-inside-the-project, project-source-outside-the-project, same-lock-on-another-machine
  (two `HOME`s, one project copied between them, byte-equal locks). README: what makes a committed **Package**
  machine-independent.

## 6. Naming the package

- [ ] 6.1 `cli.main` prints `skill-graft: package: <absolute package>` via `errors.notice` after parsing and
  before dispatching `init`, `resolve`, `build`, `update`, `add`, `remove` and `rename`; not for `tree`, `why`,
  `help` or a usage error. Top-level and per-command help texts say the **Package** is the nearest
  `.apm/skill-graft/`, else `~/.apm/skill-graft/`. Verify: build-names-the-package (project), user-scope line,
  printed when the command fails (no config), read-only-command (`tree`, `why`), none on a usage error, help text
  tests updated.

## 7. Wrap-up

- [ ] 7.1 `docs/design.md` paths, commands and lock mention both scopes; ADR 0003 note and ADR 0004 already
  written. Verify: `pre-commit run --all-files` green and `openspec validate project-scope --strict` passes.
