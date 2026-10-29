# Design

## Context

`compute.check_refs(config, given)` raises on the first git **Source** with no `ref` that is not in `given`, naming only
it. `update` calls it with the selected aliases as `given`, before any remote is contacted; `compute_hull` calls it for
every command, with the refs it was given (none outside `update`). Only `update` knows the flags it was run with.

## Goals / Non-Goals

**Goals:** one error per run, whose suggested command gets past it: no loop between hints.

**Non-Goals:**

- Updating unnamed **Sources** implicitly. `update a` moving `b` too would break "only the named sources" and write a
  `ref` the user did not ask for.
- Reporting every later error up front. The suggested command may still fail on something else, such as an added
  **Source**'s invalid `branch`, checked only once it is selected.

## Decisions

- **One check, one message.** `check_refs(config, given, flags="")` stays the only place that refuses, so `update` and
  the other commands cannot drift apart, and no ordering between two checks has to hold. It names the git **Sources**
  without `ref` that are not in `given` (`source 'b' has no ref` for one, `sources 'b', 'c' have no ref` for several),
  and suggests `skill-graft update`, then the aliases in `given` plus those, each once, in config order, then `flags`.
  Naming only the ones not given tells the user what blocks the run; putting `given` in the command is what breaks the
  loop: with `a` and `b` both without `ref`, `update a` suggests `update a b`, not `update b`, which fails on `a`.
- **`update` passes its flags**: `--dry-run` when it was given or `--expect` was, and `--diff <file>` as given,
  shell-quoted, as `update`'s `review:` line quotes the user's aliases. `--expect` itself is dropped: the added
  **Sources** change the **Hull digest**, and the dry run then prints its own `review:` or `apply:` line.
- **Aliases unquoted**: config parsing allows only `[A-Za-z0-9][A-Za-z0-9._-]*`, which no shell treats specially.

## Risks / Trade-offs

- `--expect` turning into a dry run surprises a user who meant to apply → refusing to apply a **Hull** nobody reviewed
  is what `--expect` is for.
- A failing `update --diff <file>` still removes the Deployed diff it wrote before, as the Deployed diff requirement
  says, so no stale review survives a failed run.
