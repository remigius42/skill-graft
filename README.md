# skill-graft

Graft agent skills from other people's repositories onto your own setup.

You name the skills you want. skill-graft follows their references to other skills and files, vendors the
whole graph, applies your renames and patches, and hands the result to [APM](https://github.com/microsoft/apm)
to deploy into Claude Code, opencode, and the other harnesses APM supports.

Renames are the reason it exists: a skill named like a harness built-in (`code-review`, `research`,
`prototype`) shadows it or is shadowed by it, and renaming one skill by hand misses the other skills that call
it by name.

Status: early. `skill-graft init` and `skill-graft build` vendor entries from local folders and from git
repositories, read at the commit `ref` names, and deploy them through APM; `skill-graft update` moves each
git source's `ref` to its branch tip. `build` follows slash, Skill tool and prose references to the whole hull,
applies `[rename]` to folders, `name:` and every reference, and checks deployed names against reserved ones;
`skill-graft resolve` shows the tree and writes the lock. Patches are not built yet.

## Development

See [docs/development.md](docs/development.md).
