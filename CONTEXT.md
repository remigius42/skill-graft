# skill-graft

skill-graft builds a user's agent skills from other people's repositories: the skills they ask for, every
skill those reach, renamed and patched as the user declares.

## Language

**Source**:
A repository or local folder that skills are taken from, known by the alias the user gives it.
_Avoid_: Pack, repo, upstream (that is a **Skill**'s text)

**Ref**:
The commit a git **Source** is read at. Only `update` moves it.
_Avoid_: Pin, version, revision

**Skill**:
A folder holding a `SKILL.md`, found anywhere in a **Source**.
_Avoid_: Command, plugin

**Skill ID**:
`<source alias>/<name>`, where the name is the `SKILL.md` front matter `name:`, else the folder name. Unique
within a **Source**.
_Avoid_: Path, slug

**Reference**:
A mention of a **Skill** by name in any Markdown file of another **Skill**: a slash command (`/grilling`), a
Skill tool call (`Skill(grilling)`, or a sentence telling the reader to call the Skill tool with `"grilling"`),
or prose (`grilling` in backticks, or a hyphenated name). A slash or Skill tool **Reference**
resolves in its own **Source** first, else in exactly one other **Source**; a prose **Reference** resolves only
in its own **Source**.
_Avoid_: Dependency, link, import

**Bind**:
A user rule that fixes where **References** of every form to one name from one **Source** resolve, overriding
the default, or that they resolve nowhere: such a name is then not a **Reference** at all. A **Reference** bound
to a **Skill** of another name is rewritten to its **Deployed name**.
_Avoid_: Alias, override, pin

**Entry**:
A **Skill ID** the user asks for directly.
_Avoid_: Root, selection

**Hull**:
The **Entries** plus every **Skill** reachable from them through slash and Skill tool **References**. Prose
**References** never extend it.
_Avoid_: Closure, graph, dependency tree

**Rename**:
A user rule that gives one **Skill** a new **Deployed name**, carried into every **Reference** to it.
_Avoid_: Alias, bind

**Prefix**:
A user rule that puts one string before the name of every **Skill** of one **Source**, giving each **Hull**
**Skill** of it a new **Deployed name**, carried into every **Reference** as a **Rename** is. A **Rename** of
the **Skill** overrides it.
_Avoid_: Namespace, glob rename

**Patch**:
A user's unified diff against a **Skill**'s upstream text. Applied before **References** resolve and before
**Renames**, so it never mentions a **Deployed name**.
_Avoid_: Override, fix

**Upstream**:
A **Skill** as its **Source** has it where it is read (at the **Ref**, at the tip during `update`, or in a
path **Source**'s folder), before any **Patch**. As an adverb, "upstream" means in the **Source** ("a new
commit upstream"); as a noun it is never the **Source** itself.
_Avoid_: Original, pristine, vanilla

**Deployed name**:
The name a **Skill** carries once installed: its **Rename**, else its **Source**'s **Prefix** before its name,
else its name. Unique across the **Hull**.
_Avoid_: Target name, alias

**Reserved name**:
A name a **Deployed name** must not take because a harness already uses it, such as `code-review`. Comes from
the list skill-graft ships, plus the user's own.
_Avoid_: Built-in, blocklist

**Package**:
The folder skill-graft builds the **Hull** into and APM deploys from, holding the user's `skill-graft.toml`.
One per **Scope**.
_Avoid_: Bundle, output

**Scope**:
Where a **Package** lives and deploys: user scope (the home folder, for every project) or project scope (one
project, for everyone working in it). A command acts on the nearest **Package** above the working folder, and
on the user scope's when there is none.
_Avoid_: Level, mode, global/local

## Example dialogue

> **Dev:** I added `mp/tdd` as an **Entry**. Why is `mp/grilling` in the **Hull**?
>
> **Expert:** `mp/tdd` calls `/grilling`, a slash **Reference**, and it resolves in its own **Source** first.
>
> **Dev:** And `` `diagnosing-bugs` `` in its prose?
>
> **Expert:** A prose **Reference** never extends the **Hull**. `resolve` suggests `mp/diagnosing-bugs`; you
> `add` it as an **Entry** if you want it.
>
> **Dev:** `mp/code-review` clashes with a **Reserved name**. Do I **Bind** it?
>
> **Expert:** No, a **Bind** redirects **References**. You **Rename** it; its **Deployed name** becomes
> `mp-code-review`, and every **Reference** to it follows, prose included.
