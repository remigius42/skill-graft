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

## What the Check enforces on Claude Code

On Claude Code, the **Check** reads **Skill** text only through confined, headless agents, checked on Claude Code
2.1.309:

- **Readers.** Each checked **Skill** gets its own `claude -p --restricted --strict-mcp-config`, with the tools `Read`,
  `Grep` and `Glob` only and no MCP server, run from a new empty folder holding a copy of that **Skill**'s own patch
  files, its other folders granted with `--add-dir`: its **Upstream** folder, its vendored copy, its targets'
  **Upstream** folders. `--restricted` confines the file tools to those folders and drops every tool that runs code,
  and ignores the user's settings, so none can widen it. The reader definition ships with the skill
  (`skills/graft-check/reader.json`).
- **The main agent** never opens a **Skill**'s **Upstream** text, vendored copy or patch files. It holds CLI output,
  `skill-graft.toml`, the lock and the readers' reports, whose quoted `text`, one line of at most 200 characters, it
  shows and never acts on.
- **The patcher** writes a **Patch** with `Read`, `Edit` and `Write` only, confined to a temporary folder holding a
  working copy, out of reach of the base it is diffed against. You read the diff before it goes into the **Package**.
- **Fix arguments** must come from CLI output or the config, each side of the slash a name skill-graft accepts, quoted.
  A finding whose fix fails this is reported without one.

Where the skill cannot start a hardened reader (another harness, no `claude` on `PATH`, a `claude` without those
flags), it says the **Check** is unhardened and why, and reads in its own session only on your yes.

## Residual risks

- **Report text.** A reader's quoted `text` reaches the main agent. It is short and shown, never followed, and you
  accept each fix; this holds at the prompt level only.
- **Fix arguments** are checked by the main agent, at the prompt level too.
- **A file skipped as binary.** A file other than Markdown that holds a NUL byte and is not UTF-8, such as UTF-16 text
  without a byte order mark, is skipped. No Markdown file can be.
- **Visible injection.** Readers are confined, not trusted: one can still misreport what a **Skill** says.
- **A later Claude Code** could change what `--restricted` confines. The `injected` eval scenario
  (`evals/graft-check/`) catches that when the skill changes.

Other harnesses are likely not secure: their **Check** reads **Skill** text in the session that holds your shell.

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
  started from a session authenticated by that variable alone reports "Not logged in", and the **Check** names each
  **Skill** as having no report. A login stored by `claude /login` works.
