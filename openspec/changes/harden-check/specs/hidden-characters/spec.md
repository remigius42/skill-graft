# Spec Delta

## Purpose

Keeps invisible instructions out of the **Hull**: resolution fails on a **Hidden character** in a **Skill**, so no
agent, the **Check**'s included, reads text a person cannot see.

## ADDED Requirements

### Requirement: Hidden characters fail resolution

Resolution SHALL fail, exit 1, when a **Hull** **Skill** holds a **Hidden character** in a file's text or in a file or
folder name: a Unicode tag character (U+E0001 to U+E007F), a bidi embedding, override or isolate (U+202A to U+202E,
U+2066 to U+2069), or a supplementary variation selector (U+E0100 to U+E01EF). The error SHALL name each file, line,
code point and class.

#### Scenario: Tag characters in SKILL.md

- **WHEN** **Entry** `mp/tdd`'s `SKILL.md` holds U+E0041 on line 7
- **THEN** `skill-graft resolve` exits 1, naming that file, line 7, `U+E0041` and the tag character class

#### Scenario: Bidi override in a script

- **WHEN** a **Hull** **Skill**'s `scripts/run.sh` holds U+202E
- **THEN** `skill-graft resolve` exits 1, naming `scripts/run.sh`

#### Scenario: In a file name

- **WHEN** a **Hull** **Skill** holds a file whose name contains U+202E
- **THEN** `skill-graft resolve` exits 1, naming that path and `U+202E`

#### Scenario: Outside the hull

- **WHEN** a **Source** holds a **Skill** with U+E0041 that no **Hull** **Skill** reaches
- **THEN** `skill-graft resolve` succeeds

### Requirement: Which files are read

A Markdown file SHALL be read as UTF-8, and one that does not decode strictly as UTF-8 SHALL fail resolution, naming it,
since its **References** could not be read. Any other file SHALL be read, in this order: in UTF-32 or UTF-16 after a
byte order mark for it, the UTF-32 marks tried first; else as UTF-8 when it decodes strictly, NUL bytes included; else,
when it holds no NUL byte, as UTF-8 with each byte that is not UTF-8 counting as no character. A file with a NUL byte
that none of these decode is binary and SHALL be skipped.

#### Scenario: UTF-16 file

- **WHEN** a **Hull** **Skill**'s `references/guide.txt` is UTF-16LE with a byte order mark and holds U+E0041
- **THEN** `skill-graft resolve` exits 1, naming that file

#### Scenario: NUL byte in text

- **WHEN** a **Hull** **Skill**'s `SKILL.md` holds a NUL byte and U+E0041, and is otherwise UTF-8
- **THEN** `skill-graft resolve` exits 1, naming `SKILL.md` and `U+E0041`

#### Scenario: One invalid byte

- **WHEN** a **Hull** **Skill**'s `notes.txt` holds byte 0xFF and U+E0041
- **THEN** `skill-graft resolve` exits 1, naming `notes.txt` and `U+E0041`

#### Scenario: Markdown that is not UTF-8

- **WHEN** a **Hull** **Skill**'s `guide.md` holds byte 0xFF, or is UTF-16 with a byte order mark
- **THEN** `skill-graft resolve` exits 1, naming `guide.md` as not UTF-8

#### Scenario: Binary file

- **WHEN** a **Hull** **Skill** holds a PNG image, which has NUL bytes
- **THEN** the image is not read, and resolution goes on

### Requirement: Upstream text and patches are both checked

For a **Skill** with **Patches**, its **Upstream** folder and the lines its patch files add SHALL be checked, so a
**Patch** that adds a **Hidden character** fails, naming the patch file and its line, and one that removes it does not
clear the **Upstream** one. In the patched copy, every file and folder name the **Upstream** folder lacks SHALL be
checked too, named by its path inside the **Skill** as in the patched copy.

#### Scenario: Patch adds one

- **WHEN** `mp/tdd`'s patch `patches/tdd.patch` adds a line holding U+202E to its `SKILL.md`
- **THEN** `skill-graft resolve` exits 1, naming `patches/tdd.patch` and that line of it

#### Scenario: Patch moves one

- **WHEN** `mp/tdd`'s **Upstream** `SKILL.md` holds U+E0041 on line 7, and its **Patch** adds three lines above it
  without touching line 7
