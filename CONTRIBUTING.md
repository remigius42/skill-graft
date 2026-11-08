# Contributing

The rules for commits, code and tests are in [AGENTS.md](AGENTS.md), and the project's terms in
[CONTEXT.md](CONTEXT.md); both hold for people as for agents. How it works, and why, is mapped in
[docs/README.md](docs/README.md).

## Setup

```sh
uv sync
uv run pre-commit install --install-hooks
uv run pre-commit install --hook-type commit-msg
```

The `commit-msg` hook is a separate install. Without it, commitlint never runs.

## Changes

A change goes through [OpenSpec](https://github.com/Fission-AI/OpenSpec), one branch per change,
`feat/opsx-<change-name>`:

1. Propose it under `openspec/changes/<change-name>/` (proposal, design, specs, tasks) and wait for its approval.
1. Apply it test-first, one commit per task.
1. Archive it, which merges its specs into `openspec/specs/`. If users see the change, add its `CHANGELOG.md` entry in
   the archive commit.

Any other commit users would see, such as a direct `fix:`, adds its own entry; [AGENTS.md](AGENTS.md) has the rule.

## Checks

```sh
uv run pre-commit run --all-files
uv run pytest
```

The hooks are listed in [.pre-commit-config.yaml](.pre-commit-config.yaml).

The tests point `HOME` at a temporary directory. The APM integration test runs the `apm` from the dev group and is
skipped when `apm` is not on `PATH`.

## Tooling

The tools run at pinned versions: the hooks at a commit SHA, their `additional_dependencies` and node at a version, the
actions at a SHA, commitlint for CI in `.github/commitlint/package-lock.json`. Only what a hook itself depends on floats
within its range, such as the commitlint hook's `@commitlint/cli`. To update the hooks:

```sh
uv run pre-commit autoupdate --freeze
uv run pre-commit install-hooks
uv run pre-commit run --all-files
```

Without `--freeze`, `autoupdate` writes tags back. Dependabot opens the bumps for `.github/commitlint/`, the actions and
`uv.lock` ([.github/dependabot.yml](.github/dependabot.yml)), weekly; the `check-dependabot` hook checks that file
against its schema. Some versions move in pairs, so bump the other with it, on a Dependabot branch too. The `check-pins`
hook ([scripts/check_pins.py](scripts/check_pins.py)) fails, naming both sides, while a pair differs:

- the mypy hook's version and `mypy` in the dev group of `pyproject.toml`, then `uv lock`
- the mypy hook's `pytest` and `tomlkit` and the versions in `uv.lock`
- each `@v<version>` in `README.md`'s Installation and `version` in `pyproject.toml`, which the release commit sets
  together; and, a pair of its own, so that neither form can go missing, each `skill-graft==<version>` there and that
  same `version`
- the APM version `README.md` requires, in its text and each `apm-cli==` of its install line, and `apm-cli` in the dev
  group of `pyproject.toml`, then `uv lock`; no hook checks the rest, so measure again what
  [docs/apm-behavior.md](docs/apm-behavior.md) records, copy the hidden character classes in
  `src/skill_graft/infra/text.py` again from APM's `apm_cli/security/content_scanner.py`, and update every other mention
  of the old version (`grep -rnF '<old version>' docs src tests`)
- the commitlint hook's `@commitlint/config-conventional` and `.github/commitlint/`:
  `npm install --prefix .github/commitlint --package-lock-only --ignore-scripts --save-exact @commitlint/cli@<version> @commitlint/config-conventional@<version>`
- `node` under `default_language_version` and `node-version` in the commitlint job of `.github/workflows/ci.yml`

Nothing bumps node or the digest of the `test-root` job's container image: update them by hand, now and then.

Run `install-hooks` before the next commit: a `commit-msg` hook's environment, commitlint's, is otherwise installed
during that commit, which has overwritten the index of a worktree with the hook's own files.

## Mutation testing

Two harnesses, both opt-in, so no hook or CI job runs either: `mutation/` mutates the tokens of the security-relevant
regexes and fails on a survivor; mutmut mutates the rest of `src/skill_graft/` and only reports.

### The regex harness

`uv run python -m mutation [target…]`, from the repository root, mutates each security-relevant regex: the **Vet**'s,
**Reference** finding, the `name:` comment, `skill-graft.toml` names and URLs, the URLs `tree` links to, the **Hidden
character** classes ([mutation/targets.py](mutation/targets.py)). For each mutant, one token changed, it runs the tests
of the modules holding the pattern, on one process per CPU, and exits 1 on a mutant no test kills, unless
[mutation/equivalent.toml](mutation/equivalent.toml) lists it with the reason it cannot change behavior, and on a listed
one that no longer survives or exists. It is opt-in and takes minutes, so no hook or CI job runs it; run it after
changing a target pattern, then kill each survivor with a test in its module's test file, or list it. With no target it
runs them all; a target is named as in `targets.py`, such as `config.NAME` or `vet._PATTERNS:send.url`.

### mutmut

`nice -n 19 ionice -c 3 uv run mutmut run`, from the repository root, mutates every function in `src/skill_graft/`
(`[tool.mutmut]` in `pyproject.toml`) and runs the tests that reach each mutant, in a copy of the repository in
`mutants/`; `nice` and `ionice` keep its one process per CPU from freezing the machine. A full run takes about an hour
on 8 CPUs; `uv run mutmut run "skill_graft.pipeline.lock*"` runs one module's mutants in a few minutes, and a rerun
skips functions that did not change. Run one at a time per checkout: two share `mutants/`. It forks, so it runs on Linux
and macOS only. `uv run mutmut results` lists the survivors, `uv run mutmut show <mutant>` prints one's diff. It never
fails a build: read the survivors after changing a module, and kill each with a test in the module's test file. Three
kinds are known noise, not gaps: a message's wording (`cli.py`'s help texts sit in the module-level `_TEXT`, which
mutmut never mutates), a change mypy would refuse, which the hooks keep from landing, and code that runs only at import,
such as `vet._commands`, which no test reaches with a mutant switched on. A mutant that cannot change behavior: first
remove what it shows redundant, or restructure so none exists, or name the value in a module-level constant; else put
the equivalent expression alone on a line of its own with a bare `# pragma: no mutate`, and
`# Equivalent mutants: <reason>` in a comment above. A pragma silences every mutant on its line, killed ones too, so
never on a line holding anything else, and no `start` … `end` regions. On an argument's line it also silences the call's
mutants, each argument dropped or `None`, though not the other lines' own: name the argument's value first, and mark
that line instead. The `linear_time` tests are left out: their wall-clock limit misses under load, and the regex harness
times them.

