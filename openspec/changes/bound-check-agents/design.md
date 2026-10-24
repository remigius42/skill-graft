# Design

## Context

Checked against `skills/graft-check/` on main (`0f3c332`):

- `SKILL.md:17-21`: the main agent holds "CLI output, `skill-graft.toml`, the lock, and the readers' reports"; the
  quoted-data rule covers a report's `text` only. Step 6 runs the patcher with its stdout returned to the main agent,
  and `patcher.json` asks for "one line per file you changed: `<path in edited/>: <what changed>`", with no length bound.
  Step 6's `awk` prints each file name of `change.patch` whole, as many as the diff holds; the patcher can `Write` files
  of any name.
- `SKILL.md:110` and `:173`: neither command passes `--max-turns`. `SKILL.md:117`: "Readers may run in parallel", no
  limit; step 5's `uses` readers inherit it.
- Claude Code 2.1.310: `claude --help` does not list `--max-turns`, but `claude -p --max-turns 1` parses (an unknown
  option exits 1 with `unknown option`; `--max-turns 1` gets past option parsing to the `--agents` file check).
  `--max-budget-usd` is listed, for `--print` only.
- `pipeline/config.py:109`: an unknown top-level key is an error, so a `[check]` table needs skill-graft's consent.
  Step 2's throwaway build parses the config before the skill reads any of it.
- `probe-check-readers` (in flight, `feat/opsx-probe-check-readers`) rewrites step 1, adds a probe reader command,
  replaces `${CLAUDE_SKILL_DIR}/reader.json` and `patcher.json` with `<reader.json>` and `<patcher.json>` in both
  commands, adds a `probe` mode to `reader.json`, and will edit `docs/security.md` (its task 3.1).

## Goals / Non-Goals

**Goals:**

