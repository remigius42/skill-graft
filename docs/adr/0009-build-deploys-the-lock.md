# Build deploys what the lock records

`build` deploys only what `skill-graft.lock` records; `resolve`, `update` and the editing commands are how a change gets
in. Each of those writes the lock and the **Vendored copies** together, and every command that vendors first checks the
copies against the lock. `build` then refuses a git **Source**'s **Skill** whose hash differs from the lock's, any
change to the **Hull**'s shape, an edited or unknown **Vendored copy**, and a missing lock, naming `resolve`. An edited
path **Source**'s text is named and deployed: editing one's own **Skills** is the normal workflow there. Until now
`build` re-resolved and overwrote the lock and the copies, so the lock's hashes recorded what was deployed but nothing
checked them: in project scope a lock reviewed in a pull request said nothing about what a later `build` deployed, and
edits to a **Vendored copy** were lost without a word. Against someone with the user's own access this guards nothing,
as they can rewrite the lock too; it names drift and accidents, and changes no one reviewed on another machine.

## Considered Options

- Re-resolve at `build` and refuse only what the config cannot explain: no new step after a hand edit, but the lock
  records **Patch** names, not their contents, so an edited **Patch** file would deploy unchecked.
- Record the **Vendored copies**' hashes beside the lock: no need for every lock writer to vendor, but a second record
  that can drift from the first.
- An override flag: the way out of an edited copy is a **Patch**, or deleting the copy to discard the edit; that of a
  hand edit to the config, `resolve`.

## Consequences

After editing `skill-graft.toml` or a **Patch** by hand, and after a skill-graft upgrade that changes how it rewrites,
the user runs `resolve` before `build`. `resolve` and the editing commands now write `.apm/skills/`, so in project scope
a pull request changing the config also shows the text it deploys; the **Package**'s `.gitattributes`, which they write
if missing, keeps git from converting the committed copies' line endings, which would read as edits. A **Package** whose
lock a `resolve` or an edit wrote after its last `build` holds copies older than its lock, which the first command after
upgrading refuses as edited; the user checks them and deletes them.
