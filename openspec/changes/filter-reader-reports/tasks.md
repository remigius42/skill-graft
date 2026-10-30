# Tasks

Apply with the `mp-tdd` skill: each task red-green-refactor, one commit. The filter is tested by running
`sh skills/graft-check/report-filter.sh` as a subprocess in `tests/cli/test_check.py`, on Linux and macOS CI; the eval
(`evals/graft-check/`) is billed and runs only when the user asks. Each task updates the parts of `docs/security.md` and
`README.md` its own work changes, so they stay true at every commit.

## 1. The report filter

- [x] 1.1 Admit the report shape: test that, run as `sh report-filter.sh <mode> <skill id> <name>…`, a finding about the
  given **Skill**, with and without `vendored`, a use of a given name, one under a bind key `mp/grill` ("A use under a
  bind key"), `findings: none` then `uses: none` on consecutive lines ("Nothing to report"), 25 findings then 200 uses
  ("Many uses"), and CRLF line ends, trailing spaces and an empty `text:` ("Line ends and trailing spaces") are printed
  back, one blank line between blocks, keys in any order, leading, trailing and repeated blank lines and lines of
  exactly ```` ``` ```` or ```` ```text ```` allowed, exit 0 ("Well-formed report"); add
  `skills/graft-check/report-filter.sh` (POSIX `sh`; `tr` into `mktemp` files, each exit checked; `LC_ALL=C awk`
  deciding in `END`, values compared as strings, no interval regex); verify the test fails first, then passes,
  `test_alone_in_its_hull` still passes with the new file, and `pre-commit run --all-files`
- [ ] 1.2 Refuse every other reply: test that each of these prints nothing and exits 1: an extra line of prose
  ("Injected line"), a finding about another **Skill** ("Finding about another skill"), a use of a name not given ("Use
  of a name not asked about"), a finding or `findings: none` in `uses` mode ("A finding in uses mode"), `kind: approved`
  ("Unknown kind"), `line: 0`, `line: 3a` and `line: 1234567`, a `means` that is neither `none` nor a **Skill ID**, one
  of 300 characters ("Unbounded means"), 101 findings or 201 uses ("Too many blocks") while 100 and 200 pass,
  `findings: none` then a finding ("Contradicting verdicts"), uses before findings, a verdict missing or repeated,
  `use: 01` given `names: 1`, an empty `kind`, a key unknown, missing or repeated, `findings: none` inside a block, and
  an empty reply; test that an `awk` refusing its program, or a failing `tr` (a stub on `PATH` that exits 1), makes the
  script exit 2, never 1; verify the test fails first, then passes, and `pre-commit run --all-files`
- [ ] 1.3 Quoted values in printable ASCII, bounded: test that in `text`, `vendored`, `why` and `file` each UTF-8
  character outside ASCII becomes one `?` ("Non-ASCII text": an em dash and a bidi override), a tab, an escape and a NUL
  each become `?`, a stray continuation byte is dropped, a 300-character value becomes its first 197 and `...` ("Long
  text"), and a value of exactly 200 is kept whole; verify the test fails first, then passes, and
  `pre-commit run --all-files`

## 2. The skill

- [ ] 2.1 Readers through the filter: test that `SKILL.md` step 4's reader command and step 5's `uses` readers send
  stdout and stderr to `mktemp` files outside the working folder, that on exit 0 the skill runs
  `sh <report-filter.sh> <mode> <skill id> <name>… < <out-file> 2> /dev/null` and holds only what it prints, that its
  exit 1 names the **Skill** as having no report with `not in the report shape`, that any other exit ends the **Check**
  naming the filter and its exit code ("A broken filter"), that `<report-filter.sh>` is named with `<reader.json>` as a
  file of this skill's folder, and that the quarantine paragraph says the main agent never opens a reader's output but
  the probe's; update those parts of `SKILL.md`; test that `reader.json` asks for `use:` as `names` writes it and states
  the caps of 100 findings and 200 uses, and update it; in `docs/security.md` the main-agent bullet, Residual risks'
  "Report text" (held to its shape and bound in code, 100 findings and 200 uses of values of at most 200 characters; a
  short visible injection still reaches the main agent) and the LLM05 row; in `README.md`'s Security section, that a
  reader's reply reaches the main agent only as the filter admits it; verify the test fails first, then passes, and
  `pre-commit run --all-files`
- [ ] 2.2 A failed reader shows why: test that on a non-zero exit steps 4 and 5 show the patcher's error-line pipeline
  on the reader's `<err-file>` and `<out-file>`, and that the pipeline turns `Error: Reached max turns (30)` on stdout,
  with stderr empty, into that line ("Reader reaches its turn cap"); update steps 4 and 5 and `docs/security.md`'s
  main-agent bullet; verify the test fails first, then passes, and `pre-commit run --all-files`
- [ ] 2.3 `?` in a fix: test that step 6's patcher prompt says a `?` in a report's `file` or `text` may stand for one
  character the filter replaced; update step 6; verify the test fails first, then passes, and
  `pre-commit run --all-files`

## 3. Integration

- [ ] 3.1 Check every scenario of the `check` delta spec against a test or a `SKILL.md` step, bring `proposal.md`,
  `design.md` and `tasks.md` in line with the code (names, signatures, moved tests), and run
  `openspec validate filter-reader-reports --strict`, `uv run pytest` and `pre-commit run --all-files`
