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
- `probe-check-readers` (in flight, `feat/opsx-probe-check-readers`) rewrites step 1, adds a probe reader command,
  replaces `${CLAUDE_SKILL_DIR}/reader.json` and `patcher.json` with `<reader.json>` and `<patcher.json>` in both
  commands, adds a `probe` mode to `reader.json`, and will edit `docs/security.md` (its task 3.1).

## Goals / Non-Goals

**Goals:**

- Nothing the patcher writes reaches the main agent unbounded or without the quoted-data rule.
- No reader or patcher can run without end; the **Check** spends at most 4 readers' worth of tokens at a time.

**Non-Goals:**

- A cost cap in dollars (`--max-budget-usd`): turns bound the loop the gap names; a dollar figure means little on a
  subscription and would need its own measurement.
- Enforcing the parallelism cap outside the prompt: the main agent starts readers through its own tool calls, and
  nothing between it and Bash counts them.
- Fixing step 6's `awk` for file names holding spaces (`$NF` takes the last word): an existing defect, reported, not
  in scope.

## Decisions

- **Discard the patcher's reply, not bound it.** The main agent needs nothing from it: the diff, which the user reads,
  says what changed, and the exit code says whether the patcher ran. Redirecting stdout to `/dev/null` in the command
  removes the reply from the main agent's context, which a length bound and a prompt rule would only narrow.
  `patcher.json` then asks for `done` only, so the patcher spends no tokens on a summary nobody reads.
  Alternative: one line per file, each of at most 200 characters, as quoted data (Future work's wording); rejected as
  weaker, and still prompt-level.
- **Bound the file names in `awk`.** They are the one part of the patcher's work the main agent must see before the
  user reads the diff, so they stay, cut in the command itself (`substr(f, 1, 200)`, at most 20 files, then
  `<k> more files`), plus the quoted-data rule. The bound is enforced by the command, not the prompt; the rule is
  prompt-level. Alternative: accept only a diff touching the one file the prompt named; rejected, as a fix may need a
  new file (`patcher.json` allows one) and the user reads the diff anyway.
- **`--max-turns 30` per reader, `10` for the patcher.** A reader globs and reads its **Upstream** folder, its vendored
  copy and each target's **Upstream** folder; tool calls in one turn run together, so 30 covers a **Skill** of a dozen
  files with targets. The patcher reads a file or two and edits; 10 is generous. A capped reader is a **Skill** with no
  report, which step 4 already handles: its exit code or reply fails the report shape. Alternative: one cap for both;
  rejected, as the patcher's work is smaller. The numbers sit in the commands, where the user's permission rules see
  them.
- **`--max-turns` though `--help` omits it.** It is the only turn bound `claude -p` has. Should a later Claude Code drop
  it, every reader and the patcher exit 1 with `unknown option`: each **Skill** has no report, and every **Patch** fix
  ends. Fail-closed, and with `probe-check-readers` in, its probe fails first and the **Check** says it is unhardened,
  naming the error.
- **At most 4 readers at once,** in step 4 and in step 5's `uses` readers alike: start the next when one finishes.
  Four keeps a large **Hull** quick and its spend at any moment small. Prompt-level only, recorded as such.
- **Exit at the cap measured, not assumed.** Whether `claude -p` exits non-zero at `--max-turns` decides only what the
  report says (no report either way), and for the patcher whether the fix ends or the user reads a partial diff, both
  safe. Task 1.1 measures it once on a tiny prompt (billed, a few cents) and records the result here.

### Avoiding conflicts with `probe-check-readers`

- `reader.json` is untouched here; the turn cap is a flag, not prompt text.
- The spec delta modifies three requirements `probe-check-readers` leaves alone ("Skill text is read by hardened
  readers", "The main agent never reads skill text", "Patches are written by a confined patcher"); it modifies "Unhardened
  only on the user's yes" and adds one. The deltas archive in either order.
- In `SKILL.md`, `--max-turns` goes on each command's first line (`claude -p --max-turns 30 --restricted …`), which
  `probe-check-readers` does not change; git still sees adjacent-line edits as one conflict in each command, resolved by
  keeping both. Whichever change lands second rebases onto main and resolves them.
- The probe is a reader "run as every reader runs", so it takes `--max-turns 30` too. The test from task 2.1 asserts
  every `claude -p` command block in `SKILL.md` carries `--max-turns`, so after either rebase it fails until the probe
  command has it.
- `docs/security.md`: this change edits Residual risks, three OWASP rows and Future work; `probe-check-readers` task 3.1
  edits the Claude Code section and the login case. The second to land rebases and merges by hand.

## Risks / Trade-offs

- \[30 turns too few for a large **Skill**\] → that **Skill** has no report, named; the user sees which and can check it
  alone. Raise the cap if the eval or use shows it.
- [The parallelism cap is prompt-level] → a hijacked main agent could ignore it; but no **Skill** text reaches the main
  agent to hijack it, so only a reader's report or a file name could try, and both are quoted data. Recorded in
  Residual risks.
- [File names still reach the main agent] → 20 of at most 200 characters each, quoted; the user reads the diff before
  any **Patch** lands.
- [A hidden flag] → see Decisions: fail-closed.
