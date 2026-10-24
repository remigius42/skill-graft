# Security

Skills come from other people's repositories and are written to steer agents, so their text can carry prompt
injection, some of it invisible. This page says what stops it, where, and what does not (ADR 0007).

## The threat

A **Skill**'s text reaches an agent twice: when a harness loads the deployed skill, and when the **Check** reads it on
purpose. The **Check** runs in an agent with a shell, file writes and network, often in a mode that asks no one before
a command. A hijacked **Check** could send files away, or write a **Patch** that the next `build` deploys.

## What APM's install blocks

APM 0.33.0 refuses to install a skill holding a critical **Hidden character**: Unicode tag characters, bidi
embeddings, overrides and isolates, and supplementary variation selectors (`apm_cli/security/content_scanner.py`). It
warns on invisible characters common as copy-paste debris. `build` runs APM; `build --into`, which the **Check** uses,
never does.

## The hidden character check

skill-graft fails resolution on the same critical characters, wherever a **Hull** **Skill** holds one: in its
**Upstream** text, a file or folder name, or the lines its **Patches** add, naming each file, line and character
class. A Markdown file that is not UTF-8 fails too, as its **References** could not be read. `resolve`, `build`
(`--into` too), `update` and the commands that edit the config write nothing; `why` and `tree` print the **Hull** as
walked, then fail. Debris only warns. So no **Hidden character** reaches any agent through the **Hull**, in any
harness.

The check sees text, not intent: visible prompt injection passes it.

## What the Check enforces with Claude Code

Wherever a working Claude Code is installed, in any harness, the **Check** reads **Skill** text only through confined,
headless agents, checked on Claude Code 2.1.309:

- **Readers.** Each checked **Skill** gets its own `claude -p --restricted --strict-mcp-config`, with the tools `Read`,
  `Grep` and `Glob` only and no MCP server, run from a new empty folder holding a copy of that **Skill**'s own patch
  files, its other folders granted with `--add-dir`: its **Upstream** folder, its vendored copy, its targets'
  **Upstream** folders. `--restricted` confines the file tools to those folders and drops every tool that runs code,
  and ignores the user's settings, so none can widen it. The reader definition ships with the skill
  (`skills/graft-check/reader.json`).
- **The main agent** never opens a **Skill**'s **Upstream** text, vendored copy or patch files. It holds CLI output,
  `skill-graft.toml`, the lock, the patcher's reply, the names of the files it changed, and the readers' reports,
  whose quoted `text`, one line of at most 200 characters, it shows and never acts on.
- **The patcher** writes a **Patch** with `Read`, `Edit` and `Write` only, confined to a temporary folder holding a
  working copy, out of reach of the base it is diffed against. You read the diff before it goes into the **Package**.
- **Fix arguments** must come from CLI output, the config or a report's names, each side of the slash a name
  skill-graft accepts, quoted. A finding whose fix fails this is reported without one.

Before any **Skill** text is read, one probe, a reader run as every reader runs from a new empty folder, must answer
`reader-ok`. Checked on Claude Code 2.1.310, it fails on a `claude` without those flags, without a login, or on a
lapsed account, before any reader starts. Outside Claude Code the skill first says the readers and the patcher run on
your Claude Code account, and probes only on your yes. With no `claude` on `PATH`, your account declined, or a failed
probe, it says the **Check** is unhardened and why, naming the probe's error, and reads in its own session only on
your yes. Tried by hand in OpenCode 1.3.0 on DeepSeek V4.1 Flash: the main agent asked, the probe passed, and each
**Skill** had its own reader.

## Limits

A hardened **Check** caps what its readers and patcher can spend. Set a limit under `[check]` in the **Package**'s
`skill-graft.toml`, in plain decimal digits; skill-graft refuses any other form. The probe always runs with the
readers' defaults, since it runs before skill-graft has checked the config.

| Key                  | Default | Reaching it                                                     |
| -------------------- | ------- | --------------------------------------------------------------- |
| `reader-turns`       | 30      | The reader stops; its **Skill** is named as having no report.   |
| `reader-budget-usd`  | 1.0     | The reader stops; its **Skill** is named as having no report.   |
| `patcher-turns`      | 10      | The patcher stops and that fix ends, with no **Patch** written. |
| `patcher-budget-usd` | 0.5     | The patcher stops and that fix ends, with no **Patch** written. |
| `readers-at-once`    | 4       | The next batch of readers starts once a batch has ended.        |

