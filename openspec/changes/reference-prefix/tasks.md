# Tasks

Apply with the `mp-tdd` skill: each task red-green-refactor (failing test first, then code), one commit, hooks green.
New words go into `.cspell.yaml`. Tests set `HOME` to `tmp_path` and build synthetic **Sources** in the test.
`reference-prefix` stays an unsupported key until task 1.1 honors it in full (vendored, locked, shown, kept from APM),
so no commit accepts intent it ignores or mishandles. No task runs `evals/`. The pytest hook fails below 99% line and
branch coverage, so each task's tests cover its branches. After each task, run mutmut on each module it changed, one run
at a time, and kill its new survivors with tests, as `docs/mutation-testing.md` says; a pragma only on a line holding an
equivalent expression alone.

## 1. Reference prefix

- [x] 1.1 `reference-prefix` end to end. `pipeline/config.py`: a supported top-level key, validated by
  `REFERENCE_PREFIX` (`[A-Za-z0-9][A-Za-z0-9._:-]*`), into `Config.reference_prefix` (`""` when absent), a warning when
  it ends in a letter or digit. `pipeline/hull.py`: `Hull.reference_prefix`, set by `hull.walk`, and
  `Hull.called(skill)`. `rename.rewrites` compares with and writes `hull.called(target)`; folders and `set_name` keep
  `deployed`. `explain._shown_edges` compares prose edges with `called`. `pipeline/lock.py`: `render` writes
  `reference-prefix` after `version` when set; `drift` names it when it differs. `transaction.resolving`, when it writes
  in place: before reading any **Source**, refuses the key in user scope and when `apm.registered(scope)`; once it has
  vendored, prints the prose count. `commands/deploy.py`: without `--into`, after `transaction.load` and before
  `resolving`, `transaction.check_reference_prefix`: the refusals `resolving` makes, then, without `--no-apm-install`,
  exit 1 naming `reference-prefix` and `skill-graft deploy --no-apm-install`. Verify the delta scenarios: config
  (valid-reference-prefix, reference-prefix-not-allowed, no-separator-at-the-end, separator-at-the-end,
  reference-prefix-key, reference-prefix-on-a-source) in `tests/pipeline/test_config.py`; renames (slash-reference,
  every-form, after-a-rename-or-a-prefix, self-reference-with-a-reference-prefix, prefix-used-as-written,
  unresolved-names-keep-their-text, patched-reference) in `tests/pipeline/test_rename.py`, and prose-prefixed, no-prose,
  nothing-written in `tests/commands/test_resolve.py`; resolve (reference-prefix-recorded) in
  `tests/pipeline/test_lock.py`; deploy (plain-deploy-refused, refused-before-any-fetch, without-apm, into-a-folder,
  user-scope, registered-project-package with `resolve` and with `bind`, unregistered-project-package,
  inspecting-stays-possible, reference-prefix-removed with a path **Source**, reference-prefix-set) in
  `tests/commands/test_deploy.py`; and a `tree` test in `tests/commands/test_explain.py` that a prose edge to an
  unrenamed **Skill** shows with a reference prefix and not without. `mutation/targets.py` lists
  `config.REFERENCE_PREFIX` beside `config.NAME`, and the regex harness run on it leaves no survivor. Every existing
  test passes, and a config without the key vendors and locks byte for byte as before.

- [x] 1.2 `why` reads the reference prefix followed by a **Deployed name** as that **Deployed name**: `explain.find`
  matches a name without `/` as written, then with `hull.reference_prefix` stripped from its front. Verify the explain
  delta scenarios (reference-prefixed-name, deployed-name-starting-with-the-reference-prefix,
  prefixed-upstream-name-of-a-renamed-skill, no-reference-prefix) in `tests/commands/test_explain.py`, then run mutmut
  on `commands.explain` and kill its new survivors.

- [ ] 1.3 `tree --format mermaid` titles the diagram with the reference prefix: `explain.mermaid` writes the Mermaid
  front matter `---`, `title: "reference-prefix: <value>"`, `---` before `flowchart TD` when `hull.reference_prefix` is
  set, and nothing more without it. Verify the explain delta scenarios (mermaid-titled-with-the-reference-prefix,
  no-title-without-one) in `tests/commands/test_explain.py`, then run mutmut on `commands.explain` and kill its new
  survivors.

## 2. graft-check

- [ ] 2.1 `skills/graft-check/SKILL.md`: the lock check's awk accepts a top-level `reference-prefix` line whose value
  matches `[A-Za-z0-9][A-Za-z0-9._:-]*`; step 3 takes `reference-prefix` from the throwaway lock; step 4 adds a
  `reference-prefix: <value>` input line to every `full` and `uses` reader when it is set; step 7 tells the user to run
  `skill-graft deploy --no-apm-install` instead of `skill-graft deploy` when it is set. `reader.json`'s Input,
  **Deployed name** term and **rewrite** kind say a **Reference** is rewritten to the reference prefix followed by the
  **Deployed name**, and one left without it is a **rewrite** finding. Verify in `tests/cli/test_check.py`, as the tests
  there check other inputs: the lock check counts 0 for reference-prefix-in-the-lock and above 0 for
  crafted-reference-prefix; the report filter passes a `full` report whose `text` and `vendored` hold `/foo:grilling`,
  and a `uses` report whose `text` holds `foo:follow-up`; the reader prompt and `SKILL.md` name `reference-prefix`, step
  3 names the lock as its source, and step 7 names `--no-apm-install`. The prefixed-rewrites-not-reported,
  reference-prefix-in-a-word-that-names-no-skill, written-in-another-form and uses-of-a-name scenarios, and the close's
  choice, are judged by the agent, so they are left to an eval run only on the user's request.

## 3. Docs

- [ ] 3.1 `CONTEXT.md` gains **Reference prefix** (a string the harness needs before every **Skill**'s name, put before
  the **Deployed name** in every **Reference**, never in a folder or `name:`; _Avoid_: Namespace, plugin prefix), and
  **Reference** and **Deployed name** point to it. `docs/adr/0012-reference-prefix-is-a-package-option.md` records
  design.md's decisions on a package key, on not allowing `:` in names, and on refusing it where APM deploys.
  `README.md`'s config section shows and explains the key, and the `deploy` row says it then needs `--no-apm-install`.
  `docs/howto.md` gains "Curate a plugin's skills": make `<plugin>/.apm/skill-graft/skill-graft.toml` by hand (no
  `init`, so APM is not registered in the plugin's repository, which would refuse the key), set
  `reference-prefix = "<plugin>:"`, run `resolve` or `deploy --no-apm-install`, point `plugin.json`'s `"skills"` at
  `./.apm/skill-graft/.apm/skills/`, write the plugin's own calls to them with the prefix, and end a stray prose rewrite
  with a **Patch**, not a **Bind**. `docs/architecture.md`'s rename paragraph mentions `Hull.called` and the lock
  paragraph `reference-prefix`. Verify: the README's TOML example parses through `config.parse`, and the hooks pass on
  the changed files.
