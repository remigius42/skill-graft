# skill-graft

skill-graft builds a user's agent skills from other people's repositories: the skills they ask for, every
skill those reach, renamed and patched as the user declares.

## Language

**Source**:
A repository or local folder that skills are taken from, known by the alias the user gives it.
_Avoid_: Pack, repo, upstream

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
Skill tool call, or prose (`grilling` in backticks, or a hyphenated name). A slash or Skill tool **Reference**
resolves in its own **Source** first, else in exactly one other **Source**; a prose **Reference** resolves only
in its own **Source**.
_Avoid_: Dependency, link, import

**Bind**:
A user rule that fixes where **References** of every form to one name from one **Source** resolve, overriding
the default, or that they resolve nowhere: such a name is then not a **Reference** at all.
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

**Patch**:
A user's unified diff against a **Skill**'s upstream text. Applied before **References** resolve and before
**Renames**, so it never mentions a **Deployed name**.
_Avoid_: Override, fix

**Deployed name**:
The name a **Skill** carries once installed: its name after **Renames**. Unique across the **Hull**.
_Avoid_: Target name, alias

**Reserved name**:
A name a **Deployed name** must not take because a harness already uses it, such as `code-review`. Comes from
the list skill-graft ships, plus the user's own.
_Avoid_: Built-in, blocklist

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