Turns are capped with `claude -p --max-turns`, spend with `--max-budget-usd`. A budget is checked after each turn, so
a run can pass it by what its last turn cost: measured on Claude Code 2.1.310, a 0.001 USD budget stopped at 0.0048
USD. The spend is counted at list price, on a subscription too, so there it bounds tokens, not your bill. A capped
reader or patcher exits non-zero, which the skill already takes as a failure. `readers-at-once` is a step of the
skill: the main agent starts each reader, and nothing between it and its shell counts them.

## Residual risks

- **Report text.** A reader's quoted `text` reaches the main agent. It is short and shown, never followed, and you
  accept each fix; this holds at the prompt level only.
- **Patcher reply.** The patcher's reply and the names of the files it changed reach the main agent too, the reply
  with no bound on its length; nothing tells the main agent to treat either as quoted data.
- **Fix arguments** are checked by the main agent, at the prompt level too.
- **Readers at once.** How many readers run at once is up to the main agent following the skill, at the prompt level
  too; each reader's own turns and spend are capped by `claude` itself.
- **A file skipped as binary.** A file other than Markdown that holds a NUL byte and is not UTF-8, such as UTF-16 text
  without a byte order mark, is skipped. No Markdown file can be.
- **Visible injection.** Readers are confined, not trusted: one can still misreport what a **Skill** says.
- **Another harness's model.** The probe and the main agent's quarantine are steps in the skill's text, which the
  harness's model may skip. In OpenCode 1.3.0, Big Pickle asked about the account, then skipped the probe and opened
  **Skill** text itself; its readers still ran confined.
- **A later Claude Code** could change what `--restricted` confines. The `injected` eval scenario
  (`evals/graft-check/`) catches that when the skill changes. It could also drop `--max-turns`, which `claude --help`
  does not list on 2.1.310: the probe then fails with `unknown option`, and the **Check** says it is unhardened.
- **Approval.** A **Patch** diff or fix written to look harmless can still win your yes; every approval rests on
  your reading.
- **Deployed Skills.** skill-graft does not judge whether a **Skill** is malicious, and no tool reliably can: past
  the **Hidden character** check, visible injection and the scripts a **Skill** ships reach your agent as written.
  Vet the **Sources** you declare.

An unhardened **Check** is likely not secure: it reads **Skill** text in the session that holds your shell.

## Running the Check

- Outside auto mode, or any mode that runs commands without asking, so you see each command the main agent runs.

- With a deny rule for `WebFetch` where you want the main agent kept off the network:
  `"permissions": {"deny": ["WebFetch"]}` in your settings.

- In Claude Code's sandbox, with the API's domain allowed: each reader and the patcher is a `claude` process the
  main agent starts through sandboxed Bash, and calls the API. Tried on Claude Code 2.1.309 on Linux, where the
  sandbox needs `bubblewrap` and `socat`, a reader ran with these settings; the only other connection, to Datadog's
  telemetry intake, was refused without harm:

  ```json
  {
    "sandbox": {
      "enabled": true,
      "failIfUnavailable": true,
      "allowUnsandboxedCommands": false,
      "network": { "allowedDomains": ["api.anthropic.com"] }
    }
  }
  ```

  `failIfUnavailable` makes Claude Code refuse to start without the sandbox rather than run commands unsandboxed.

- With a login the readers can find: Claude Code's Bash does not pass `CLAUDE_CODE_OAUTH_TOKEN` on, so a reader
  started from a session authenticated by that variable alone reports "Not logged in". The probe catches it before
  any reader starts and advises `claude auth login`, whose stored login works.

## OWASP Top 10

