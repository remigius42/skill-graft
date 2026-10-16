# Renames are declared, patches apply first

A rename is a declared operation (`[rename]` in the TOML) that skill-graft carries into the folder, `name:`, and
every reference, rather than a diff the user writes: a diff touching every reference breaks on each upstream
bump. Content changes are unified diffs against the upstream text, applied before references resolve and
before renames, so a patch never mentions a deployed name and changing a rename never invalidates a patch.
