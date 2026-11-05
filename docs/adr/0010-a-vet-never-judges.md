# A vet never judges

A **Vet** reads text written by the people it vets, and an agent judging hostile text is what that text can be written
to fool: a **Skill** can tell its reader it is harmless. So a **Vet** gives **Flags**, never a verdict or a score, and
no **Flag** is never a pass. Its scan is code, in the CLI, and prints no **Skill** text. Its readers are confined, one
per **Skill**, see only that **Skill**'s folder and never the scan, and reply with locations and categories only, no
free text, so a steered reader can only misplace **Flags**, not talk to the main agent. Code, not the main agent, merges
the two and counts the scan's **Flags** a reader missed, the sign it was steered. With no hardened reader, a **Vet**
runs the scan alone: unlike the **Check**, it never reads **Skill** text in the session that holds your shell, since
that text is what it is vetting.

## Considered Options

- A safe/unsafe verdict or risk score: what users want, but one an injected **Skill** can earn.
- Readers that explain what they found: more useful, but every word is a channel from the **Skill** to the main agent.
- Readers shown the scan: they would echo it, and the cross-check needs two independent reads.
- Reading unhardened on the user's yes, as the **Check** does: exposes the shell to the very text in question.
- A pattern list that blocks, as **Hidden characters** do: legitimate **Skills** call `sudo` and `curl`, and a list is
  easy to evade.
