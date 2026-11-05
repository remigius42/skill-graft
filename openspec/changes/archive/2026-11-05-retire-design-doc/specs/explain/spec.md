## MODIFIED Requirements

### Requirement: Tree as a mermaid.live link

`tree --format mermaid --link` SHALL print one line: a `https://mermaid.live/edit#pako:` URL whose fragment encodes the
diagram `--format mermaid` prints, in the form mermaid.live reads: a JSON state holding the diagram as `code` and
`"mermaid": "{\"theme\": \"default\"}"`, zlib-deflated, in url-safe base64 without padding. skill-graft SHALL make no
network call for it and open no browser. `--link` without `--format mermaid` SHALL be a usage error.

#### Scenario: Link decodes to the diagram

- **WHEN** the user runs `skill-graft tree --format mermaid --link`
- **THEN** it prints one URL, and decoding its fragment (url-safe base64, then zlib, then JSON) gives a state whose
  `code` equals the output of `skill-graft tree --format mermaid`, whose `mermaid` is `{"theme": "default"}` as JSON,
  and the fragment holds no `=`

#### Scenario: Link without Mermaid

- **WHEN** the user runs `skill-graft tree --link`
- **THEN** it exits 2 naming `--link` and `--format mermaid`
