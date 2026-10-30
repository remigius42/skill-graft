# Proposal

## Why

The **Check**'s main agent holds a shell and must never hold text that a **Source**'s author wrote. Yet it reads the
lock's `upstream` and `why`'s `upstream:` line, both paths whose folder names that author chose, and pastes them into
Bash (`--add-dir`, `cp -rL`). A folder name can carry a line break that forges an output line, `$(…)` that runs in the
agent's shell, or invisible characters. **Skill** names already meet `[A-Za-z0-9][A-Za-z0-9._-]*`; the folders that lead
to a **Skill** meet nothing.

## What Changes

- Each folder on the path from a **Source**'s folder to a **Skill**, the **Skill**'s own folder included, SHALL match
  `[A-Za-z0-9._-]+`, not only dots: the name characters, a leading dot allowed for folders such as `.claude/`. A
  **Skill** at the **Source**'s folder itself still works. A **Skill** whose path does not match is unusable: an
  **Entry**, `[bind]` target, slash or `Skill(<name>)` **Reference** that needs it fails, naming the path with every
  other byte written in octal, so no shell syntax survives; elsewhere in the **Source** it blocks nothing, as an
  unreadable name does today.
- The error for a name that is no path segment escapes the name and path the same way.
- **BREAKING**: each segment of a git **Source**'s `subdirectory` SHALL match it too; any other value is a config error.
  A **Skill** of a path **Source** under a folder such as `my skills/` becomes unusable.
- So every segment of the lock's `upstream`, and of `why`'s `upstream:` line below the **Source**'s root, matches it.
- graft-check checks the lock before reading it, with one command that prints its version and a count only: a line in a
  form skill-graft would not write ends the **Check**; a version other than 1 keeps today's advice. For a **Skill** at a
  git **Source**'s root, `why`'s `upstream:` line is that root.
- ADR 0007 records that paths below a **Source**'s root are held to the name characters.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `skill-discovery`: new requirements "Skill folders use name characters", "An unusable skill path is an error where
  needed" and "Invalid names are escaped".
- `config`: "Git source subdirectory" requires each segment to match `[A-Za-z0-9._-]+`, not only dots.
- `check`: new requirement "The lock is checked before use".

## Impact

- `src/skill_graft/pipeline/discovery.py`: `index` checks each **Skill**'s path relative to the walked folder.
- `src/skill_graft/pipeline/config.py`: `_relative_folder` requires each segment to match the new segment pattern, its
  error naming it.
- `skills/graft-check/SKILL.md`: step 2 checks the lock's lines before reading it.
- `docs/adr/0007-upstream-text-is-untrusted.md`: one sentence.
- Tests: `tests/pipeline/test_discovery.py`, `tests/pipeline/test_config.py`, `tests/cli/test_check.py`.
- `CHANGELOG.md` at archive: `### Changed` for unusable **Skills** under such folders and the stricter `subdirectory`.
