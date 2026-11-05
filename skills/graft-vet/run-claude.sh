# graft-check's claude runner:
#   sh run-claude.sh reader <folder> <files> <turns> <budget-usd> <add-dir>...
#   sh run-claude.sh patcher <folder> <files> <turns> <budget-usd>
# Runs `claude -p` as that agent, defined in this script's folder, from <folder>,
# <files>/prompt on its stdin, its stdout in <files>/out and its stderr in
# <files>/err; exits as claude does, or 2 when it refuses its arguments. It sets
# every confining flag itself and runs only in a temporary folder, so a permission
# rule admitting it admits no other claude than a reader of the folders it names
# or a patcher in a temporary folder. It also holds the cd and the output files,
# which Claude Code's Bash guard refuses in one command.

# A folder as it really is, every link and `..` resolved; nothing if it is none.
real() { (cd "$1" 2> /dev/null && pwd -P); }
tmp=$(real "${TMPDIR:-/tmp}")
# None: every absolute path would pass for one under it.
[ -n "$tmp" ] || { echo "run-claude.sh: \$TMPDIR is no folder: ${TMPDIR:-/tmp}" >&2; exit 2; }
# A temporary folder: really under $TMPDIR, so no link leads out of it.
temporary() {
  case $1 in
    "$tmp"/?*) return 0 ;;
    *) return 1 ;;
  esac
}
files=$(real "$3")
temporary "$files" || { echo "run-claude.sh: <files> must be a folder under $tmp" >&2; exit 2; }
# Out and err first, so every later failure lands in err.
exec > "$files/out" 2> "$files/err" || exit 2

refuse() { echo "run-claude.sh: $1" >&2; exit 2; }
[ $# -ge 5 ] || refuse "takes a role, a folder, a files folder and two caps"
role=$1 turns=$4 budget=$5
folder=$(real "$2")
temporary "$folder" || refuse "the folder must be under $tmp: $2"
shift 5
case $role in
  reader) ;;
  patcher) [ $# -eq 0 ] || refuse "a patcher takes no --add-dir" ;;
  *) refuse "unknown role: $role" ;;
esac
case $turns in
  '' | *[!0-9]*) refuse "turns must be a whole number" ;;
esac
case $budget in
  '' | *[!0-9.]* | .* | *. | *.*.*) refuse "the budget must be a number of dollars" ;;
esac
# Absolute paths only: no value may pass for a claude option.
for path; do
  case $path in
    /*) ;;
    *) refuse "not an absolute path: $path" ;;
  esac
done
agents="$(cd "$(dirname "$0")" && pwd -P)/$role.json" || refuse "cannot find $role.json"
n=$#
for dir; do set -- "$@" --add-dir "$dir"; done
shift "$n"

exec < "$files/prompt" || exit 2
cd "$folder" || exit 2
if [ "$role" = reader ]; then
  exec claude -p --max-turns "$turns" --max-budget-usd "$budget" --restricted --strict-mcp-config \
    --tools Read,Grep,Glob --agents "$agents" --agent reader "$@"
fi
exec claude -p --max-turns "$turns" --max-budget-usd "$budget" --restricted --strict-mcp-config \
  --tools Read,Edit,Write --permission-mode acceptEdits --agents "$agents" --agent patcher