The baseline to beat, 8097 mutants with the change `mutmut-src` (2026-11-07): 7532 killed, 5 timed out, 560 survived;
202 survive since the change `mutmut-cli`. `pipeline` is from its rerun after the change `mutmut-src`; `infra` from its
rerun with the change `mutmut-infra`; `commands` from its rerun, 2261 mutants, with the change `mutmut-commands`; `cli`
from its rerun, 845 mutants, with the change `mutmut-cli`. Survivors per layer:

| Layer      | Survivors | Of which                                                                       |
| ---------- | --------: | ------------------------------------------------------------------------------ |
| `cli`      |        48 | all known noise: 34 usage wording in `_parser`, message wording, mypy refusals |
| `commands` |        65 | all known noise: message wording, mypy refusals, import-time code              |
| `infra`    |        38 | all known noise: message wording, mypy refusals                                |
| `pipeline` |        51 | all known noise: message wording, mypy refusals, import-time code              |

## Evals

`evals/graft-check/run.sh [scenario…]` runs the working copy of the `graft-check` skill headless with `claude -p` on
synthetic packages and greps its reports. It is opt-in and costs tokens, so no hook or CI job runs it; run it when the
skill changes. It needs `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) or `ANTHROPIC_API_KEY`. Scenarios and
checks: [evals/graft-check/README.md](evals/graft-check/README.md).

`evals/graft-vet/run.sh [scenario…]` does the same for the `graft-vet` skill, with the same token and opt-in. Its
`corpus` scenario vets a labelled corpus of synthetic skills and prints a score per skill and kind; run it when the
skill or the corpus changes, and compare runs before and after. `CORPUS_SKILLS="<name>…"` runs a few skills only,
`GRAFT_VET_SCORES=<dir>` keeps each score, and `evals/graft-vet/corpus.py compare` sums kept scores scored against the
same corpus and skill. Labels, the score and how to read it: [evals/graft-vet/README.md](evals/graft-vet/README.md).

## Releasing

A release turns `CHANGELOG.md`'s `[Unreleased]` into a version, tagged `v<version>`, uploaded to PyPI and published as a
GitHub release. Only a commit CI passed is tagged, and `main` never names a version before CI has passed it.

1. Pick the version from the sections under `[Unreleased]`, by [Semantic Versioning](https://semver.org/). An entry is
   breaking when it sits under `### Removed`, or under `### Changed` and a config, command or lock users already have
   stops working as before. Before 1.0, a breaking entry raises the minor version, anything else the patch. From 1.0, a
   breaking entry raises the major version, else an `### Added` or `### Deprecated` entry the minor, else the patch.

1. Branch from an up-to-date `main`, with the version in `v` for the commands below:

   ```sh
   v=0.2.0
   git switch main && git pull --ff-only && git switch -c "release/v$v"
   ```

