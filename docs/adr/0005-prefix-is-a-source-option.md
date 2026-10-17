# A prefix is a source option, not a glob rename

Namespacing a whole **Source** is `prefix = "mp-"` under `[sources.mp]`, which gives every **Hull** **Skill** of
it, dependencies `update` pulls in later included, the **Deployed name** `mp-<name>`; an exact `[rename]` key
still wins. Glob keys in `[rename]` (`"mp/*" = "mp-*"`) were rejected: they mix patterns into a table keyed by
**Skill ID** and raise questions a fixed string does not (precedence between overlapping patterns, when a
pattern counts as unused, what `skill-graft rename` edits), and `*` only ever makes sense as a prefix or suffix.
Because the prefix applies without a key, renaming a **Skill** back to its upstream name now writes an explicit
key rather than removing one.
