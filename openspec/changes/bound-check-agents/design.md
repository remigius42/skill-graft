# Design

## Context

Checked against `skills/graft-check/` on main (`8c0bad8`, `probe-check-readers` archived):

- `SKILL.md:17-21`: the main agent holds "CLI output, `skill-graft.toml`, the lock, and the readers' reports"; the
  quoted-data rule covers a report's `text` only. Step 6 runs the patcher with its stdout returned to the main agent,
  and `patcher.json` asks for "one line per file you changed: `<path in edited/>: <what changed>`", with no length
  bound. Step 6's `awk` prints each file name of `change.patch` whole, as many as the diff holds; the patcher can
  `Write` files of any name.
- `SKILL.md:61`, `:131` and `:194`: neither the probe, the reader nor the patcher command passes `--max-turns`.
  `SKILL.md:138`: "Readers may run in parallel", no limit; step 5's `uses` readers inherit it.
- Claude Code 2.1.310: `claude --help` does not list `--max-turns`, but `claude -p --max-turns 1` parses (an unknown
  option exits 1 with `unknown option`; `--max-turns 1` gets past option parsing to the `--agents` file check).
  `--max-budget-usd` is listed, for `--print` only.
- `pipeline/config.py:109`: an unknown top-level key is an error, so a `[check]` table needs skill-graft's consent.
  Step 2's throwaway build parses the config before the skill reads any of it.
- `probe-check-readers`, now on main: step 1 runs a probe, a reader run as every reader runs, in an empty folder with
  `mode: probe`, before step 2's build; the commands name `<reader.json>` and `<patcher.json>`.

## Goals / Non-Goals

**Goals:**

- Of the patcher's work, only numbers and one bounded, quoted error line reach the main agent.
- No reader or patcher can run without end. Each one's spend is capped, softly: a run stops after the turn that passes
  its budget, so one turn of many parallel reads can overshoot it; turns bound how often. By default the **Check** has
  at most 4 readers in flight.
- Every limit documented, with its default, and settable per **Package**.

**Non-Goals:**

- Limits per **Source** or per **Skill**: one set per **Package** covers a large **Hull** by raising it; finer grain
  can come when someone needs it.
- Limits for an unhardened **Check**: its reading happens in the session itself, which no flag bounds.
- Enforcing the parallelism cap outside the prompt: the main agent starts readers through its own tool calls, and
  nothing between it and Bash counts them.

## Decisions