How skill-graft meets each risk of the [OWASP Top 10 for LLM Applications 2025](https://genai.owasp.org/llm-top-10/)
and the [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/).
Readers and the patcher are confined only when the **Check** runs hardened, wherever a working Claude Code is
installed; elsewhere it reads **Skill** text in the session that holds your shell.

### LLM Applications 2025

| Risk                                                                                                                  | Here                                                                                                                                                                                                                                                                                                             |
| --------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [LLM01 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)                                     | Into the **Check**: the **Hidden character** check, then confined readers. Into a deployed **Skill**: hidden characters only (Residual risks).                                                                                                                                                                   |
| [LLM02 Sensitive Information Disclosure](https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/) | Hardened, readers see only the folders of the **Skill** they check and its targets. Unhardened, the main agent reads **Skill** text in the session that holds your files.                                                                                                                                        |
| [LLM03 Supply Chain](https://genai.owasp.org/llmrisk/llm032025-supply-chain/)                                         | A git **Source** may be pinned to a commit; a path **Source** never is. The lock records a hash per vendored **Skill** but nothing verifies it. Hardened, you read every **Patch** diff; unhardened, the main agent writes it into the **Package** without showing it. Trusting a **Source** is yours to decide. |
| [LLM04 Data and Model Poisoning](https://genai.owasp.org/llmrisk/llm042025-data-and-model-poisoning/)                 | Not applicable: skill-graft trains nothing. A poisoned **Skill** is LLM01.                                                                                                                                                                                                                                       |
| [LLM05 Improper Output Handling](https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/)                 | A reader's quoted `text` is one line of at most 200 characters, shown, never acted on; fix arguments must come from CLI output, the config or a report's names, each a name skill-graft accepts. The patcher's reply is unbounded (Residual risks).                                                              |
| [LLM06 Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/)                                 | Readers hold `Read`, `Grep` and `Glob` under `--restricted`, no MCP server; the patcher holds `Read`, `Edit` and `Write` in a temporary folder.                                                                                                                                                                  |
| [LLM07 System Prompt Leakage](https://genai.owasp.org/llmrisk/llm072025-system-prompt-leakage/)                       | Not applicable: the reader and patcher prompts are public (`skills/graft-check/reader.json`, `patcher.json`) and hold no secret.                                                                                                                                                                                 |
| [LLM08 Vector and Embedding Weaknesses](https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/)   | Not applicable: no embeddings or retrieval.                                                                                                                                                                                                                                                                      |
| [LLM09 Misinformation](https://genai.owasp.org/llmrisk/llm092025-misinformation/)                                     | A reader can misreport a **Skill** (Residual risks); you accept each fix.                                                                                                                                                                                                                                        |
| [LLM10 Unbounded Consumption](https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/)                       | Each reader and the patcher stop at a cap on their turns and their spend, and at most 4 readers run at once by default, the last at the prompt level only (Limits).                                                                                                                                              |

### Agentic Applications 2026

The agentic list has no page per risk; its entries are in the PDF on OWASP's page linked above.

| Risk                                       | Here                                                                                                                                                                                                                                                               |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| ASI01 Agent Goal Hijack                    | As LLM01.                                                                                                                                                                                                                                                          |
| ASI02 Tool Misuse                          | As LLM06. The main agent holds a full shell; outside auto mode, you see each command it runs.                                                                                                                                                                      |
| ASI03 Identity & Privilege Abuse           | Readers and the patcher use your Claude login but hold no shell. The sandbox settings under Running the Check, if you apply them, keep the main agent's commands off the network but the API, which can itself carry data out; `WebFetch` needs its own deny rule. |
| ASI04 Agentic Supply Chain Vulnerabilities | As LLM03; readers and the patcher load no MCP server (`--strict-mcp-config`).                                                                                                                                                                                      |
| ASI05 Unexpected Code Execution            | No reader or patcher can run code. Scripts a deployed **Skill** ships: Residual risks.                                                                                                                                                                             |
| ASI06 Memory & Context Poisoning           | A hijacked **Check** could write a **Patch** the next `build` deploys; hardened, you read each diff first. skill-graft keeps no agent memory.                                                                                                                      |
| ASI07 Insecure Inter-Agent Communication   | Readers reach the main agent only through their reports (LLM05); the patcher through its reply and the names of the files it changed (Residual risks).                                                                                                             |
| ASI08 Cascading Failures                   | Each checked **Skill** gets its own reader, but a reader also reads its targets' **Upstream** text, so one injected **Skill** can mislead the readers of every **Skill** that references it.                                                                       |
| ASI09 Human-Agent Trust Exploitation       | Residual: every approval rests on your reading.                                                                                                                                                                                                                    |
| ASI10 Rogue Agents                         | Readers and the patcher are confined whatever they intend (LLM06); the main agent only by your approvals outside auto mode.                                                                                                                                        |

## Future work

Rudimentary checks that narrow, not close, the risks above:

- `update` shows each changed **Skill**'s text diff, so vetting covers only what changed.
- Flag scripts, URLs and shell commands in **Skill** text for you to review.
- Bound the patcher's reply as a reader's `text` is, and have the main agent treat it and the names of the files it
  changed as quoted data.
