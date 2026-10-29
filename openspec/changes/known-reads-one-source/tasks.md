# Tasks

Apply with the `mp-tdd` skill: each task red-green-refactor, one commit. Every existing test passes unchanged;
`pre-commit run --all-files` stays green at every commit. Git **Sources** in the new tests come from the
`Upstream`/`seed` helpers in `tests/conftest.py`; a `ref` "not cached, remote unreachable" is a `git` URL to a missing
folder.

## 1. One source per check

- [x] 1.1 Split `compute._folders`'s per-**Source** body into `_folder` (checkout, then `_subdirectory`;
  `check_refs(config, ())` when a git **Source** has no `ref`) and make `known` read only `_folder` of its own
  **Source** and index it with `_index`, which `_indexes` shares; `edit.bind` calls `known` on every target but `false`,
  before its no-op check; tests in `tests/commands/test_edit.py` for the `edit` scenarios "Unknown skill before another
  source", "Unknown target before another source" (each with `other` lacking a `ref`, and with an unreachable one),
  "Known skill, another source without a ref" and "The skill's own source without a ref"; verify they fail first (the
  first two today say `no ref`), then pass; and that `rename` reads a git **Source** with `subdirectory` only in that
  folder
- [x] 1.2 Tests for the no-op scenarios "No-op bind ignores other sources" and "No-op rename fetches no other source",
  and for `renames`' "Entries clash after rename reads only its source" (no fetch for `other`: its folder in the cache
  stays absent, `other` being a reachable remote the cache lacks); verify they fail on the code before 1.1 and pass on
  it
- [ ] 1.3 A test in `tests/commands/test_explain.py` that `why mp/notes`, outside the **Hull**, with a second git
  **Source** in the config, still errors naming `skill-graft add mp/notes`; it should pass unchanged (design: `why`
  keeps calling `known`)

## 2. Docs

- [ ] 2.1 `docs/design.md`: the `rename` and `bind` bullets say the given **Skill ID** is checked by reading only its
  **Source**, so a missing **Skill** is reported before another **Source**'s missing `ref`, and a no-op reads no other
  **Source**; verify `pre-commit run --all-files` passes
