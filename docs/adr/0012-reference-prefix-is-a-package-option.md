# A reference prefix is a package option that touches only references

A Claude Code plugin `foo` names its **Skills** `foo:<name>`, so a vendored **Reference** must read `/foo:grilling`.
`reference-prefix = "foo:"`, a top-level key, puts that string before the **Deployed name** in every **Reference** to a
**Hull** **Skill**, and nowhere else: folders and `name:` keep the **Deployed name**, and **Skill IDs**, **Binds** and
**Patches** keep upstream names. It is one key per **Package**, not a **Source** option like `prefix` (ADR 0005): the
harness puts one prefix before every skill of the plugin, whichever **Source** it came from, so a per-**Source** value
could only be set wrong. Since it changes no **Deployed name**, uniqueness, **Reserved names** and the lock's `deployed`
are as without it.

A **Package** with the key holds skills that work only inside the plugin, so every command that writes its
`.apm/skills/` refuses the key where APM deploys it: in user scope, which `init` registers, and in a project whose
`apm.yml` lists the **Package**. `deploy` also refuses it unless `--no-apm-install` or `--into` is given, as a
**Package** may be registered after it was vendored. Inspecting stays possible: `tree`, `why`, `vet` and dry runs.

## Considered Options

- `:` in `prefix` or `[rename]`: it would put `:` in folder names, which Windows cannot check out, and in `name:`, which
  the Agent Skills format does not allow, and rely on Claude Code not doubling an explicit `name: foo:x`.
- A **Source** option: one prefix per plugin, not per **Source**.
- Refusing it in `config.load`: the editing commands parse the config themselves, and `tree`, `why` and `vet` pass
  through `load`, which would keep a user from inspecting the **Hull** before removing the key.
- A separator built in: which one is the harness's choice, so the string is used as written; one ending in a letter or
  digit warns.

## Consequences

Every resolved prose **Reference** is rewritten, not only those to a renamed **Skill**, so a word that matches a
**Hull** **Skill**'s name changes; the commands that vendor in place count the words, and `tree` shows the **Skills**
they name. The lock records the key after `version`, only when set, so `version` stays 1, and `deploy` refuses a changed
value as it refuses any other difference from the lock.