- **Discard the patcher's reply, not bound it.** The main agent needs nothing from it: the diff, which the user reads,
  says what changed, and the exit code says whether the patcher ran. Sending stdout to `/dev/null` in the command
  removes the reply from the main agent's context, which a length bound and a prompt rule would only narrow.
  `patcher.json` then asks for `done` only, so the patcher spends no tokens on a summary nobody reads.
  Alternative: one line per file, each of at most 200 characters, as quoted data (Future work's wording); rejected as
  weaker, and still prompt-level.
- **Keep one line of the patcher's errors.** stderr goes to `<base-dir>/patcher.err`; on a non-zero exit the skill
  shows its first line, cut to 200 characters (`head -n 1 patcher.err | cut -c 1-200`), as quoted text, so the user
  can tell a misconfigured `claude` (an unknown option, no login) from a cap reached, and the fix ends. Measured: a
  reached turn cap writes `Error: Reached max turns (1)` to stdout, not stderr, so then the line is empty and the exit
  code alone says it. Alternative: stderr to `/dev/null` too; rejected, as it hides why every **Patch** fix fails.
- **The summary is numbers only, counted from `change.patch`.** No file name the patcher chose reaches the main agent:
  nothing to bound, escape or quote. The user reads the names in the diff, the only place they matter. One `awk` over
  `change.patch` prints `files: <n>, lines: +<added> -<removed>, binary: <n>`. It reads structure, not names: in
  `diff -ruN` output every hunk line starts with a space, `+`, `-`, `@` or `\`, so a line starting with `diff` and a
  space in column 0 begins a file, its next two lines are the `---` and `+++` headers, skipped by position, and a line
  starting with `Binary files` and a space is a binary file. A removed `-- x` or an added `++ x` is counted, and a name
  with spaces or quotes, however diff writes it, is never read. Counting from the patch itself keeps the summary and the
  stored **Patch** in agreement: a file `diff -ruN` leaves out, such as an empty new one, is in neither. Alternatives:
  per-file lines with names bounded and quoted; rejected after trying `git diff --no-index --numstat`, which disagrees
  with `diff -ruN` on empty files and on how far into a file a NUL makes it binary, follows the user's `diff.orderFile`
  and global attributes, and C-quotes names in forms a 200-character cut can split. Parsing names from `change.patch`
  instead: GNU diffutils 3.12 quotes a name with a space or tab, BSD diff does not.
- **A binary file ends the fix.** `diff -ruN` writes one `Binary files … differ` line and no hunk for it, so the
  **Patch** could not carry it and `git apply` would refuse the line. A summary counting one ends that fix.
- **Defaults: 30 turns per reader, 10 for the patcher.** A reader globs and reads its **Upstream** folder, its vendored
  copy and each target's **Upstream** folder; tool calls in one turn run together, so 30 covers a **Skill** of a dozen
  files with targets. The patcher reads a file or two and edits; 10 is generous. A capped reader is a **Skill** with no
  report, which step 4 already handles: its exit code or reply fails the report shape. Alternative: one cap for both;
  rejected, as the patcher's work is smaller.
- **And a budget: 1 USD per reader, 0.50 USD for the patcher.** Turns miss a run of few turns that each read huge
  files; `--max-budget-usd` bounds that. One minimal reader turn cost 0.014 USD on Opus 5.5, and `evals/graft-check/`
  puts a typical reader near 0.06 USD on an earlier model, so 1 USD stops only a runaway. Measured on 2.1.310: a
  budget of 0.001 USD stopped after the turn that passed it, at 0.0048 USD, exit 1, `subtype`
  `error_max_budget_usd`. So a run can pass its budget by one turn, and the cost is at list price
  (`costBasis: list`) on a subscription too: a bound on tokens, not on a bill.
- **The limits live in `[check]` in `skill-graft.toml`.** The skill already holds that file, and skill-graft parses it
  at step 2's build, so a value the skill reads is a plain decimal skill-graft has checked (see below), not text it
  must judge. `config.py` checks the five keys and their values and keeps nothing: no command of skill-graft uses
  them. The skill writes each command with `<reader-turns>` and the like, filled from `[check]` or the default it
  names. Alternatives: environment variables (no check but the prompt's, invisible in the **Package**); arguments to
  `/graft-check` (mixed with the **Skill IDs**, and set again at every run). Backward compatibility is not a concern:
  an older skill-graft refusing `[check]` only affects someone who set it.
- **Limit values are checked as written.** The skill reads `skill-graft.toml`'s text, not tomllib's numbers, and TOML
  writes 30 as `0x1E`, `3_0` or `+30` too, which `claude` may read otherwise. So `config.py` reads each `[check]`
  value's source form through `tomlkit` (already a runtime dependency; `table.item(key).as_string()`, which gives
  `'0x1E'` and `'true'` as written) and accepts `[1-9][0-9]*` for a count and `[0-9]+(\.[0-9]+)?` above zero for a
  budget; `true` and `1e0` fail with the rest. Alternative: a command printing the parsed limits; rejected, a new CLI
  surface for five numbers.
- **`--max-turns` though `--help` omits it.** It is the only turn bound `claude -p` has. Should a later Claude Code drop
  it, every reader and the patcher exit 1 with `unknown option`: each **Skill** has no report, and every **Patch** fix
  ends, its error line naming the option. Fail-closed: the probe, which carries the flag too, fails first and the
  **Check** says it is unhardened, naming the error.
- **At most `readers-at-once` readers at once, 4 by default,** in step 4 and in step 5's `uses` readers alike: start
  the next when one finishes. Four keeps a large **Hull** quick and its spend at any moment small. Prompt-level only,
  recorded as such.
- **Exit at the cap, measured.** On Claude Code 2.1.310, the reader's flags with `--max-turns 1`, asked to glob and
  then read, exit 1 with `Error: Reached max turns (1)` on stdout and nothing on stderr (`--output-format json`:
  `subtype` `error_max_turns`). A capped reader fails the report shape and exits non-zero: no report. A capped
  patcher exits non-zero: the fix ends, its partial edits never diffed. The budget's stop exits 1 the same way.

### The probe

- `reader.json` is untouched here; the caps are flags, not prompt text.
- The probe is a reader "run as every reader runs", so it carries both caps, written as their defaults
  (`--max-turns 30 --max-budget-usd 1.0`). It runs at step 1, before step 2's build has checked the config, so it
  never takes a value from `skill-graft.toml`, which nothing has checked yet. It reads nothing and replies one word,
  about 0.01 USD, so a lower `[check]` budget it ignores costs the user nothing they would notice. The test from task
  3.1 asserts every `claude -p` command block in `SKILL.md` carries both caps.
- The `check` delta modifies three requirements `probe-check-readers` left as they were ("Skill text is read by
  hardened readers", "The main agent never reads skill text", "Patches are written by a confined patcher"); their main
  text is unchanged since this change was proposed.

## Risks / Trade-offs

- \[A default too low for a large **Skill**\] → that **Skill** has no report, named; the user raises `reader-turns` or
  `reader-budget-usd` in `[check]` and checks it alone.
- [A user raises a limit far] → their choice, in their own config; injected text cannot reach `skill-graft.toml`
  through a reader, and a **Patch** goes only into `patches/`.
- [The parallelism cap is prompt-level] → a hijacked main agent could ignore it; but no **Skill** text reaches the main
  agent to hijack it, so only a reader's report or the patcher's error line could try, and both are quoted data.
  Recorded in Residual risks.
- [No file names before the user opens the diff] → the user reads `change.patch` in full before accepting anyway; the
  summary only says how big it is.
- \[A NUL past the part of a file `diff` inspects\] → `diff -ruN` writes a text hunk holding it, and the summary counts
  no binary file. The user reads the diff; a **Patch** `git apply` refuses fails the next build, which undoes it.
- \[The patcher's error line is quoted data from `claude`\] → one line of at most 200 characters, shown, never followed.
- [The budget is soft] → one turn can pass it by what that turn reads; the turn cap bounds how many such turns run.
  Documented in the Limits section.
- [A hidden flag] → see Decisions: fail-closed.
