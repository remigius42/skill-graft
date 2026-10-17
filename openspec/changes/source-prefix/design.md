# Design

## Context

Every consumer of a **Deployed name** already reads it from one place: `config.deployed(config, skill)` feeds
`Hull.deployed` (`hull.py`) and the entries-only uniqueness check (`resolve.py`). `rename.rewrites`, `vendor`,
`lock` (`deployed`, tree `as`) and `explain` (`why` by **Deployed name**) all follow `Hull.deployed`, comparing
it with `skill.name`. Only three places reason about *why* a name differs: `rename._hint` and the
`skill not in config.renames` tests in `check_unique` and `check_reserved`, and `edit.rename`'s removal test
`name == skill.name`.

## Goals / Non-Goals

**Goals:** change `deployed`, the hints and `edit.rename`'s removal test; leave the rest to follow.

**Non-Goals:** a `prefix` command; a suffix; warning about a `[rename]` key that equals the prefixed name;
hints that suggest adding a `prefix`.

## Decisions

- **`Config.prefixes: dict[str, str]`** (alias → prefix, only **Sources** that set one), parsed in `_sources`
  for both kinds. Alternative: a `prefix` field on `PathSource` and `GitSource`. Rejected: every reader would
  need `config.sources[alias].prefix` across a union, and the cache and git code that take a **Source** have no
  use for it.
- **`config.default_name(config, skill)`**: the prefix plus the name, else the name. `deployed` is
  `config.renames.get(skill, default_name(config, skill))`, and `edit.rename` removes the key when
  `name == default_name(...)`. One function keeps the build and the editor agreeing on what "no key" means.
- **Hints in one place.** `_hint(config, skill)` gets three cases: a key (`change [rename] "<id>" = "<v>"`), a
  prefix (`add a [rename] key for "<id>", or change [sources.<alias>] prefix = "<p>"`), neither (today's
  `[rename] "<id>" = "<alias>-<name>"`). `check_unique` picks the **Skill** to hint for in the order neither,
  renamed, prefixed, by the same "chosen by the user" test; `check_reserved` offers the shipped warning's
  suggestion only for neither. The test "the user chose this name" becomes `skill in renames or skill.alias in prefixes`.
- **Template.** `init.py`'s commented example gains `# prefix = "mp-"` under `[sources.mp]`, so the option is
  discoverable without a hint suggesting it.

## Risks / Trade-offs

- **`rename <id> <upstream name>` writes a key under a Prefix** instead of removing one. Mitigation: only
  reachable after adding a `prefix`, which did not exist before; the tree shows the result.
- **Adding a `prefix` to an existing Source changes every vendored copy and lock hash of it at once.**
  Mitigation: that is the intent; `resolve` prints the new tree before `build` deploys it.
- **Old `[rename]` keys equal to the prefixed name linger silently.** Mitigation: harmless; the proposal names
  the cleanup of this repository's own TOML as a follow-up.