- **THEN** `skill-graft resolve` reports U+E0041 once, on line 7 of the **Upstream** file

#### Scenario: Patch removes one

- **WHEN** `mp/tdd`'s **Upstream** `SKILL.md` holds U+E0041 and its **Patch** removes that line
- **THEN** `skill-graft resolve` exits 1, naming the **Upstream** file

#### Scenario: Patch creates a name

- **WHEN** `mp/tdd`'s **Patch** creates a file whose name contains U+202E, written quoted in the patch's header
- **THEN** `skill-graft resolve` exits 1, naming that path as in the patched copy

### Requirement: One run reports every hidden character

A **Skill** holding a **Hidden character**, or a Markdown file that is not UTF-8, SHALL still have its other
**References** read, so the walk reaches every **Skill** it would, and one run SHALL report every **Hidden character**
and every such Markdown file of the **Hull**. Like a failing **Patch**, they SHALL be reported before another error that
stops the walk, and the warnings for unused `[rename]`, `[patches]` and `[bind]` keys SHALL be left out.

#### Scenario: Two skills

- **WHEN** **Entry** `mp/tdd` holds U+E0041, and calls `/grilling`, which holds U+202E
- **THEN** one `skill-graft resolve` reports both

#### Scenario: With Markdown that is not UTF-8

- **WHEN** **Entry** `mp/tdd`'s `notes.md` is Latin-1, and `mp/tdd` calls `/grilling`, which holds U+202E
- **THEN** one `skill-graft resolve` reports both

#### Scenario: With a failing patch

- **WHEN** `mp/tdd`'s **Patch** fails and **Entry** `mp/notes` holds U+E0041
- **THEN** one `skill-graft resolve` reports both

### Requirement: Invisible debris warns

A zero-width space, joiner or non-joiner (U+200B to U+200D), word joiner (U+2060), soft hyphen (U+00AD), variation
selector (U+FE00 to U+FE0E), bidi mark (U+200E, U+200F, U+061C), invisible operator (U+2061 to U+2064), annotation
marker (U+FFF9 to U+FFFB) or deprecated formatting character (U+206A to U+206F) in a file of a **Hull** **Skill** or one
of its patch files SHALL warn once per file, naming the file, its first line holding one, and the count, and resolution
SHALL go on.

#### Scenario: Zero-width space

- **WHEN** a **Hull** **Skill**'s `SKILL.md` holds two U+200B, first on line 3
- **THEN** `skill-graft resolve` succeeds and warns once, naming the file, line 3 and 2 characters

### Requirement: Writing commands fail alike

`resolve`, `build` (with `--into` too), `update`, and the commands that edit the config SHALL fail on a **Hidden
character** as `resolve` does, writing nothing: no lock, no `.apm/skills/`, no `ref`, no config change, and no `apm`
run.

#### Scenario: Build into a folder

- **WHEN** a **Hull** **Skill** holds U+E0041 and the user runs `skill-graft build --into <dir>`
- **THEN** it exits 1 and `<dir>` stays empty

#### Scenario: Update to a tip holding one

- **WHEN** the tip of **Source** `mp`'s branch adds U+E0041 to a **Hull** **Skill**, and the user runs
  `skill-graft update mp`
- **THEN** it exits 1 and `mp`'s `ref` is unchanged

#### Scenario: Add a skill holding one

- **WHEN** `mp/notes` holds U+E0041 and the user runs `skill-graft add mp/notes`
- **THEN** it exits 1 and `skill-graft.toml` keeps its bytes

#### Scenario: Remove the skill holding one

- **WHEN** **Entry** `mp/notes` holds U+E0041, nothing else reaches it, and the user runs `skill-graft remove mp/notes`
- **THEN** it succeeds, as the edited config's **Hull** holds no **Hidden character**

### Requirement: Why and tree still show the hull

`why` and `tree` SHALL print what they print for the **Hull** as walked, then report the **Hidden characters** and
Markdown files that are not UTF-8 as `resolve` does and exit 1, so the user sees what pulls a **Skill** holding one into
the **Hull**.

#### Scenario: Why a skill is in the hull

- **WHEN** `mp/deep` holds U+2066 and is reached through `mp/tdd`, and the user runs `skill-graft why mp/deep`
- **THEN** it prints the path from `mp/tdd` to `mp/deep`, reports U+2066 in `mp/deep`, and exits 1
