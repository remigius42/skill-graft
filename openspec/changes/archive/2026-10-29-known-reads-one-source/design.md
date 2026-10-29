# Design

## Context

`compute.known` parses the **Skill ID**, then takes `_folders(config, cache, {})[skill.alias]`: `_folders` runs
`check_refs` over every git **Source** and checks each one out (`cache.checkout`, fetching a missing commit), then
`known` indexes only the one it wants. Its callers are `edit.rename`, `edit.bind` (only for a key already in `[bind]`; a
new key's target is checked by resolving) and `explain.show_why` through `find`, on the path where a **Skill ID** is not
in the **Hull**.

## Goals / Non-Goals

**Goals:**

- `known` checks out one **Source**; its errors, for that **Source**, read as today.
- Each user-visible consequence decided once, and pinned in `edit` and `renames` (see specs).

**Non-Goals:**

- Reading fewer **Sources** while the **Hull** is computed: a **Reference** may resolve in any **Source**.
- Changing `add`, whose **Skill IDs** are checked by resolving, or `unbind`, which reads no **Source**.

## Decisions

### `known` reads one folder through a shared helper

Split the per-**Source** body of `_folders` into `_folder(config, cache, alias, ref)` (checkout, then `_subdirectory`),
which `_folders` loops over and `known` calls once, then indexes that folder with `_index`, which `_indexes` calls per
**Source**, so the rule confining a git **Source** to its checkout stays in one place. A git **Source** with no `ref`,
given or its own, makes `_folder` call `check_refs(config, ())`, which raises naming every git **Source** without one,
the same message and hint `build` gives; `_folders` has run `check_refs` already, so only `known` reaches it. Naming
them all, not just this one, saves the user a second failure: the edit then resolves, and resolving needs every `ref`.

Alternative: keep `check_refs` over all **Sources** at the start of `known`. It costs no fetch, so it alone keeps
today's error order. Rejected: see the next two decisions.

### A missing Skill comes before another Source's missing ref

With a bad **Skill ID** and another git **Source** without a `ref`, `rename` and `bind` now say the **Skill** is
missing; today they say `no ref`. The **Skill ID** is what the user just typed, and `update` cannot fix a typo:
reporting `no ref` first sends the user to `update`, after which the same command fails on the typo. A **Source** that
cannot be fetched is the same case: the typo is reported without touching the network.

Malformed IDs and undeclared aliases are still refused first, from the config alone; entry clashes are still reported
before any other **Source** is read, after the checked **Skill**'s **Source** (`renames`).

### `bind` checks every target up front

`bind` calls `known` on any target but `false`, not only for a key already in `[bind]`, before its no-op check. A new
key's target was checked only by resolving, which reports another **Source**'s missing `ref` first; the order above
would then hold for `rename` and not for `bind`. The check checks out one **Source** and indexes it, and resolving
indexes it again from the cache: a new **Bind** pays that **Source**'s discovery twice, as a changed one already did. A
malformed target or undeclared alias is now refused by that check, as `bind: '<target>' is not …`, not by resolving, as
`bind."<key>": '<target>' is not …`: the message no longer names the key, which the user just typed beside it.

Alternative: leave `bind` alone and pin the order only for a key already bound. Rejected: the typo case is the same
whether or not the key exists.

### A no-op reads no other Source

A no-op `rename` or `bind` returns before `_finish`, so it no longer requires other **Sources**' `refs` or a fetch; it
exits 0 with its notice. This matches `add` of an existing **Entry**, which already returns without reading any
**Source**, and the `edit` spec's "neither resolve nor write anything". The **Skill** itself is still checked, so
"Already bound to a skill gone upstream" still fails.

### `why` keeps calling `known`

`why` computes the **Hull** first, which checks every `ref` and checks out every **Source**; `known` is reached only for
a **Skill ID** outside the **Hull**, an error path. After this change it re-uses one cached tree and indexes one
**Source**. Looking the **Skill** up in the folders the **Hull** read instead would need `Hull` (or `compute_hull`) to
carry the per-**Source** indexes for one error message, and the fallback `_explain` runs on a `PatchError`'s partial
**Hull** would need them too. No output changes either way, so `explain` gets no spec delta.

## Risks / Trade-offs

- \[A no-op edit succeeds on a config whose next `build` fails on a missing `ref`\] → It wrote nothing, and `build`,
  `resolve` and every changing edit still fail with the `update` hint.
- \[Error order differs between `add` (resolves, so `no ref` first) and `rename`/`bind`\] → `add` checks its **Skill
  IDs** by resolving, which reads every **Source** anyway; the specs pin each command's order.
