# Tasks

Apply with the `tdd` skill: each task red-green-refactor, one commit. The archive commit adds the `CHANGELOG.md` entry
under `[Unreleased]`: the **Check**'s hardened readers and patcher, and both **BREAKING** failures (**Hidden
characters**, Markdown that is not UTF-8).

## 1. Spike: are headless readers confined?

- [x] 1.1 Run the reader command from `design.md` (`--add-dir <skill>` only) from an empty folder on a synthetic
  **Skill** whose `SKILL.md` tells its reader to run `curl`, write a marker file, and read a file outside `<skill>`;
  verify with `--output-format stream-json` that the session's tool list holds only `Read`, `Grep` and `Glob`, that the
  marker file does not exist and the outside file's content is not in the output, and that auth works under
  `--restricted`. Also check that `CLAUDECODE` is set in Claude Code's Bash and whether `${CLAUDE_SKILL_DIR}` expands in
  a `SKILL.md`. Record the findings in `design.md`'s Context and settle its open question; if the reader is not
  confined, stop the change and report back

## 2. Hidden characters

- [ ] 2.1 Add `pipeline/hidden.py` test-first in `tests/pipeline/test_hidden.py`: each critical class found with file,
  line, code point and class, in text and in file and folder names; the warning set, APM's ranges with U+2061 and U+FE00
  to U+FE0E, counted once per file with its first line; Markdown that is not strictly UTF-8 reported; other files read
  by the spec's order (UTF-32 marks before UTF-16, strict UTF-8 with NULs, lenient UTF-8 without, else binary skipped),
  a NUL byte not switching the scan off; `.git` left out as vendoring leaves it out; verify the tests pass and
  `lint-imports` stays green
- [ ] 2.2 Scan each **Skill** in `hull.walk`: its **Upstream** folder, the `+` lines of its patch files, and in the
  patched copy the names the **Upstream** lacks and the files a binary hunk writes; collected, with Markdown that is not
  UTF-8, alongside patch failures into one error raised after the walk, each list under its own header, unused-key
  warnings left out; the not-UTF-8 warning in `references.scan` gone; carry the hidden list through `update._fetch_hint`
  and name it in `update._previous`; tests in `tests/pipeline/test_hull.py` for two **Skills** in one run, with Latin-1
  Markdown, with a failing **Patch**, a **Patch** that adds one, moves one, removes one, creates a name holding one, and
  writes one through a binary hunk, and a **Skill** outside the **Hull**, and in `tests/commands/` for
  `update --dry-run` keeping the hidden list; verify they pass, the old not-UTF-8 warning test rewritten to the error
- [ ] 2.3 Let `why` and `tree` print the **Hull** as walked when only **Hidden characters** or Markdown that is not
  UTF-8 failed, then report them and exit 1; end-to-end tests in `tests/cli/` for the hidden-characters spec:
  `resolve`'s message and exit code, the warning, `build --into` leaving its folder empty, `update` keeping the `ref`,
  `add` keeping `skill-graft.toml`, `remove` of the **Skill** holding one succeeding, `why` printing its path before
  failing; verify they pass
- [ ] 2.4 Describe the scan in `docs/design.md` (where the walk runs it, APM's table it copies, why **Upstream** too);
  verify `pre-commit run --all-files`

## 3. The skill

- [ ] 3.1 Add `skills/graft-check/reader.json` and `patcher.json`, the agent definitions: the reader's prompt holds the
  Kinds section moved from `SKILL.md`, the report shape with `text` one line of at most 200 characters, and every use of
  each given name with its verdict; the patcher's prompt edits only `edited/` and keeps `name:`. Extend
  `tests/cli/test_check.py`: the reader names only `Read`, `Grep`, `Glob`, the patcher only `Read`, `Edit`, `Write`, and
  the skill still resolves alone with no warning; verify the tests pass
- [ ] 3.2 Rewrite `skills/graft-check/SKILL.md` by `mp-writing-for-agents`: detecting Claude Code from `claude --help`'s
  flags and asking before an unhardened **Check**; one reader per **Skill** by the command in `design.md`, with a copy
  of its own patch files and its targets' **Upstream** folders, the main agent never opening **Skill** text; wrong
  targets judged by the readers, **Bind** scope by use-only readers over every **Hull** **Skill** of the **Source**,
  whatever the scope, run where no use list for the name exists; fix arguments checked against skill-graft's name
  pattern and quoted; the patcher with `edited/` only, `base/` out of its reach, the diff's counts and path, and the
  user's review before the **Patch** enters the **Package**; the unhardened path keeping today's flow. Verify
  `tests/cli/test_check.py` and `pre-commit run --all-files`
- [ ] 3.3 Add eval scenarios to `evals/graft-check/`: `injected` (a **Hull** **Skill** telling the reader to write a
  marker file outside its folders: the marker is absent and the other findings are reported) and `unhardened` (a
  `claude` wrapper on `PATH` whose `--help` lacks `--restricted`: the skill asks and, on no, reads nothing); update its
  README. Verify `bash -n` and shellcheck in pre-commit; run the eval only on the user's go, and record the result
- [ ] 3.4 Ignore the deployed `.claude/skills/graft-check/` in `.gitignore` beside `mp-*` and `hl-*`; verify
  `git status` no longer lists it

## 4. Security docs

- [ ] 4.1 Write `docs/security.md`: the threat, what APM's install blocks, the **Hidden character** check, what the
  **Check** enforces on Claude Code and how, the residual risks (report text, fix arguments, BOM-less UTF-16 skipped as
  binary), that other harnesses are likely not secure, and running the **Check** outside auto mode, with a `WebFetch`
  deny rule where wanted, and in Claude Code's sandbox only with the API's domain allowed and `~/.claude` writable, as
  the readers are `claude` processes: try that sandbox setup on a synthetic **Package** and write down what it needs.
  Add a `## Security` section to `README.md` after "Checking a package" with the three points and the link, and update
  "Checking a package" for the readers and the patcher's review; verify `pre-commit run --all-files`
