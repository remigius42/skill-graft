# Design

## Context

See proposal.md for why. Today one value, `Hull.deployed[skill]`, serves three places: the vendored folder
(`vendor.py`), the `name:` line (`rename.set_name`) and the text every **Reference** is rewritten to (`rename.rewrites`,
which rewrites when `hull.deployed[target] != ref.name`). `rewrites` has five callers, all handing it only the `Hull`:
`vendor.py`, `lock.py` (hashes), `commands/vet.py`, `commands/review.py` (twice) and `commands/update.py`.
`commands/explain.py` shows a prose edge in the tree only when vendoring rewrites it, by the same comparison, and
graft-check reads that tree for each reader's targets. A plugin needs the folder and `name:` bare but the **References**
prefixed, so the third use has to come apart from the other two.

`lock.drift` refuses a changed hash only for a git **Source** or a patched **Skill**; an unpatched path **Source**
**Skill** whose hash alone changed is deployed with a notice, as its own text may change between `resolve` and `deploy`.
So hashes alone do not make `deploy` refuse a changed reference prefix.

Claude Code facts this rests on, checked on 2.1.319 (see proposal.md): a plugin's skills are `<plugin>:<name>`, `name:`
setting `<name>`; `plugin.json`'s `"skills"` takes a path that starts with `./` inside the plugin and adds to the
default `skills/` scan; a path into a dot folder (`./.apm/...`) validates, installs from a local and a git marketplace
with the folder kept, and loads its skills.

## Goals / Non-Goals

**Goals:**

- One place decides the text a **Reference** to a **Skill** is vendored as; every caller of `rewrites`, and the tree,
  agree on it without new parameters.
- No harness built in: skill-graft never adds a separator itself.
- No prefixed copy written into a **Package** that APM deploys, whichever command vendors it, while inspecting stays
  possible.

**Non-Goals:**

- Changing the lock `version` or the **Hull digest**'s inputs.
- Re-reading vendored text: skill-graft never scans its own output, so `foo:grilling` not being a **Reference** to the
  scanner does not matter here.

## Decisions

- **`Hull.reference_prefix` and `Hull.called(skill)`**: the `Hull` carries the config's reference prefix (`""` when
  unset), set by `hull.walk`, and one method gives a **Skill**'s name as **References** to it are vendored,
  `reference_prefix + deployed[skill]`. `rewrites` compares with and writes `hull.called(target)`; `set_name` and the
  folder keep `deployed`; `explain._shown_edges` compares with `called`, so with a reference prefix every resolved prose
  edge shows, as every one is rewritten. Alternative: a second map `called` beside `deployed`, rejected as state derived
  from two others that every later `Hull` built or replaced would have to keep in step. Alternative: a parameter on
  `rewrites`, rejected because five callers and the tree would each pass it and could disagree.
- **A package key, not a source option**: the harness puts one prefix before every skill of the plugin, whichever
  **Source** it came from, so a per-**Source** value could only be set wrong. Unlike `prefix` (ADR 0005), it changes no
  **Deployed name**, so uniqueness, **Reserved names**, the lock's `deployed` and `tree`'s `as <deployed name>` are
  untouched. Recorded as ADR 0012.
- **Not `:` in `prefix` or `[rename]`**: it would put `:` in folder names, which Windows cannot check out, and in
  `name:`, which the Agent Skills format does not allow; and it relies on Claude Code not doubling an explicit
  `name: foo:x`, documented only from 2.1.246. Keeping `NAME` for names and allowing `:` only in the reference prefix
  keeps every path skill-graft writes as it is.
- **Validation**: `[A-Za-z0-9][A-Za-z0-9._:-]*` (`config.REFERENCE_PREFIX`), a full match. No `/` (a slash **Reference**
  `/foo/grilling` reads as a path), no whitespace or quotes (they would break the `Skill("…")` and sentence forms), and
  a leading letter or digit as for every name. A value ending in a letter or digit is used as written, but warns:
  `reference-prefix "foo" ends in a letter or digit: /grilling is vendored as /foogrilling`. Requiring a separator was
  rejected: which one is the harness's choice. The pattern guards what skill-graft writes into Markdown, so the regex
  harness (`mutation/`) targets it, as it does `config.NAME`.
- **Refused where APM deploys, in `transaction.resolving`**: every command that writes the **Package**'s `.apm/skills/`
  goes through `resolving`: `resolve`, `deploy`, `update`, and the editing commands, which parse the config themselves
  (`edit.py` calls `config.parse`, not `load`). So `resolving` checks first, before it reads any **Source**, when it
  writes in place (`write` true and `skills` the **Package**'s): in user scope the key is an error (`init` registers
  `~/.apm/skill-graft` with APM, and every user-scope `deploy` runs it); in project scope it is one when
  `apm.registered(scope)` finds the project's `apm.yml` listing the **Package**. The message names `reference-prefix`,
  the **Package** and, in project scope, the `apm.yml`. Alternatives: `config.load`, rejected because the editing
  commands bypass it and `tree`, `why` and `vet` pass through it, which would keep a user from inspecting the **Hull**
  before removing the key; a check in `deploy` alone, rejected because the other writers fill the same `.apm/skills/`,
  which the next `apm install` the user runs for any reason would deploy. `deploy --into` is no inspecting command: it
  refuses a **Hull** other than the lock's, which only `resolve` writes, so in such a **Package** it, and graft-check,
  end at `resolve`'s refusal, which names what to do.
