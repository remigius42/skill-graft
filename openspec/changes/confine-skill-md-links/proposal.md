# Proposal

## Why

Discovery reads the `SKILL.md` of every **Skill** in every **Source** to learn its name, before the symlink check of
`build` runs, and that check covers only **Hull** **Skills**. A git **Source** that commits `SKILL.md` as a symlink to a
file outside its tree makes skill-graft read that local file: a front-matter `name:` line in it is printed in an error.
A `SKILL.md` that is, or links to, a device or FIFO (`/dev/zero`, `/dev/stdin`) stalls every command that reads the
**Sources**, used by an **Entry** or not; a path **Source** can be a third-party clone too.

## What Changes

- In a git **Source**, discovery never opens a `SKILL.md` symlink that resolves outside its **Skill**'s folder. Its name
  is unreadable: an **Entry** or **Reference** naming its folder fails naming the link, not what it leads to; other
  **Entries** never see it.
- In every **Source**, discovery never opens a `SKILL.md` that is not a regular file once links are followed; its name
  is unreadable likewise.
- A `SKILL.md` symlink to a file inside its **Skill** keeps working, as `build` vendors it; path **Sources** may still
  link `SKILL.md` anywhere to a regular file.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `git-sources`: "The checkout is the upstream tree" adds that discovery opens no `SKILL.md` symlink leading out of its
  **Skill**.
- `skill-discovery`: a new requirement that a `SKILL.md` must be a regular file to be opened.

## Impact

- `src/skill_graft/pipeline/discovery.py`: a check before `read_name` in `index`.
- Tests in `tests/pipeline/test_discovery.py`, end-to-end ones in `tests/cli/test_git_build.py` and
  `tests/cli/test_build.py`.
- `CHANGELOG.md` entry at archive: a security fix users see.
