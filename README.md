# [skill-graft](https://github.com/remigius42/skill-graft)

[![Version](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Fremigius42%2Fskill-graft%2Fmain%2Fpyproject.toml&query=%24.project.version&label=version)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/remigius42/skill-graft/actions/workflows/ci.yml/badge.svg)](https://github.com/remigius42/skill-graft/actions/workflows/ci.yml)

Copyright 2026 [Andreas Remigius Schmidt](https://github.com/remigius42)

Graft agent skills from other people's repositories onto your own setup.

You name the skills you want. skill-graft follows their references to other skills and files, vendors the whole graph,
applies your renames and patches, and hands the result to [APM](https://github.com/microsoft/apm) to deploy into Claude
Code, opencode, and the other harnesses APM supports.

Skills call each other (`/grilling`, "call the Skill tool with `domain-modeling`"), so taking one skill means taking
every skill it reaches. Installing a whole collection is fine for a large model, but on a smaller one the full skill set
crowds the context, and taking only a subset by hand means tracing those calls yourself, skill by skill. skill-graft
computes that hull, the skills you ask for plus every skill they call, and deploys only those skills. Renames come with
it: a skill named like a harness built-in (`code-review`) shadows it or is shadowed by it, and renaming one skill by
hand misses the other skills that call it by name.

If you already know every skill you need, APM alone can install just those: `apm install <owner>/<repo> --skill <name>`
([docs](https://microsoft.github.io/apm/reference/cli/install/#skill-subset)). skill-graft also finds the skills they
reference, lets you rename skills whose names clash, shows who calls what (`tree`, `why`), and applies your patches,
checking on `update` that they still apply.

## Installation

skill-graft runs on Linux and macOS, and on Windows through [WSL](https://learn.microsoft.com/windows/wsl/). Native
Windows is unsupported: there every command prints `skill-graft: native Windows is unsupported: run skill-graft in WSL`
and exits 1.

skill-graft needs Python 3.11 or later. It is not on PyPI; install a release from the repository with any of:

```sh
uv tool install git+https://github.com/remigius42/skill-graft@v0.3.0
pipx install --python python3.11 git+https://github.com/remigius42/skill-graft@v0.3.0
pip install git+https://github.com/remigius42/skill-graft@v0.3.0      # into the active environment
pipenv install "skill-graft @ git+https://github.com/remigius42/skill-graft@v0.3.0"
```

uv picks a suitable Python itself; pipx and pip use theirs, so point them at 3.11 or later. pipenv installs into that
project's environment: run it as `pipenv run skill-graft`.

skill-graft also runs `git`. With git 2.44 or later, looking up what the [cache](#cache) holds never contacts the
remote; the git macOS ships is older, Homebrew's is not. A remote that refuses files asked by name needs git 2.36 or
later.

These install the latest release; the others are listed under
[releases](https://github.com/remigius42/skill-graft/releases), and each tag's README describes its release. To install
the unreleased `main` instead, drop `@v0.3.0` from the URL. `skill-graft --version` names what is installed: the
version, the tag or branch the URL names and the commit, `skill-graft <version> (v<version> @ <commit>)`, or only the
commit for a URL naming neither.

The release tags after `v0.3.0` are signed with this SSH key, fingerprint
`SHA256:U5FNzbtnPR2kPX/Edlg1+p7rJmlBIx88HBKkzBVmOWE`:

```text
remigius42-github.dcds7@aleeas.com namespaces="git" ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHKYDmxyNPjrRUXm2mr6s8UiL/yT89vmPC0gPB1pZc2L
```

GitHub shows such a tag as **Verified**. To check one yourself, save that line as `~/allowed_signers`, then in a clone
run `git -c gpg.ssh.allowedSignersFile="$HOME/allowed_signers" verify-tag v<version>`; git reads a relative path from
the clone's top folder. A tag can be moved, a commit cannot: to install exactly what you checked, put the commit
`git rev-parse "v<version>^{commit}"` prints in the URL in place of the tag.

skill-graft runs APM as a command, so `apm` must be on `PATH` as well, in version 0.35.0: the folders APM deploys to
were measured on it, and another version may deploy elsewhere. Install it the same way, e.g.
`uv tool install apm-cli==0.35.0`, `pipx install apm-cli==0.35.0` or `pip install apm-cli==0.35.0`.

## Usage

Besides skill-graft and APM, you need a harness folder for APM to deploy into, such as `~/.claude/` for Claude Code. To
deploy the `tdd` skill of [mattpocock/skills](https://github.com/mattpocock/skills), and every skill it calls, create
your package:

```sh
skill-graft init
```

`init` writes the package's config, `~/.apm/skill-graft/skill-graft.toml`, all commented out. Add the repository to it
as a source, a new table after the comments (the commented `[sources.mp]` there is only an example):

```toml
[sources.mp]
git = "https://github.com/mattpocock/skills.git"
```

Then:

```sh
skill-graft update mp                                    # set the source's ref to its branch tip
skill-graft add mp/tdd --dry-run --diff-file review.diff # write the text it would vendor, nothing else
skill-graft add mp/tdd                                   # ask for the skill; vendors the hull and writes the lock
skill-graft tree                                         # see the hull: mp/tdd and every skill it calls
skill-graft deploy                                       # deploy what skill-graft.lock records through APM
```

The dry run writes `mp/tdd` and every skill it calls, as they would deploy, to `review.diff`, and writes nothing else.
Read it in an editor, never by printing it to a terminal: it is untrusted text. Then run the `add` itself.

After editing `skill-graft.toml` or a patch by hand, run `skill-graft resolve` before `deploy`, previewing it first with
`skill-graft resolve --dry-run --diff-file review.diff`: `deploy` deploys only what the lock records, and names
`resolve` when the config or a patch differs from it. An edit to a vendored copy in `.apm/skills/` is refused too; move
it into a patch, or delete the folder to vendor it again.

`tdd` and the skills it calls are now in `~/.claude/skills/`. To share skills through a project instead, see
[A package for one project](#a-package-for-one-project); to deploy them under other names, `[rename]` and `prefix` in
[Config](#config); to change what a skill says, [Writing a patch](#writing-a-patch).

Later, to move `mp` to its new tip, review what would change first:

```sh
skill-graft update mp --dry-run --diff-file review.diff # write each changed skill's text as deployed
skill-graft update mp --expect <hull-digest>            # the `apply:` line the dry run printed
```

Read `review.diff` in an editor, as before. The `apply:` line updates to exactly the hull you read; a push, a path
source's edit, a patch or a rename since then makes it refuse.

## Commands

`resolve`, `update` and the editing commands resolve and stage: they write the lock and `.apm/skills/` together, and
never deploy. `deploy` checks the package against the lock and deploys it through APM.

Options are taken only spelled in full: `--dry` is a usage error, not `--dry-run`.

### Setup

| Command            | What it does                                                                                    |
| ------------------ | ----------------------------------------------------------------------------------------------- |
| `init [--project]` | Create the package, `~/.apm/skill-graft/` (or `./.apm/skill-graft/`), and register it with APM. |

### Staging

| Command                                     | What it does                                                                                                                                 |
| ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `resolve`                                   | Compute the hull from the config as it stands, vendor it patched and renamed, print the tree and the skills prose mentions outside the hull. |
| `add <skill-id>…`                           | Append skills to `entries`, keeping the file's comments, once the result resolves.                                                           |
| `remove <skill-id>…`                        | Delete skills from `entries`; one another entry reaches stays in the hull.                                                                   |
| `rename <skill-id> <name>`                  | Set a skill's deployed name; the name it would deploy as without a key undoes it.                                                            |
| `bind <alias>/<name> <skill-id>\|false`     | Resolve `<name>` from that source to the skill, or to no reference.                                                                          |
| `unbind <alias>/<name>`                     | Remove that bind, so `<name>` resolves by default again.                                                                                     |
| `update [source…] [--expect <hull-digest>]` | Move each git source's `ref` to its branch tip, if the hull still resolves and every patch still applies there.                              |

Each staging command takes `--dry-run` and `--diff-file <file>`. `--dry-run` resolves and prints the hull diff, each
added, removed or changed skill with its changed files but never their text, and writes nothing but `--diff-file`'s
file. `--diff-file <file>` writes that text as deployed, the Deployed diff, to a new `*.diff` file, or one it wrote
before; read it in an editor. `update` compares against the hull at the current refs, the other commands against the
vendored copies. `update`'s `--expect <hull-digest>` updates only to the hull a dry run showed.

### Deploying

| Command                                     | What it does                                                                                                                                                                                                                                                             |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `deploy [--no-apm-install \| --into <dir>]` | Deploy what the lock records through APM, refusing a hull other than the lock's or an edited vendored copy. `--no-apm-install` stops before running APM. `--into <dir>` writes the skills and the lock into an empty `<dir>` instead, never touching the package or APM. |

### Inspecting

| Command                                      | What it does                                                                                                        |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `tree [--format text\|mermaid [--link]]`     | Print the hull, writing nothing; with `--format mermaid`, `--link` gives a mermaid.live URL: see the warning below. |
| `why <skill>`                                | Print the paths from the entries that reach a skill, and its upstream folder.                                       |
| `help [command]`, or `--help` on any command | Explain it.                                                                                                         |

Warning: `tree --format mermaid --link` hands the diagram to mermaid.live, a third-party site whose page code can read
it: it then sees which upstream repositories and refs you use, a target list for a supply-chain attack on them.

## Config

`skill-graft.toml`, in the package:

```toml
entries = ["mp/tdd", "mp/implement", "own/chisel"]
reserved = ["review"]

[sources.mp]
git = "https://github.com/mattpocock/skills.git"
branch = "main"  # optional; defaults to the remote's default branch
ref = "<sha>"
prefix = "mp-"   # optional; every skill of `mp` deploys as mp-<name>

[sources.cp]
git = "https://github.com/cursor/plugins.git"
ref = "<sha>"
subdirectory = "pstack/skills"  # optional; read only this folder of the repository

[sources.own]
path = "~/skills"

[rename]
"own/chisel" = "own-chisel"
"mp/tdd" = "tdd"  # wins over the prefix

[bind]
"mp/grilling" = "own/grilling"
"mp/tmp" = false  # `/tmp` from `mp` is not a reference

[patches]
"mp/implement" = ["patches/implement-no-pr.patch"]

[check]  # optional; graft-check's limits, defaults shown
reader-turns = 30
reader-budget-usd = 1.0
patcher-turns = 10
patcher-budget-usd = 0.5
readers-at-once = 4
```

- `entries`: the skills you ask for. Slash references and Skill tool calls (`Skill(x)`, or "call the Skill tool with
  `x`") pull in the rest of the hull; prose mentions only become suggestions.
- `sources`: local folders (`path`) and git repositories (`git`), read at the commit `ref` names.
- `subdirectory`: a git source is read only in this folder, as if it were the repository's root, for a repository
  holding several plugins whose skills share names. It must be a real folder at the commit read, or the command fails;
  `update` then leaves `ref` where it is. The lock still records each skill's `upstream` relative to the repository's
  root.
- `prefix` and `[rename]`: a skill deploys as its `[rename]` value, else its source's prefix before its name, else its
  name. Carried into its folder, `name:` and every reference.
- `[bind]`: settles which skill a reference means when several sources have one of that name, or with `false` makes it
  no reference at all.
- `[patches]`: unified diffs, applied before renames, so a patch can change what a skill calls (see
  [Writing a patch](#writing-a-patch)).
- `reserved`: deployed names to refuse, on top of the harness built-ins skill-graft warns about.
- `[check]`: how far graft-check's readers and patcher may go: turns and spend in USD each, and how many readers run at
  once. Each value is written in plain decimal digits; [docs/security.md](docs/security.md#limits) says what reaching a
  limit does.

## A package for one project

`skill-graft init` creates your package, `~/.apm/skill-graft/`, deployed for you in every project. For skills a team
shares through one repository, run `skill-graft init --project` in its root (which needs a harness folder such as
`.claude/`, or APM refuses): it creates `.apm/skill-graft/` there and registers it in the project's `apm.yml`. Every
command then acts on the nearest `.apm/skill-graft/` above the working folder, and on `~/.apm/skill-graft/` when there
is none.

Commit the whole `.apm/skill-graft/`, vendored skills and its `.gitattributes` included, with `apm.yml` and
`apm.lock.yaml`; `.gitattributes` keeps git from changing the vendored skills' line endings, which `deploy` would refuse
as edits. Teammates then need only APM: `apm install` deploys the skills, and only whoever changes them runs
skill-graft. Keep path sources inside the project (`path = "../../skills"`) and the rest git sources: the lock then
records them relative to the package and reads the same on every machine; a path outside the project is recorded
absolute.

## Checking a package

skill-graft finds references by their form alone, so it misses "run the grilling skill", takes `/tmp` for a call, and
can rewrite a word a prefix happens to match. The `graft-check` skill, in this repository's `skills/`, has an agent read
the vendored skills for those mistakes. Install it like any other skill, with the lines `init` writes commented out into
`skill-graft.toml`:

```toml
[sources.skill-graft]
git = "https://github.com/remigius42/skill-graft.git"
subdirectory = "skills"
```

```sh
skill-graft update skill-graft
skill-graft add skill-graft/graft-check
skill-graft deploy
```

Until that `update` sets the source's `ref`, every `deploy` fails, not only graft-check's.

Run it in your harness as `/graft-check`, or `/graft-check mp/tdd` to check only some skills; it runs only when you ask.
It deploys into a temporary folder with `deploy --into`, and has one reader per skill compare its upstream text with its
vendored copy. The readers report missed and false references, references resolved to the wrong skill, wrong or missed
rewrites, and relative links vendoring broke. For each finding it proposes `add`, `bind`, `unbind` or a patch, and
applies it only once you accept; a patch is written by a confined patcher, and you read its diff before it goes into the
package. It never runs APM: when the package would change, it tells you to run `skill-graft deploy`. It reads lock
`version` 1 only; for a newer lock, update the source you installed it from.

## Cache

Git **Sources** are cached under `$XDG_CACHE_HOME/skill-graft/`, else `~/.cache/skill-graft/`: one repository per URL,
holding commits and trees and only the files read, and one export per commit and `subdirectory`.

- Any command but `init` and a `--dry-run` removes, as it ends, each export no command has used for 30 days. One removed
  is exported again from its repository when next needed, without the remote.
- No command removes a repository. Every **Ref** read stays in its repository, with its files, even after it vanished
  from every branch upstream.
- Deleting a repository, or the whole folder, by hand is safe unless a **Ref** you use has since vanished upstream: that
  one cannot be fetched again.

## Security

Skill text comes from other people's repositories and may carry prompt injection. [docs/security.md](docs/security.md)
has the details.

- skill-graft fails resolution on a skill holding a hidden character (tag characters, bidi controls, supplementary
  variation selectors), as APM's install does, so none reaches any agent through the hull.
- Wherever a working Claude Code is installed, graft-check reads skill text only through `claude -p --restricted`
  readers limited to `Read`, `Grep` and `Glob`, without MCP servers, confined to that skill's folders, and patches
  through a patcher confined to a temporary folder. A probe reader must answer first; outside Claude Code it asks before
  using your Claude Code account. The probe and keeping skill text from the main agent are steps of the skill: they hold
  only as far as your harness's model follows them. Otherwise it says it is unhardened and why, and reads only on your
  yes; an unhardened check is likely not secure.
- In a hardened check, each reader and the patcher stop at a cap on their turns and their spend, and at most 4 readers
  run at once, all settable in `[check]` ([Limits](docs/security.md#limits)). The patcher's reply never reaches the main
  agent, and its diff reaches it only as counts.
- A reader's reply reaches the main agent only as a report filter admits it, held to the report shape and bound in code,
  or, when the reader fails, as one bounded error line.
- Run it outside auto mode; in Claude Code's sandbox, allow the API's domain. Fix arguments and how many readers run at
  once are checked at the prompt level only.

Report a vulnerability privately, as [SECURITY.md](SECURITY.md) says, not in a public issue.

## Writing a patch

A patch is a unified diff against the skill's upstream folder, which `skill-graft why <skill>` prints on its last line.
No command writes one; in a shell (a project package keeps its patches in its own `.apm/skill-graft/`):

```sh
upstream="$(skill-graft why mp/implement | sed -n 's/^upstream: //p')"
cd "$(mktemp -d)"
cp -rL "$upstream" base && rm -rf base/.git
# Only for a skill that already has patches: apply them first, in order.
(cd base && git apply -p1 ~/.apm/skill-graft/patches/first.patch)
cp -r base edited
"$EDITOR" edited/SKILL.md
LC_ALL=C diff -ruN base/ edited/ > ~/.apm/skill-graft/patches/second.patch
```

Then list it, after the skill's earlier patches:

```toml
[patches]
"mp/implement" = ["patches/first.patch", "patches/second.patch"]
```

`skill-graft resolve --dry-run --diff-file review.diff` writes the patched skill as it would deploy to `review.diff`;
read it in an editor, then run `skill-graft resolve`.

`diff` needs `-N`, or added and deleted files are lost; skill-graft refuses such a patch, and binary changes, by the
lines `diff` writes for them in English: hence `LC_ALL=C`. A file such a patch leaves empty is deleted, with any folder
that leaves empty, as `-N` writes a deleted file as one emptied; so any `diff`, GNU or the BSD one of macOS, deletes
alike. A `git diff` patch applies as git applies it. A patch must not change the skill's `name:`: use `[rename]`. When
`update` finds that a patch no longer applies at a new commit, it keeps the old `ref` and names the upstream folder at
the new commit: redo the patch against it, then run `update` again.

## Contributing

Report bugs and suggest ideas in [GitHub issues](https://github.com/remigius42/skill-graft/issues), and vulnerabilities
as [SECURITY.md](SECURITY.md) says. To change the code, see [CONTRIBUTING.md](CONTRIBUTING.md).

This is a personal exploration project with best-effort maintenance. Responses to issues or pull requests may be slow,
and changes that don't align with the project's direction are unlikely to merge.

If skill-graft saves you time, you can [buy me a coffee](https://buymeacoffee.com/remigius).
