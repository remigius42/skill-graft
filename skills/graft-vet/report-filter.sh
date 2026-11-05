# graft-vet's report filter:
#   sh report-filter.sh <vet output> <report file> [<dir> [<skill id> <reader out>]...]
# Merges `skill-graft vet`'s flags with each reader's reply into the report file,
# one line per flag, and prints only numbers. A reply line naming no file and line
# of its skill, in the reply shape, is dropped and counted: no word of a reply but
# a place its skill already has reaches the report. Exits 0 with the report file
# written, 2 when the filter itself fails.

case $# in
  0 | 1) exit 2 ;;
  2) ;;
  *) [ $((($# - 3) % 2)) -eq 0 ] || exit 2 ;;
esac
vet=$1 report=$2
[ -f "$vet" ] || exit 2
work=$(mktemp -d) || exit 2
trap 'rm -rf "$work"' EXIT
trap 'exit 2' HUP INT TERM
: > "$work/skills" || exit 2 # each folder of <dir>, as a skill ID
: > "$work/pairs" || exit 2  # each reader's skill ID and its reply, sanitized
: > "$work/names" || exit 2  # each file of a skill read: ok or bad, lines, name
dir='' physical=''
if [ $# -ge 3 ]; then
  dir=$3
  shift 3
  # As it really is, every link resolved: a reader's tools may name it so.
  physical=$(cd "$dir" && pwd -P) || exit 2
  for folder in "$dir"/*/*; do
    [ -d "$folder" ] || continue
    printf '%s\n' "${folder#"$dir"/}" >> "$work/skills" || exit 2
  done
fi
n=0 given=" "
while [ $# -gt 0 ]; do
  id=$1 out=$2
  shift 2
  # A skill ID: two parts of [A-Za-z0-9._-], neither `.` nor `..`.
  case $id in
    *[!A-Za-z0-9._/-]* | */*/* | /* | */ | ./* | ../* | */. | */..) exit 2 ;;
    ?*/?*) ;;
    *) exit 2 ;;
  esac
  # A reader runs once: a second reply for a skill is no reply to merge.
  case $given in *" $id "*) exit 2 ;; esac
  given="$given$id "
  n=$((n + 1))
  # Carriage returns and UTF-8 continuation bytes go; every other byte outside
  # printable ASCII and the line break, a UTF-8 lead byte included, becomes `?`.
  LC_ALL=C tr -d '\015\200-\277' < "$out" > "$work/dropped" || exit 2
  LC_ALL=C tr -c '\n -~' '[?*]' < "$work/dropped" > "$work/reply$n" || exit 2
  printf '%s %s\n' "$id" "$work/reply$n" >> "$work/pairs" || exit 2
  [ -d "$dir/$id" ] || continue
  # Each regular file: `bad` when its name holds a control character, which a
  # listing a line per name would split, or is no UTF-8, which `vet` maps a `?`
  # per byte; its line count, as awk counts them; its name mapped as `vet` maps it.
  LC_ALL=C find "$dir/$id" -type f -exec sh -c '
    root=$1 id=$2
    shift 2
    for file; do
      name=${file#"$root"/} state=ok
      case $name in *[[:cntrl:]]*) state=bad ;; esac
      printf %s "$name" | iconv -f UTF-8 -t UTF-8 > /dev/null 2>&1 || state=bad
      lines=$(awk "END { print NR }" "$file") || exit 1
      mapped=$(printf %s "$name" | tr -d "\200-\277" | tr -c "!-~" "[?*]") || exit 1
      printf "%s %s %s %s\n" "$id" "$state" "$lines" "$mapped"
    done' sh "$dir/$id" "$id" {} + >> "$work/names" || exit 2
done

work=$work dir=$dir physical=$physical report=$report LC_ALL=C awk '
BEGIN {
  work = ENVIRON["work"]; dir = ENVIRON["dir"]; physical = ENVIRON["physical"]
  report = ENVIRON["report"]
  split("read write send run privilege persistence permission unreviewable", c, " ")
  for (i in c) category[c[i]] = 1
  while ((getline line < (work "/names")) > 0) {
    split(line, f, " ")
    key = f[1] SUBSEP f[4]
    if (key in lines || f[2] == "bad") bad[key] = 1
    lines[key] = f[3]
  }
  while ((getline line < (work "/skills")) > 0) add(line)
  while ((getline line < (work "/pairs")) > 0) {
    # The reply`s path, under $TMPDIR, may hold spaces; a skill ID never does.
    at = index(line, " ")
    read_reply(substr(line, 1, at - 1), substr(line, at + 1))
  }
}

# Adds `id` to the skills, in the order first seen.
function add(id) { if (!(id in known)) { known[id] = 1; order[++skills] = id } }

# Keeps each line of a reply that is a place of skill `id`; drops and counts the rest.
function read_reply(id, file,   line, prefix, real) {
  add(id)
  replied[id] = 1
  dropped[id] += 0
  prefix = dir "/" id "/"
  real = physical "/" id "/"
  while ((getline line < file) > 0) {
    sub(/ +$/, "", line)
    if (line == "" || line == "```" || line == "```text" || line == "none") continue
    if (index(line, prefix) == 1) line = substr(line, length(prefix) + 1)
    else if (index(line, real) == 1) line = substr(line, length(real) + 1)
    else if (substr(line, 1, 2) == "./") line = substr(line, 3)
    if (!place(id, line) || ++kept[id] > 1000) { dropped[id]++; continue }
    flag[id, at_file, at_line, at_category] = 1
  }
  close(file)
}

# Whether `line` is `<file>:<line> <category>`, its file one of skill `id`s names,
# each space as `?`, and its line within that file; sets at_file, at_line and
# at_category.
function place(id, line,   rest, key) {
  if (!match(line, / [^ ]*$/)) return 0
  at_category = substr(line, RSTART + 1)
  rest = substr(line, 1, RSTART - 1)
  if (!(at_category in category) || !match(rest, /:[^:]*$/)) return 0
  at_line = substr(rest, RSTART + 1)
  at_file = substr(rest, 1, RSTART - 1)
  if (at_line !~ /^(0|[1-9][0-9]*)$/ || length(at_line) > 6) return 0
  gsub(/ /, "?", at_file)
  key = id SUBSEP at_file
  return at_file != "" && key in lines && !(key in bad) && at_line + 0 <= lines[key]
}

END {
  for (i = 1; i <= skills; i++) {
    id = order[i]
    if (id in replied) print id " steering 0 dropped " dropped[id] > report
    else print id " no-reply steering 0" > report
  }
  for (key in flag) {
    split(key, f, SUBSEP)
    print f[1] " " f[2] ":" f[3] " " f[4] > report
  }
}' "$vet" || exit 2
