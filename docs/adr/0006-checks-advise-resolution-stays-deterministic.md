# A check advises; resolution stays deterministic

skill-graft finds references by their form alone, so it misses "run the grilling skill", takes `/tmp` for a call and
warns that no skill matches it, and can rewrite a word a prefix happens to match. An agent reading the text catches
these, but skill-graft never asks one: the same TOML must give the same hull, lock and vendored bytes on every machine,
and the runtime dependencies stay the standard library and `tomlkit`. The agent works in the `graft-check` skill
instead, invoked by the user, and its findings become binds, entries and patches the user accepts, so every fix lands in
the config, where resolution stays reproducible.

## Considered Options

- Let an agent decide references during `resolve`: better guesses, but a lock no one can reproduce.
- Let the agent edit the vendored skills: the next `build` overwrites the edits, and the lock's hashes lie.