1. Make one commit, `chore(release): <version>`:

   - In `CHANGELOG.md`, rename `## [Unreleased]` to `## [<version>] - <today, YYYY-MM-DD>`, and add an empty
     `## [Unreleased]` above it.
   - At the end of `CHANGELOG.md`, point `[Unreleased]` at `compare/v<version>...HEAD` and add `[<version>]` comparing
     the previous tag with `v<version>`; for the first release, `[<version>]` links `releases/tag/v<version>`. Both are
     URLs under `https://github.com/remigius42/skill-graft/`. mdformat then writes the labels in lower case and sorts
     them; leave them so.
   - Set `version` in `pyproject.toml`, then run `uv lock`.
   - In `README.md`'s Installation, replace each `skill-graft==<previous version>` with `skill-graft==<version>`, and
     each `@v<previous version>`, in the install commands and the paragraph naming the releases, with `@v<version>`.
     "The release tags after `v0.3.0`" keeps its version.

1. Push the branch, which runs CI, and wait for the run to pass:

   ```sh
   git push -u origin "release/v$v"
   gh run watch "$(gh run list --branch "release/v$v" --limit 1 --json databaseId --jq '.[0].databaseId')"
   ```

   If CI fails, fix it on the branch and push again. If `main` moved meanwhile, rebase the branch onto it, set the
   changelog date to today, and push with `--force-with-lease`.

1. Fast-forward `main` to the release commit and tag it, signed with the SSH key the README names. Only once the
   signature checks, push `main` and the tag in one atomic push, so `main`'s README never names a tag that is not there:

   ```sh
   git switch main && git merge --ff-only "release/v$v"
   git tag -s "v$v" -m "skill-graft $v" && git verify-tag "v$v" && git push --atomic origin main "v$v"
   ```

   If `git verify-tag` fails, delete the tag with `git tag -d "v$v"`, fix the configuration below and tag again.

   Signing needs `gpg.format ssh` and `user.signingkey` set to that key in the repository's `git config`, not
   `--global`, and `git verify-tag` needs `gpg.ssh.allowedSignersFile` naming a file with the README's line. GitHub
   shows the tag as **Verified** only while the key is a signing key on GitHub and the tagger's email, the README's, is
   verified there.

1. The tag's push starts `publish.yml`, which builds the release from the tag and waits for you before uploading it to
   PyPI. Once its `build` job has passed, approve the `publish` job (**Review deployments**, `pypi`, **Approve and
   deploy**) and wait for it. The loop waits until GitHub has created the run for the tag's commit:

   ```sh
   until run="$(gh run list --workflow publish.yml --commit "$(git rev-parse "v$v^{commit}")" --limit 1 \
     --json databaseId --jq '.[0].databaseId // empty')" && [ -n "$run" ]; do sleep 5; done
   gh run view "$run" --web && gh run watch --exit-status "$run"
   ```

   If it fails for a reason outside the workflow, such as an outage, re-run its failed jobs and approve again. A run
   skips the files PyPI already holds, so it also completes an upload that stopped halfway:

   ```sh
   gh run rerun --failed "$run"
   ```

   If the workflow itself must change, a re-run would run the tag's copy of it again. Fix it on `main`, add the branch
   rule `main` to the `pypi` environment (below), start the run by hand for the tag, approve it, and remove the rule
   once it has passed:

   ```sh
   gh workflow run publish.yml -f tag="v$v"
   ```

1. Publish the GitHub release, with that version's changelog section as its notes:

   ```sh
   awk -v v="$v" 'index($0, "## [" v "]") == 1 { f = 1; next } f && (/^## \[/ || /^\[[^]]*\]: /) { exit }
     f && NF { while (n) { print ""; n-- } s = 1; print; next } f && s { n++ }' CHANGELOG.md > notes.md
   gh release create "v$v" --verify-tag --title "skill-graft $v" --notes-file notes.md && rm notes.md
   ```

1. Delete the branch: `git branch -d "release/v$v" && git push origin --delete "release/v$v"`.

A wrong tag not yet on PyPI and nobody has installed is removed by first cancelling its publish run, which may wait for
approval with a build of the wrong commit, then the release, if there is one yet, and the tag:

```sh
gh run list --workflow publish.yml --commit "$(git rev-parse "v$v^{commit}")" --json databaseId,status \
  --jq '.[] | select(.status != "completed") | .databaseId' | xargs -r -n1 gh run cancel
gh release delete "v$v" --cleanup-tag --yes || { git push origin --delete "v$v"; }; git tag -d "v$v"
```

Once it is on PyPI or someone may have installed it, leave it and release a fixed patch version instead. PyPI never
takes a version twice, not even after it is deleted: yank the wrong one instead, on its release page under **Manage
project**, so that installers skip it unless it is pinned.

The upload needs a setup done once, on PyPI and on GitHub. On pypi.org, under **Publishing**, a trusted publisher for
the project `skill-graft`: owner `remigius42`, repository `skill-graft`, workflow `publish.yml`, environment `pypi` (a
pending publisher until the first upload; it does not reserve the name). In the repository's **Settings**,
**Environments**, the environment `pypi`: deployments limited to the tags `v*.*.*`, so a run started by hand, which
starts from `main`, is refused until `main` is added for it; required reviewer the maintainer, with **Prevent
self-review** off, or the only maintainer could never approve.
