## MODIFIED Requirements

### Requirement: Git source subdirectory

A git source's `subdirectory`, if present, SHALL be a relative path of segments separated by `/`, each matching
`[A-Za-z0-9._-]+`, not only dots, and not `.git` in any case, with no segment `.apm` followed by `skill-graft`. Anything
else, the empty string, a leading or trailing `/`, `//`, a space and a control character included, SHALL be an error
naming `sources.<alias>.subdirectory`, never a crash. Loading SHALL NOT read the repository; the commit read checks the
folder.

#### Scenario: Valid subdirectory

- **WHEN** `[sources.cp]` has `git = "https://github.com/cursor/plugins.git"` and `subdirectory = "pstack/skills"`
- **THEN** the config loads

#### Scenario: Hidden folder

- **WHEN** `[sources.cp]` has `subdirectory = ".claude/skills"`
- **THEN** the config loads

#### Scenario: Subdirectory leaving the repository

- **WHEN** `[sources.cp]` has `subdirectory` set to `"../x"`, `"a/../../x"`, `"/etc"`, `"."`, `"a/./b"`, `""`, `"a//b"`,
  `"a/"`, `"a/.git/b"` or `".GIT"`
- **THEN** the command exits non-zero naming `sources.cp.subdirectory`, and git is never run

#### Scenario: Control character

- **WHEN** `[sources.cp]` has `subdirectory = "a\u0000b"` or `subdirectory = "a\nb"`
- **THEN** the command exits non-zero naming `sources.cp.subdirectory`, without a traceback

#### Scenario: Character outside the name characters

- **WHEN** `[sources.cp]` has `subdirectory` set to `"my skills"`, `"a/$(x)"` or `"é"`
- **THEN** the command exits non-zero naming `sources.cp.subdirectory`, and git is never run

#### Scenario: Subdirectory into a package

- **WHEN** `[sources.cp]` has `subdirectory = "proj/.apm/skill-graft/.apm/skills"`
- **THEN** the command exits non-zero naming `sources.cp.subdirectory`