- **`deploy` refusal kept**: the registration scan has limits (see Risks), and a **Package** may be registered after it
  was vendored; so `deploy` still checks the key right after `transaction.load` and before `resolving`, reading no
  **Source**, fetching nothing and writing nothing; `--into` skips it. One check, `transaction.check_reference_prefix`,
  serves both: `resolving` calls it with `apm_install` false, `deploy` with `apm_install` true unless
  `--no-apm-install`. It refuses first where APM deploys, as `resolving` would, so `deploy`'s hint never names a command
  that then fails; only in a **Package** no `apm.yml` lists does `deploy` say
  `reference-prefix "foo:" makes skills that work only inside a plugin; run skill-graft deploy --no-apm-install`.
  Alternative: a check of its own in `deploy`, rejected because in user scope and in a listed **Package** its hint led
  to a second refusal.
- **`why` strips the reference prefix**: `explain.find` matches a name without `/` as a **Deployed name** as written,
  then with the reference prefix removed from its front, so the name a vendored **Reference** shows reaches its
  **Skill**, while a **Deployed name** that starts with the prefix (`mp-tdd` with `reference-prefix = "mp-"` and
  `prefix = "mp-"`) still names its own; and every hint `why` gives for a bare name (an upstream name after a rename, a
  prose suggestion) applies after the prefix too. A name the prefix does not start is read as before. Alternative:
  accepting `called` names as a second lookup, rejected as a second path to every hint.
- **A Mermaid title, not labels**: `explain.mermaid` puts Mermaid front matter, `title: "reference-prefix: foo:"`,
  before `flowchart TD` when the reference prefix is set: it applies to every edge, so one line says it, and nodes and
  edges stay as without it. The value matches `REFERENCE_PREFIX`, which holds no `"` or `\`, so it needs no escape in
  the YAML string. Alternatives: `as foo:grilling` on each node, rejected as wrong (the folder and `name:` stay
  `grilling`); the rewritten form on each edge label, rejected as the same rewrite repeated on every edge; a line in the
  text `tree`, rejected because graft-check reads it line by line and every writing command prints it.
- **Lock records it**: a top-level `reference-prefix = "foo:"` after `version`, only when set, so a lock without it is
  byte for byte as before and `version` stays 1. `drift`'s shape comparison already covers top-level keys, so a changed
  value refuses for path **Sources** too; its refusal names `reference-prefix` first, then the **Skills** whose hash it
  changed. graft-check's lock check gains that line form, its value matched by the pattern alone, as `deployed` is.
- **Prose count**: `transaction.resolving`, once it has vendored in place, under the same condition as the gate, prints
  `reference-prefix: <n> prose words prefixed; skill-graft tree shows the skills they name`
  (`1 prose word … the skill it names` for one) when `n`, the resolved prose **References** in `hull.occurrences`, is
  above 0 with a reference prefix set. Dry runs and `deploy --into`, which graft-check runs, print none. It counts
  occurrences, not edges, as each changed word is one.
- **graft-check**: step 3 takes `reference-prefix` from the throwaway deploy's lock, which tomlkit wrote and step 2's
  lock check has matched against the pattern, never from `skill-graft.toml`, whose written form (a literal string, an
  escape, a comment) can differ from the value; step 4 adds a `reference-prefix:` input line to every `full` and `uses`
  reader when it is set; `reader.json` says under **Deployed name** and the **rewrite** kind that a **Reference** is
  rewritten to the reference prefix followed by the **Deployed name**, so one left without it is a **rewrite** finding,
  its "Missed" case; step 7 tells the user to run `skill-graft deploy --no-apm-install` when the lock has the key. The
  reader's report and the report filter carry the text as written; the task checks that the filter passes a `:` in it,
  in both modes.
- **No template line**: every **Package** `init` makes is registered with APM, so a `reference-prefix` uncommented there
  would always be refused; the howto, which makes the **Package** by hand, carries the key alone.

## Risks / Trade-offs

- [Prose rewrites widen] With a reference prefix, every resolved prose **Reference** is rewritten, not only those to a
  renamed **Skill**, so a hyphenated word that matches a **Hull** **Skill**'s name in its own **Source** now changes
  even without renames. → It is the same rule renames already follow; the count says how many words, `tree` the
  **Skills** they name, and graft-check reads them. A **Patch** ends one stray word; `bind <alias>/<name> false` ends
  the name as a **Reference** in its whole **Source**, slash and Skill tool calls included, so it suits only a name that
  never means a **Skill**.
- [Harness behavior changes] The bare-name fallback and the `name:`/namespace rules are Claude Code's, partly
  undocumented. → The reference prefix relies only on the documented `<plugin>:<name>` form.
- [A plugin's own files] Commands, agents and hooks of the plugin are not vendored, so their calls to vendored skills
  are the plugin author's to write with the prefix. → The howto says so.
- \[`init` registers with APM\] `init --project` in a plugin would register the package with APM in the plugin's repo,
  after which the key is refused. → The howto makes the package by hand (`.apm/skill-graft/skill-graft.toml`); `resolve`
  and `deploy --no-apm-install` need no `apm.yml`.
- [Registration read in place] Each in-place write with a reference prefix in project scope reads the project's
  `apm.yml`. → A line scan of one small file, only when the key is set.
- [Registration scan's reach] `apm.registered` recognizes `- x` and `- path: x` list items, the forms APM itself writes;
  an `apm.yml` that lists the **Package** another way (flow style) reads as unregistered, and the key loads. → User
  scope is refused whatever its `apm.yml` says, and `deploy` without `--no-apm-install` refuses the key in every scope;
  the gap is a project `apm.yml` written by hand and an `apm install` run outside skill-graft.

## Migration Plan

None: the key is new and optional, and a config without it vendors and locks byte for byte as before.
