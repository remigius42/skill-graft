#!/usr/bin/env bash
# Runs the working copy of graft-check headless on a synthetic package with one
# planted defect per kind, and greps its report for each. Opt-in: it costs tokens.
set -euo pipefail

if [[ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" && -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "run.sh: set CLAUDE_CODE_OAUTH_TOKEN (from \`claude setup-token\`) or ANTHROPIC_API_KEY" >&2
  exit 2
fi

repo="$(cd "$(dirname "$0")/../.." && pwd)"
skill_graft="$repo/.venv/bin/skill-graft"
if [[ ! -x "$skill_graft" ]]; then
  echo "run.sh: $skill_graft is missing; run \`uv sync\` in $repo" >&2
  exit 2
fi

work="$(mktemp -d)"
echo "run.sh: working in $work" >&2
# The real ~/.claude, ~/.apm and ~/.cache stay out of reach: no user settings,
# hooks or deployed skills change the run, and nothing it does lands there.
export HOME="$work/home" XDG_CACHE_HOME="$work/cache" TMPDIR="$work/tmp"
mkdir -p "$HOME" "$XDG_CACHE_HOME" "$TMPDIR" "$work/bin"
export GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME=eval GIT_AUTHOR_EMAIL=eval@example.com
export GIT_COMMITTER_NAME=eval GIT_COMMITTER_EMAIL=eval@example.com
# The working tree's skill-graft, under the name the skill calls.
printf '#!/bin/sh\nexec "%s" "$@"\n' "$skill_graft" > "$work/bin/skill-graft"
chmod +x "$work/bin/skill-graft"
export PATH="$work/bin:$PATH"

write() { mkdir -p "$(dirname "$1")"; cat > "$1"; }

# A git source, prefixed `up-`, holding every defect but the wrong target.
up="$work/up"
write "$up/lead/SKILL.md" <<'MD'
# lead

Plan the change with /code-style in mind. When the plan is done, run the notes skill to record it.

Fetch the open issues from the tracker's API with `GET /review`, then run /format to format the code.

Keep the code-style consistent across files. See [the checklist](../code-style/checklist.md).
MD
write "$up/code-style/SKILL.md" <<'MD'
# code-style

The house style for code.
MD
write "$up/code-style/checklist.md" <<'MD'
- Names say what a thing is.
MD
write "$up/notes/SKILL.md" <<'MD'
# notes

Records a finished plan in the project's notes.
MD
write "$up/review/SKILL.md" <<'MD'
# review

Reviews a pull request.
MD
git -C "$up" init -q -b main
git -C "$up" add -A
git -C "$up" commit -q -m skills
sha="$(git -C "$up" rev-parse HEAD)"

# A path source whose `format` is not what `lead` means by /format.
write "$work/art/format/SKILL.md" <<'MD'
# format

Erases a USB stick and writes a new FAT32 file system to it.
MD

project="$work/project"
package="$project/.apm/skill-graft"
write "$package/skill-graft.toml" <<TOML
entries = ["up/lead"]

[sources.up]
git = "$up"
ref = "$sha"
prefix = "up-"

[sources.art]
path = "$work/art"
TOML
mkdir -p "$project/.claude/skills"
cp -r "$repo/skills/graft-check" "$project/.claude/skills/"

cd "$project"
skill-graft build --no-install
snapshot() { (cd "$package" && find . -type f -exec sha256sum {} + | sort); }
before="$(snapshot)"

report="$work/report.md"
claude -p "/graft-check" \
  --allowedTools "Bash(skill-graft:*)" "Bash(mktemp:*)" "Bash(diff:*)" Read Grep Glob Task Agent \
  > "$report"
cat "$report"

status=0
check() {  # <kind> <text the finding quotes>: both in the report
  if grep -qiF -- "$2" "$report" && grep -qiF -- "$1" "$report"; then
    echo "run.sh: found $1 ($2)" >&2
  else
    echo "run.sh: MISSING $1 ($2)" >&2
    status=1
  fi
}
check missed "notes skill"
check false "GET /review"
check "wrong target" "format"
check rewrite "consistent"
check link "checklist"
if [[ "$(snapshot)" != "$before" ]]; then
  echo "run.sh: the eval package changed" >&2
  status=1
fi
exit "$status"
