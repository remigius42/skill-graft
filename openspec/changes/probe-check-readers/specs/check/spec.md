## MODIFIED Requirements

### Requirement: Unhardened only on the user's yes

A **Check** is hardened when its probe, a reader run as every reader runs on a prompt asking only that it answer, in a
new empty folder, exits 0 with the expected answer. The skill SHALL run the probe before reading any **Skill** text,
unless `claude` is not on `PATH` or the user declined their Claude Code account. Otherwise the skill SHALL say the
**Check** is unhardened and why, naming the probe's error, before reading any **Skill** text, and only after the user
says yes read and patch the **Skills** in its own session, where the hardened requirements do not bind it; on anything
else it SHALL end the **Check**.

#### Scenario: No claude

- **WHEN** no `claude` is on `PATH`
- **THEN** the skill says the **Check** is unhardened and why, and waits for the user's yes

#### Scenario: Another harness

- **WHEN** the skill runs in a harness that is not Claude Code and the user does not say yes to using their Claude Code
  account
- **THEN** no `claude` process starts, and the skill says the **Check** is unhardened and waits for the user's yes

#### Scenario: Older Claude Code

- **WHEN** the installed `claude` does not know `--restricted`
- **THEN** the probe fails, and the skill says the **Check** is unhardened, naming the probe's error, and waits for the
  user's yes

#### Scenario: Not logged in

- **WHEN** the probe reports "Not logged in"
- **THEN** the skill says the **Check** is unhardened, naming that error and advising `claude auth login`, and starts no
  other reader

#### Scenario: Declined

- **WHEN** the user does not say yes
- **THEN** the **Check** ends, having read no **Skill** text and changed nothing

## ADDED Requirements

### Requirement: Another harness's readers only on the user's yes

When the skill's session does not run in Claude Code and `claude` is on `PATH`, the skill SHALL say, before the probe,
that its readers and patcher run on the user's Claude Code account, and run the probe only after the user says yes. On
anything else the **Check** SHALL be unhardened, as when the probe fails.

#### Scenario: Another harness with Claude Code

- **WHEN** the skill runs in another harness, `claude` is installed and logged in, and the user says yes
- **THEN** the probe runs, and each checked **Skill** is read by its own reader