- Nothing the patcher writes reaches the main agent unbounded or without the quoted-data rule.
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
  says what changed, and the exit code says whether the patcher ran. Sending stdout and stderr to `/dev/null` in the
  command (`> /dev/null 2>&1`; `claude`'s errors could echo model or file text) removes both from the main agent's
  context, which a length bound and a prompt rule would only narrow.
  `patcher.json` then asks for `done` only, so the patcher spends no tokens on a summary nobody reads.
  Alternative: one line per file, each of at most 200 characters, as quoted data (Future work's wording); rejected as
  weaker, and still prompt-level.
- **Summarize with `git diff --numstat`, bounded in `awk`.** The file names are the one part of the patcher's work the
  main agent must see before the user reads the diff, so they stay: from `<base-dir>`,
  `git -c core.quotePath=true diff --no-index --no-renames --no-textconv --no-ext-diff --numstat base edited`, piped to
  an `awk` that strips the `base/`/`edited/` paths git shows (`/dev/null => edited/<name>` for a new file,
  `base/<name> => /dev/null` for a removed one, `{base => edited}/<name>` otherwise; the new-file form is tested
  first), cuts each name to 200 characters, prints the first 20, then `<k> more files`. Plus the quoted-data rule.
  The bound is enforced by the command, not the prompt; the rule is prompt-level. Alternative: accept only a diff
  touching the one file the prompt named; rejected, as a fix may need a new file (`patcher.json` allows one) and the
  user reads the diff anyway.
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
- **`--max-turns` though `--help` omits it.** It is the only turn bound `claude -p` has. Should a later Claude Code drop
  it, every reader and the patcher exit 1 with `unknown option`: each **Skill** has no report, and every **Patch** fix
  ends. Fail-closed, and with `probe-check-readers` in, its probe fails first and the **Check** says it is unhardened,
  naming the error.
- **At most `readers-at-once` readers at once, 4 by default,** in step 4 and in step 5's `uses` readers alike: start
  the next when one finishes. Four keeps a large **Hull** quick and its spend at any moment small. Prompt-level only,
  recorded as such.
- **Exit at the cap, measured.** On Claude Code 2.1.310, the reader's flags with `--max-turns 1`, asked to glob and
  then read, exit 1 with `Error: Reached max turns (1)` on stdout and nothing on stderr (`--output-format json`:
  `subtype` `error_max_turns`). A capped reader fails the report shape and exits non-zero: no report. A capped
  patcher exits non-zero: the fix ends, its partial edits never diffed. The budget's stop exits 1 the same way.
- **Why `numstat`, not parsing `change.patch`.** Step 6's `awk` took the name from the `diff` line's last word, so
  `foo bar.md` came out empty, and skipped any line starting with three dashes or plus signs and a space, so a
  removed `-- x` went uncounted.
  Reading the patch's headers instead does not work either: GNU diffutils 3.12 quotes a name holding a space or tab
  (`+++ "edited/notes and links.md"`, a tab written `\t`), BSD diff does not, and a binary file gets one
  `Binary files … differ` line and no headers. Measured with git: `--numstat` prints one line per file,
  `<added>\t<removed>\t<path>`, sorted by path, `-` and `-` for a binary file, and with `core.quotePath` a name
  holding a tab, line break or quote C-quoted on that line (`"edited/new\nline"`), so no name can forge a line; a
  space stays as is. The `-c` and `--no-*` flags keep the user's git config from changing that. `git` is already a
  step-6 dependency (`git apply`). `change.patch` stays `diff -ruN`, which `git apply` reads.
- **A binary file ends the fix.** `diff -ruN` writes no hunk for it, so the **Patch** could not carry it, and
  `git apply` would refuse the `Binary files` line. The summary prints `<name>: binary`, and the skill ends that fix,
  naming it.
- **Limit values are checked as written.** The skill reads `skill-graft.toml`'s text, not tomllib's numbers, and TOML
  writes 30 as `0x1E`, `3_0` or `+30` too, which `claude` may read otherwise. So `config.py` reads each `[check]`
  value's source form through `tomlkit` (already a runtime dependency) and accepts `[1-9][0-9]*` for a count and
  `[0-9]+(\.[0-9]+)?` above zero for a budget; `true` and `1e0` fail with the rest. Alternative: a command printing the
  parsed limits; rejected, a new CLI surface for five numbers.

### Avoiding conflicts with `probe-check-readers`

- `reader.json` is untouched here; the caps are flags, not prompt text.
- This change's `check` delta modifies three requirements `probe-check-readers` leaves alone ("Skill text is read by
  hardened readers", "The main agent never reads skill text", "Patches are written by a confined patcher").
  `probe-check-readers` modifies "Unhardened only on the user's yes" and adds "Another harness's readers only on the
  user's yes". This change's `config` delta touches nothing of that change. The deltas archive in either order.
- In `SKILL.md`, the caps go on each command's first line
  (`claude -p --max-turns <reader-turns> --max-budget-usd <reader-budget-usd> --restricted …`), which
  `probe-check-readers` does not change; git still sees adjacent-line edits as one conflict in each command, resolved by
  keeping both. Whichever change lands second rebases onto main and resolves them.
- The probe is a reader "run as every reader runs", so it takes the reader's caps too. The test from task 2.1 asserts
  every `claude -p` command block in `SKILL.md` carries both, so after either rebase it fails until the probe command
  has them. The probe runs at step 1, before step 2's build has checked the config, and reads no **Skill** text: it
  runs with the default caps, never with a value from `skill-graft.toml`, which nothing has checked yet.
- `docs/security.md`: this change adds a Limits section and edits Residual risks, three OWASP rows and Future
  work; `probe-check-readers` task 3.1 edits the Claude Code section and the login case. The second to land rebases
  and merges by hand.

## Risks / Trade-offs

- \[A default too low for a large **Skill**\] → that **Skill** has no report, named; the user raises `reader-turns` or
  `reader-budget-usd` in `[check]` and checks it alone.
- [A user raises a limit far] → their choice, in their own config; injected text cannot reach `skill-graft.toml`
  through a reader, and a **Patch** goes only into `patches/`.
- [The parallelism cap is prompt-level] → a hijacked main agent could ignore it; but no **Skill** text reaches the main
  agent to hijack it, so only a reader's report or a file name could try, and both are quoted data. Recorded in
  Residual risks.
- [File names still reach the main agent] → 20 of at most 200 characters each, escaped and quoted; the user reads the
  diff before any **Patch** lands.
- [The budget is soft] → one turn can pass it by what that turn reads; the turn cap bounds how many such turns run.
  Documented in the Limits section.
- [A hidden flag] → see Decisions: fail-closed.
