# Tasks

Apply with the `mp-tdd` skill: each task red-green-refactor, one commit. `pre-commit run --all-files` stays green.

## 1. Subdirectory segments

- [ ] 1.1 `SEGMENT` in `config.py`, and `_relative_folder` requiring each segment to match it, its error naming the
  rule, as design.md says. Tests in `tests/pipeline/test_config.py`, one per scenario of the config delta's "Git source
  subdirectory": the new "Hidden folder" loads, "Character outside the name characters" fails naming
  `sources.cp.subdirectory` and `A-Z a-z 0-9 . _ -`; verify they fail first, and the existing subdirectory tests pass
  unchanged

## 2. Skill folders use name characters

- [ ] 2.1 `discovery.index` checks each **Skill**'s path below the walked folder against `SEGMENT`, after `_check`, and
  files a bad one as `unreadable`, keyed and its path escaped over `os.fsencode` bytes as design.md says; the `invalid`
  error escapes its name and path the same way. Tests in `tests/pipeline/test_discovery.py`, one per scenario of the
  three skill-discovery delta requirements, written first and failing; "Shell syntax in a folder" builds a git
  **Source** with the `Upstream` helper and asserts no file `x` appears; "Bad path and a SKILL.md that is a device"
  patches `read_name` to fail if called on it; "Bind target" goes in `tests/pipeline/test_hull.py` if the bind tests
  live there. `test_skill_at_the_source_root` passes unchanged
- [ ] 2.2 Add one sentence to `docs/adr/0007-upstream-text-is-untrusted.md`: every folder below a **Source**'s root on a
  **Skill**'s path, and so every segment of the lock's `upstream`, uses `[A-Za-z0-9._-]` only. Verify it reads correctly
  against the spec delta

## 3. graft-check checks the lock

- [ ] 3.1 In `skills/graft-check/SKILL.md` step 2, before "Read the lock", the `awk` command of design.md: a version
  other than 1 takes the existing version path, else a count above 0 ends the **Check** with "the lock holds a value
  skill-graft would not write" and the advice to update skill-graft; the version check after reading goes. Test in
  `tests/cli/test_check.py`, written first and failing: extract the command from the skill's text, run it on a lock from
  a real `build --into` with an entry, a rename, a **Bind**, a patch and a prose suggestion, which counts 0 and exits 0,
  and on that lock edited to hold `upstream = "."` or `".claude/skills/tdd"`, which count 0; then with an `upstream`,
  `id`, `from`, `to` or `deployed` holding `$(x)`, a space, `\n` or `..`, and with `upstream="x"` and
  `"upstream" = "x"`, `patches = [], upstream = "$(x)"`, a header `[[skills]] # x` or `[skills.x]` and a top-level
  `upstream = "$(x)"`, each counting 1; and `version = 2` with an unknown key, printing `version: 2`
- [ ] 3.2 In step 3, a git **Source**'s root is the whole of `why`'s `upstream:` line when the lock's `upstream` is `.`.
  Verify by reading step 3 against the check delta's "Skill at a source's root"
