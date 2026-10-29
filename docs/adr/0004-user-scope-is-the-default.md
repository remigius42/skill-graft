# User scope is the default, project scope is opt-in

`skill-graft init` creates the user scope's package, `~/.apm/skill-graft/`; only `init --project` creates one in a
project, although APM defaults the other way. Choosing entries, renaming, patching and moving refs is work kept up per
package, and a package per repository multiplies it. A project package pays off only when a team shares one setup
through the repository. Every other command acts on the nearest `.apm/skill-graft/` above the working folder, as git
finds `.git`; the home folder is an ancestor of most folders, so user scope is the fallback of the same rule rather than
a separate flag.
