# Tasks

Apply with the `mp-tdd` skill: each task red-green-refactor, one commit. Every existing test passes unchanged;
`pre-commit run --all-files` stays green at every commit. Git **Sources** in the new tests come from the
`Upstream`/`seed` helpers in `tests/conftest.py`; a `ref` "not cached, remote unreachable" is a `git` URL to a missing
folder.

## 1. One source per check

- [ ] 1.1 Split `compute._folders`'s per-**Source** body into `_folder` (checkout, then `_subdirectory`) and make
  `known` check its own **Source**'s `ref` (`check_refs(config, ())` when it is git and has none) and read only
  `_folder` of it; tests in `tests/commands/test_edit.py` for the `edit` scenarios "Unknown skill before another
  source's missing ref", "Unknown target before another source's missing ref", "Known skill, another source without a
  ref" and "The skill's own source without a ref"; verify they fail first (the first two today say `no ref`), then pass
- [ ] 1.2 Tests for the no-op scenarios "No-op bind ignores other sources" and "No-op rename fetches no other source",
  and for `renames`' "Entries clash after rename reads only its source" (no fetch for `other`: its folder in the cache
  stays absent); verify they pass on 1.1 alone, else fix `known` until they do
- [ ] 1.3 A test in `tests/commands/test_explain.py` that `why mp/notes`, outside the **Hull**, with a second git
  **Source** in the config, still errors naming `skill-graft add mp/notes`; it should pass unchanged (design: `why`
  keeps calling `known`)

## 2. Docs

- [ ] 2.1 `docs/design.md`: the `rename` and `bind` bullets say the given **Skill ID** is checked by reading only its
  **Source**, so a missing **Skill** is reported before another **Source**'s missing `ref`, and a no-op reads no other
  **Source**; verify `pre-commit run --all-files` passes
