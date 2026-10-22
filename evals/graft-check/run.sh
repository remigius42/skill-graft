#!/usr/bin/env bash
# Runs the working copy of graft-check headless on synthetic packages, one per
# scenario, and greps its reports. Opt-in: every scenario costs tokens.
#   run.sh [scenario…]   default: every scenario
set -euo pipefail

scenarios=(defects clean never-built scoped unknown-argument build-fails newer-lock fix)
selected=("$@")
[[ ${#selected[@]} -gt 0 ]] || selected=("${scenarios[@]}")
for name in "${selected[@]}"; do
  if [[ " ${scenarios[*]} " != *" $name "* ]]; then
    echo "run.sh: unknown scenario $name; known: ${scenarios[*]}" >&2
    exit 2
  fi
done

if [[ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" && -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "run.sh: set CLAUDE_CODE_OAUTH_TOKEN (from \`claude setup-token\`) or ANTHROPIC_API_KEY" >&2
  exit 2
fi

repo="$(cd "$(dirname "$0")/../.." && pwd)"
skill_graft="$repo/.venv/bin/skill-graft"
python="$repo/.venv/bin/python"
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
# The working tree's skill-graft, under the name the skill calls. With
# EVAL_LOCK_VERSION set, a throwaway build's lock claims that version.
{
  echo '#!/bin/sh'
  echo "skill_graft='$skill_graft'"
  cat <<'SH'
"$skill_graft" "$@" || exit
[ -n "${EVAL_LOCK_VERSION:-}" ] || exit 0
into=""
previous=""
for argument; do
  case "$argument" in --into=*) into="${argument#--into=}" ;; esac
  [ "$previous" = --into ] && into="$argument"
  previous="$argument"
done
[ -z "$into" ] || sed -i "s/^version = 1\$/version = $EVAL_LOCK_VERSION/" "$into/skill-graft.lock"
SH
} > "$work/bin/skill-graft"
chmod +x "$work/bin/skill-graft"
export PATH="$work/bin:$PATH"

write() { mkdir -p "$(dirname "$1")"; cat > "$1"; }

# A git source at $1: with `defects`, every defect but the wrong target; with
# `clean`, none. Prints the commit.
source_repo() {
  local up="$1"
  if [[ "$2" == defects ]]; then
    write "$up/lead/SKILL.md" <<'MD'
# lead

Plan the change with /code-style in mind, and file leftovers with /follow-up. When the plan is done, run the notes skill to record it.

Fetch the open issues from the tracker's API with `GET /review`, then run /format to format the code.

Answer every follow-up question from the reviewer. See [the checklist](../code-style/checklist.md).
MD
    write "$up/code-style/SKILL.md" <<'MD'
# code-style

The house style for code. Check the service first with `GET /status`.
MD
    write "$up/code-style/checklist.md" <<'MD'
- Names say what a thing is.
MD
    write "$up/follow-up/SKILL.md" <<'MD'
# follow-up

Files an issue for each task left over from a change.
MD
    write "$up/notes/SKILL.md" <<'MD'
# notes

Records a finished plan in the project's notes.
MD
    write "$up/review/SKILL.md" <<'MD'
# review

Reviews a pull request.
MD
  else
    write "$up/lead/SKILL.md" <<'MD'
# lead

Plan the change with /code-style in mind.
MD
    write "$up/code-style/SKILL.md" <<'MD'
# code-style

The house style for code.
MD
  fi
  git -C "$up" init -q -b main
  git -C "$up" add -A
  git -C "$up" commit -q -m skills
  git -C "$up" rev-parse HEAD
}

# The project for scenario $1 at $work/$1, its package holding: with
# `defects`, the defects source prefixed `up-`, a path source `art` whose
# `format` is not what `lead` means by /format, and a user patch of `lead`;
# with `clean`, the clean source; with `missing`, the clean source and an entry
# it lacks. With `built`, built in place first.
project() {
  local dir="$work/$1" kind="$2" built="${3:-}"
  local package="$dir/project/.apm/skill-graft" sha
  sha="$(source_repo "$dir/up" "$([[ $kind == defects ]] && echo defects || echo clean)")"
  if [[ "$kind" == defects ]]; then
    write "$dir/art/format/SKILL.md" <<'MD'
# format

Erases a USB stick and writes a new FAT32 file system to it.
MD
    # A patched line is intended, never a rewrite.
    cp -r "$dir/up/lead" "$dir/base"
    cp -r "$dir/base" "$dir/edited"
    echo "Record each decision in the changelog." >> "$dir/edited/SKILL.md"
    mkdir -p "$package/patches"
    (cd "$dir" && LC_ALL=C diff -ruN base/ edited/ > "$package/patches/lead.patch") || true
    write "$package/skill-graft.toml" <<TOML
entries = ["up/lead"]

[sources.up]
git = "$dir/up"
ref = "$sha"
prefix = "up-"

[sources.art]
path = "$dir/art"

[patches]
"up/lead" = ["patches/lead.patch"]
TOML
  else
    write "$package/skill-graft.toml" <<TOML
entries = ["$([[ $kind == missing ]] && echo up/missing || echo up/lead)"]

[sources.up]
git = "$dir/up"
ref = "$sha"
TOML
  fi
  mkdir -p "$dir/project/.claude/skills"
  cp -r "$repo/skills/graft-check" "$dir/project/.claude/skills/"
  if [[ -n "$built" ]]; then
    (cd "$dir/project" && skill-graft build --no-install)
  fi
  snapshot "$1" > "$dir/before"
}

snapshot() { (cd "$work/$1/project/.apm/skill-graft" && find . -type f -exec sha256sum {} + | sort); }

# Runs claude in scenario $1's project, its reply in $work/$1/$2; the rest are
# claude's arguments. A failing claude fails the scenario, after its output.
ask() {
  local dir="$work/$1" report="$work/$1/$2" code=0
  shift 2
  # --add-dir: the throwaway builds lie under TMPDIR, outside the project.
  (cd "$dir/project" && claude -p "$@" --add-dir "$TMPDIR" \
    --allowedTools "Bash(skill-graft:*)" "Bash(mktemp:*)" "Bash(diff:*)" Read Grep Glob Task Agent) \
    > "$report" || code=$?
  echo "=== $report" >&2
  cat "$report" >&2
  if [[ "$code" != 0 ]]; then
    fail "claude exited $code"
  fi
}

status=0
scenario=""
fail() { echo "run.sh: $scenario: FAILED $1" >&2; status=1; }
pass() { echo "run.sh: $scenario: ok $1" >&2; }
check() {  # <description> <command…>
  local what="$1"
  shift
  if "$@"; then pass "$what"; else fail "$what"; fi
}
report() { cat "$work/$scenario/${1:-report}"; }
# A line naming both: a finding of that kind quoting that text.
# `> /dev/null`, not `-q`: an early exit would SIGPIPE the pipe, which pipefail reports.
found() { report | grep -iF -- "$2" | grep -iF -- "$1" > /dev/null; }
has() { report "${2:-}" | grep -iF -- "$1" > /dev/null; }
lacks() { ! has "$@"; }
# `skill-graft build` advised, not `build --into` narrated.
advises_build() {
  report "${1:-}" | grep -iP 'skill-graft build(?! --into)' | grep -viE "don't|do not|no need|not need" > /dev/null
}
unchanged() { diff <(snapshot "$scenario") "$work/$scenario/before" > /dev/null; }

for scenario in "${selected[@]}"; do
  case "$scenario" in
    defects)
      project defects defects built
      ask defects report "/graft-check"
      check "missed: notes skill" found missed "notes skill"
      check "false: GET /review" found false "GET /review"
      check "wrong target: format" found "wrong target" "format"
      check "rewrite: follow-up question" found rewrite "follow-up question"
      check "link: checklist" found link "checklist"
      check "patched line not a rewrite" eval '! report | grep -i changelog | grep -i rewrite | grep -viE "intended|patch" > /dev/null'
      check "package unchanged" unchanged
      ;;
    clean)
      project clean clean built
      ask clean report "/graft-check"
      check "found nothing" has nothing
      check "no build advice" eval '! advises_build'
      check "package unchanged" unchanged
      ;;
    never-built)
      project never-built clean
      ask never-built report "/graft-check"
      check "build advised" advises_build
      check "package unchanged" unchanged
      ;;
    scoped)
      project scoped defects built
      ask scoped report "/graft-check up/code-style"
      check "false: GET /status" found false "GET /status"
      check "lead not checked" eval 'lacks "notes skill" && lacks "GET /review"'
      check "package unchanged" unchanged
      ;;
    unknown-argument)
      project unknown-argument defects built
      ask unknown-argument report "/graft-check up-lead"
      check "argument named" has "up-lead"
      check "skill IDs listed" has "up/lead"
      check "nothing checked" lacks "GET /review"
      check "package unchanged" unchanged
      ;;
    build-fails)
      project build-fails missing
      ask build-fails report "/graft-check"
      check "build error shown" has "up/missing"
      check "package unchanged" unchanged
      ;;
    newer-lock)
      project newer-lock clean built
      export EVAL_LOCK_VERSION=2
      ask newer-lock report "/graft-check"
      unset EVAL_LOCK_VERSION
      check "update advised" has update
      check "new session advised" has "new session"
      check "package unchanged" unchanged
      ;;
    fix)
      project fix defects built
      ask fix report "/graft-check"
      ask fix reply --continue \
        "Apply only \`skill-graft bind up/review false\`, then finish. Decline every other fix."
      check "up/review left the hull" eval 'has "up/review" reply && has left reply'
      check "build advised" advises_build reply
      check "only that bind written" "$python" -I -c '
import sys, tomllib
from pathlib import Path
package = Path(sys.argv[1])
config = tomllib.loads((package / "skill-graft.toml").read_text())
assert config["bind"] == {"up/review": False}, config
assert config["patches"] == {"up/lead": ["patches/lead.patch"]}, config
assert config["entries"] == ["up/lead"], config
assert [p.name for p in (package / "patches").iterdir()] == ["lead.patch"]
' "$work/fix/project/.apm/skill-graft"
      check "vendored copies unchanged" eval \
        'diff <(snapshot fix | grep " ./.apm/") <(grep " ./.apm/" "$work/fix/before") > /dev/null'
      ;;
  esac
done
exit "$status"
