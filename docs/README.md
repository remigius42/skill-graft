# Docs

| Where                                                         | What                                                                                                  |
| ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| [README](../README.md)                                        | what skill-graft does, installing it, the commands and config                                         |
| [howto.md](howto.md)                                          | common tasks: adding a source, updating, patches, projects, graft-check                               |
| [CONTEXT.md](../CONTEXT.md)                                   | the glossary: the terms every other doc uses                                                          |
| [security.md](security.md)                                    | the threat of untrusted skill text, what stops it and what does not                                   |
| [architecture.md](architecture.md)                            | the package's files, how a write stays atomic, the source layers                                      |
| [apm-behavior.md](apm-behavior.md)                            | what APM 0.35.0 was measured to do, which skill-graft relies on                                       |
| [assets/](assets/)                                            | the logo: `skill-graft.svg` at 64 px and up, `skill-graft-small.svg` below, where the full mark blurs |
| [adr/](adr/)                                                  | the reasons for the less obvious decisions, one record each                                           |
| [openspec/specs/](../openspec/specs/)                         | what each capability does, as requirements and scenarios                                              |
| [CHANGELOG.md](../CHANGELOG.md)                               | what changed for users in each release                                                                |
| [SECURITY.md](../SECURITY.md)                                 | how to report a vulnerability                                                                         |
| [skills/graft-check/SKILL.md](../skills/graft-check/SKILL.md) | the **Check**: the skill an agent follows to check a package                                          |
| [skills/graft-vet/SKILL.md](../skills/graft-vet/SKILL.md)     | the **Vet** with readers: the scan plus a confined reader per skill                                   |
| [CONTRIBUTING.md](../CONTRIBUTING.md)                         | setup, the change workflow, checks, tooling and evals                                                 |
| [mutation-testing.md](mutation-testing.md)                    | how to run the two mutation harnesses and read their survivors; mutmut's baseline                     |
| [releasing.md](releasing.md)                                  | the maintainer's steps to release a version                                                           |
| [evals/graft-check/README.md](../evals/graft-check/README.md) | the opt-in evals of graft-check                                                                       |
| [evals/graft-vet/README.md](../evals/graft-vet/README.md)     | the opt-in evals of graft-vet, and how to read and compare its corpus scores                          |
| [mutation/](../mutation/)                                     | the regex harness: its targets, and the mutants listed as equivalent                                  |
| [AGENTS.md](../AGENTS.md)                                     | the rules for commits, code and tests                                                                 |
