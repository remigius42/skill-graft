# Proposal

## Why

A Claude Code plugin `foo` names each of its **Skills** `foo:<name>`, and neither `plugin.json` nor `marketplace.json`
can turn that off. A **Package** vendored into a plugin keeps writing **References** as bare **Deployed names**
(`/grilling`, `Skill(grilling)`), so curating a plugin's skills with skill-graft fails where it matters. Tested on
Claude Code 2.1.319: a bare `Skill(grilling)` resolves only while no other skill has that name; with a second plugin
holding one it fails ("Several skills match that name"), and with a personal or project skill of that name the agent ran
that one instead in two runs of three, silently. `Skill(foo:grilling)` reached the plugin's own skill every time.
Neither a **Rename** nor a **Prefix** helps: each sets the **Deployed name**, carried into the folder and `name:` as
well, which must stay bare, and neither accepts `:`. A **Bind** only chooses the target.

## What Changes

- **`reference-prefix`**: a new optional top-level key, `reference-prefix = "foo:"`. Every **Reference** that resolves
  to a **Hull** **Skill**, **Binds** applied, is vendored as the reference prefix followed by the target's **Deployed
  name**, in every form: `/foo:grilling`, `Skill(skill: "foo:grilling")`, `` `foo:grilling` ``, a self-**Reference**
  included. Folders and `name:` keep the **Deployed name**; **Skill IDs**, **Binds** and **Patches** keep upstream
  names. The string is used as written, so the separator is the user's: no harness is built in.
- **Validation at load**: a string of the name characters plus `:`, `[A-Za-z0-9][A-Za-z0-9._:-]*`; anything else is an
  error naming `reference-prefix`. A value ending in a letter or digit is a warning, since `/grilling` then becomes
  `/foogrilling`.
- **Never in a package APM deploys**: with a reference prefix, the vendored copies work only inside the plugin, so APM
  would deploy skills whose **References** point nowhere. Every command that writes the **Package**'s `.apm/skills/`
  (`resolve`, `deploy`, `update`, the editing commands) refuses the key in user scope, whose **Package** `init` always
  registers with APM, and in a project **Package** the project's `apm.yml` lists, before reading any **Source**. Dry
  runs, `tree`, `why` and `vet` still run; `deploy --into`, and so graft-check, checks the **Hull** against a lock only
  `resolve` writes, so it serves a **Package** no `apm.yml` lists. In a **Package** no `apm.yml` lists, `deploy` without
  `--no-apm-install` or `--into` also exits non-zero, naming `reference-prefix` and
  `skill-graft deploy --no-apm-install`, in case the **Package** gets registered later.
- **Prose counted**: as with renames, every resolved prose **Reference** is rewritten, now each one, so a command that
  writes the **Package**'s `.apm/skills/` says how many prose words got the prefix, and `tree` shows the **Skills** they
  name.
- **`why` reads the prefixed name**: `skill-graft why foo:grilling` reads `foo:grilling`, the name a vendored
  **Reference** shows, as the **Deployed name** `grilling`, as `why grilling` would; without a reference prefix,
  `foo:grilling` is read as before.
- **Mermaid names it**: `tree --format mermaid` opens with the Mermaid front matter `title: "reference-prefix: foo:"`
  when the key is set, so a chart whose prose edges all show says why; the text `tree`, which graft-check reads and
  `resolve` prints, is unchanged.
- **Lock**: records `reference-prefix` when set; `version` stays 1. Setting, changing or removing it makes `deploy`
  refuse until `resolve` accepts it, for path **Sources** too.
- **graft-check**: takes `reference-prefix` from its throwaway lock and gives it to each reader, in `full` and `uses`
  mode, so a **Reference** rewritten to `<reference prefix><deployed name>` is intended, not a wrong rewrite; its lock
  check accepts the new key; and it closes by telling the user to run `deploy --no-apm-install` instead of `deploy` when
  the key is set.
- **Docs**: `CONTEXT.md` gains **Reference prefix**; the README's config section and `docs/howto.md` (a new "Curate a
  plugin's skills" section: the package in the plugin, made by hand without `init` and so without APM, `resolve`, and
  `plugin.json`'s `"skills": "./.apm/skill-graft/.apm/skills/"`) document it; a new ADR records why it is a package
  option that touches only **References**. The `init` template does not show it: every **Package** `init` makes is
  registered with APM, where the key is refused.

Out of scope: reading `ns:name` in upstream text as a **Reference** to `name` (a plugin **Source**'s own calls); a
reference prefix per **Source**; `init` without APM registration; relaxing the shipped **Reserved name** warnings for a
namespaced plugin; showing the reference prefix in the text `tree`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `config`: `reference-prefix` becomes a supported, validated top-level key.
- `renames`: **References** carry the reference prefix before the **Deployed name**; folder and `name:` do not; prose
  rewrites are counted.
- `resolve`: the lock records `reference-prefix`.
- `deploy`: no command writes prefixed copies into a **Package** APM deploys; with a reference prefix, `deploy` runs
  only with `--no-apm-install` or `--into`, and refuses a lock of another reference prefix.
- `explain`: `why` reads the reference prefix followed by a **Deployed name** as that **Deployed name**;
  `tree --format mermaid` titles the diagram with the reference prefix.
- `check`: readers are told the reference prefix, the lock check accepts it, and the close names the right `deploy`.

## Impact

- Code: `pipeline/config.py` (key, validation, warning, `Config.reference_prefix`), `pipeline/hull.py`
  (`Hull.reference_prefix` and `Hull.called`), `pipeline/rename.py` (`rewrites` writes `called`), `pipeline/lock.py`
  (the key, and `drift` naming it), `commands/transaction.py` (the APM gate and the prose count in `resolving`),
  `commands/explain.py` (prose edges shown by `called`, `why` reading the prefixed name, the Mermaid title),
  `commands/deploy.py` (the refusal), with tests.
- graft-check: `skills/graft-check/SKILL.md` (lock check, step 3 takes the key from the lock, step 4 passes it, step 7's
  `deploy`) and `reader.json` (the input and the **rewrite** kind).
- Docs: `README.md`, `docs/howto.md`, `docs/architecture.md`, `CONTEXT.md`,
  `docs/adr/0012-reference-prefix-is-a-package-option.md`.
