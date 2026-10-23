# Tasks

Apply with the `tdd` skill: each task red-green-refactor, one commit.

## 1. Discovery checks SKILL.md before reading it

Tests that could block on a FIFO or device run under a timeout (`signal.alarm`), so a regression fails, not hangs.

- [ ] 1.1 In `discovery.index`, before `read_name`, refuse a `SKILL.md` whose `os.stat` fails or is not `S_ISREG`, in
  every **Source**, filing the name as unreadable with `<full path>/SKILL.md: not a regular file`; in `read_name`,
  open with `O_NONBLOCK`, `fstat` and require `S_ISREG` before reading; tests in `tests/pipeline/test_discovery.py`: a
  link to `/dev/zero` and a FIFO (other **Skills** found, nothing blocks), a dangling link and a link the user cannot
  stat (refused, no traceback), `read_name` on a FIFO (refused), a regular file linked from outside in an unconfined
  **Source** (read, as today); verify they pass
- [ ] 1.2 When `confined`, first refuse a `SKILL.md` whose real path leaves its **Skill**'s resolved folder, with
  `<full path>/SKILL.md: a symlink leading outside its skill`, before any stat; tests: links to an outside file whose
  `name:` is `leaked-marker`, to `/dev/zero` and to a missing path all give that one message (holding neither
  `leaked-marker` nor the target path), a link to a sibling **Skill**'s file (refused), a link to a file inside the
  **Skill** (read), and the same inside link in a **Skill** reached through a symlinked folder of the **Source**
  (read); verify they pass

## 2. End to end

- [ ] 2.1 In `tests/cli/test_git_build.py`, through a real git **Source**, the git-sources spec's scenarios "SKILL.md
  linked out of the tree", "Unused skill linked out of the tree" and "SKILL.md linked inside its skill"; in
  `tests/cli/test_build.py`, the skill-discovery spec's "SKILL.md linked to a device" and "Entry names it", under a
  timeout; verify they pass
- [ ] 2.2 Note in `docs/design.md`, where discovery and git **Sources** are described, both checks before a
  `SKILL.md` is read; verify `pre-commit run --all-files`

## 3. Changelog

- [ ] 3.1 If what a user sees changed (it does: commands no longer read such a `SKILL.md`, and name it in an error),
  add an entry to `CHANGELOG.md` under `[Unreleased]`, `### Security` (create the heading if missing), in
  `CONTEXT.md`'s terms: a `SKILL.md` that a git **Source** links outside its **Skill**, or that is not a regular file,
  is no longer read, so a **Source** can neither make skill-graft read a local file nor hang it. Per `AGENTS.md` it
  lands in the archive commit, not an apply commit; check the box there; verify `pre-commit run --all-files`
