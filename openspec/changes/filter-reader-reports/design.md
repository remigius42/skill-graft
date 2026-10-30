# Design

## Context

Checked against `skills/graft-check/` on main (`adf0655`):

- `SKILL.md` step 4 runs each reader as `claude -p … < <prompt file>`, its stdout returned to the main agent: "Its reply
  is the reader's report". "A reply that is not in the report shape" is the main agent's judgement, at the prompt level.
  Step 5 starts more readers, in `uses` mode, the same way, for the uses a **Bind** needs.
- Step 6 gives the patcher "the file and line to change", taken from a report's `file` and `text`.
- `reader.json` asks for `findings: none` and `uses: none` with no blank line between them, and for `use: <name>`
  without saying how a `binds` key in `names`, `<alias>/<name>`, is written.
- The report shape, and the 200-character bound on `text` and `vendored`, are rules of `reader.json`'s prompt only. The
  check spec already says those lines are in printable ASCII; the reader prompt does not.
- Step 6 already holds the patcher to code: stdout and stderr to `mktemp` files, the reply never opened, and on a
  non-zero exit one line, `cat <err-file> <out-file> | LC_ALL=C tr -cd '\040-\176\n' | grep -m 1 . | cut -c 1-200`
  (`bound-check-agents`).
- The skill reaches its shipped files as absolute paths in its own folder (`<reader.json>`, `<patcher.json>`), and is
  installed through skill-graft itself (`skill-graft add skill-graft/graft-check`), so it can be newer or older than the
  installed CLI. `skill-graft` is on `PATH` wherever the skill runs (step 2's build); a `python3` need not be.
- CI runs on Linux and macOS, so a shell filter meets GNU, mawk and BSD tools.

## Goals / Non-Goals

**Goals:**

- Of a reader that exits 0, only a report in the report shape reaches the main agent: at most 100 findings and 200 uses,
  every value one line of printable ASCII, at most 200 characters; of one that fails, one bounded error line. Step 4's
  and step 5's readers alike.
- The filter, not the main agent, decides what is in the report shape.

**Non-Goals:**

- Stopping visible injection inside a quoted value: `text` exists to quote **Upstream** lines, so a 200-character
  instruction still reaches the main agent, shown and never followed, as today.
- The probe: it reads no **Skill** text, its reply must be exactly `reader-ok`, and its failure line is bounded already.
- An unhardened **Check**: the main agent reads **Skill** text in its own session, so filtering a reply guards nothing.
- Checking fix arguments in code: they draw on the config and the tree as well as reports, and stay a step of the skill.

## Decisions

- **A POSIX `sh` script in the skill's folder, `report-filter.sh`.** Run as
  `sh <report-filter.sh> <mode> <skill id> <name>… < <reply file> 2> /dev/null`, `<mode>` `full` or `uses`, its path
  found as `<reader.json>` is, so it needs no exec bit, no interpreter beyond `sh`, `tr` and `awk`, and ships and
  versions with the skill that calls it. `tests/cli/test_check.py` runs it as a subprocess on Linux and macOS.
  Alternatives: a `skill-graft` subcommand, in Python, which could reuse `pipeline/hidden.py`; rejected as a public
  command only the skill calls, and as it splits filter and caller across two installs that can drift. A one-liner in
  `SKILL.md`: rejected, too long to read or test as one line. A `python3` script: rejected, `python3` need not be on
  `PATH`.

- **Bytes mapped by `tr`, shape checked by `awk`.** Before `awk` sees the reply,
  `LC_ALL=C tr -d '\015\200-\277' | LC_ALL=C tr -c '\n -~' '[?*]'` drops every carriage return and every UTF-8
  continuation byte, then turns every byte outside printable ASCII and the line break, a UTF-8 lead byte, a control, a
  tab, a NUL, into `?`. A UTF-8 character becomes one `?`, and every **Hidden character** is gone, as none is ASCII; a
  stray continuation byte is dropped, and so is a carriage return, so a reply with CRLF line ends reads as one with LF.
  `awk` then reads printable ASCII only, so every dialect agrees on what a character is, a cut splits none, and no octal
  escape or NUL reaches it. `[?*]` is POSIX's way to repeat `?`, which GNU and BSD `tr` both read. The spec's printable
  ASCII holds for every value. Each `tr` writes to a `mktemp` file and its exit code is checked before the next step
  runs: POSIX `sh` has no `pipefail`, and a failing `tr` must not look like an empty reply. Alternatives: map bytes in
  `awk` with octal ranges; rejected, as dialects disagree on octal escapes in bracket expressions and on NUL. Drop
  non-ASCII, as the patcher's `tr -cd` does; rejected, as words run together and the user cannot tell. Keep printable
  Unicode minus the **Hidden characters**; rejected, as it needs a Unicode-aware filter, which a portable `awk` is not.

- **Every value bounded.** A `text`, `vendored`, `why` or `file` longer than 200 characters becomes its first 197 and
  `...`. `skill` and `use` must equal an argument, which the main agent took from the lock, the tree or the config.
  `line` matches `^[1-9][0-9]*$` and is at most 6 characters long; `means` is `none` or two names matching
  `^[A-Za-z0-9][A-Za-z0-9._-]*$` around a slash (`config.NAME`, the fix arguments' rule), at most 200 characters in all.
  Neither regex uses an interval `{m,n}`, which mawk 1.3.3 and gawk before 4 read as literal text. A value outside its
  rule fails the reply. `awk` compares every value with an argument or a fixed word as a string: each value is cut from
  its line with `substr`, each argument taken as `"" ARGV[i]`, and names are array keys, never numbers. A value and an
  argument that both look numeric would otherwise compare as numbers, so `use: 01` would pass for `names: 1`.

- **Strict shape, one verdict per reply.** After the mapping, trailing spaces are trimmed from each line; a line is then
  `<key>: <value>`, split at the first colon and space, `<key>:` with an empty value, or blank. Only `text` and
  `vendored` may be empty, as an **Upstream** line can be. A line that is exactly ```` ``` ```` or ```` ```text ```` is
  read as a blank line, as `reader.json` shows its blocks fenced. Blank lines separate blocks; leading, trailing and
  repeated blank lines are allowed. A block is one of:

  - a finding: `skill`, `file`, `text`, `kind`, `why` once each, `vendored` at most once, in any order;
  - a use: `use`, `file`, `line`, `text`, `means` once each, in any order;
  - a `findings: none` or `uses: none` line, a block of its own whether or not a blank line follows it, as `reader.json`
    asks for the two on consecutive lines.

  The blocks come in the order `reader.json` asks for, each verdict once. In `full` mode: `findings: none` or one to 100
  findings, then `uses: none` or one to 200 uses. In `uses` mode: `uses: none` or one to 200 uses, and no finding. A
  finding's `skill` must equal `<skill id>`, `kind` be one of `missed`, `false`, `rewrite`, `link`, `wrong target`; a
  use's `use` one of the `<name>` arguments, written exactly as `names` gives it, `<alias>/<name>` for a `binds` key.
  `reader.json` says so, `use: <one of names, as written there>`, and states both caps. Findings and uses have caps of
  their own, as uses grow with how often a name is written and findings do not: one cap shared would let a long list of
  uses cost a **Skill** its findings. Anything else fails the reply: a verdict missing, repeated or out of order, a
  finding after `findings: none`, a cap passed, a key unknown, missing or repeated, or an empty reply. Alternatives:
  drop the lines that fail; rejected, as a hijacked reader could then choose what survives. One cap of 100 blocks;
  rejected, as above. A cap of 500 blocks; rejected, as it gives a hijacked reader five times the room.

- **Exit codes.** `awk` decides a reply only in a checked `END`: it exits 0 when the reply is in the report shape and 3
  when it is not, and on its own errors exits 1 or 2, depending on the dialect. The script turns 0 into 0 and 3 into 1,
  and every other exit, its own `tr` or `mktemp` failing included, into 2. Exit 0: the script printed the admitted
  blocks, normalized, one blank line between blocks, and the skill shows only that. Exit 1: not in the report shape,
  nothing printed; the skill names the **Skill** as having no report with the fixed reason `not in the report shape`,
  and opens neither file. Any other exit, 2 or `sh` not finding the script (127), is a broken filter, not a reader's
  doing: the **Check** ends, naming the filter and its exit code. Its stderr goes to `/dev/null`, so an `awk` message
  quoting input reaches no one. `awk` prints only in `END`, once the whole reply passed, so a reply refused halfway
  prints nothing.

- **A failed reader's error line, as the patcher's.** stdout and stderr go to `mktemp` files outside its working folder.
  On a non-zero exit the skill shows
  `{ cat <err-file>; echo; cat <out-file>; } | LC_ALL=C tr -cd '\040-\176\n' | grep -m 1 . | cut -c 1-200`, quoted, the
  patcher's step 6 too: the `echo` ends an error output with no final line break, which would otherwise run into the
  first line of `<out-file>`. Measured for the patcher (`bound-check-agents`), a reached cap writes `claude`'s error to
  stdout, not the agent's reply. Should a later `claude` write some of the reply there too, it is one line of printable
  ASCII, at most 200 characters, shown as quoted text: no more than a report's `text` carries.

- **`?` in a fix.** Step 6's patcher prompt, written from a report's `file` and `text`, says that each `?` there may
  stand for one character the filter replaced, so the patcher finds the line by its other characters with `Grep`.

## Risks / Trade-offs

- [A reader slips from the shape: a preamble, a bullet] → that **Skill** has no report, named, and the user can run the
  **Check** on it again. The `injected` eval (`evals/graft-check/`) shows how often, when it is next run.
- [Visible injection in a quoted value] → at most 200 characters of printable ASCII per value, 100 findings and 200 uses
  per reply, shown as quoted text, never followed; `docs/security.md` keeps it a residual risk.
- \[A file name or line with non-ASCII characters reaches the patcher with `?`\] → the patcher reads the **Skill** and
  finds the line itself; a **Patch** it gets wrong is a diff the user reads and declines.
- \[A **Skill** with more than 200 uses of its names\] → it has no report, named; rare, and the user sees which.
- \[A **Skill** whose name holds a non-ASCII character\] → the filter turns it into `?` in the reply, not in the
  arguments, so `skill` and `use` never match: that **Skill** has no report, named. Rare: the Agent Skills specification
  allows only `a-z`, `0-9` and `-` in a name.
- \[A `full` mode reader lists a use under a name spelled otherwise than `names`\] → the reply fails; `reader.json` now
  names the spelling.
