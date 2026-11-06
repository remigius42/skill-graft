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
shift 2
[ -f "$vet" ] || exit 2
work=$(mktemp -d) || exit 2
trap 'rm -rf "$work"' EXIT
trap 'exit 2' HUP INT TERM
: > "$work/skills" || exit 2 # each folder of <dir>, as a skill ID
: > "$work/pairs" || exit 2  # each reader's skill ID and its reply, sanitized
: > "$work/names" || exit 2  # each file of a skill read: ok or bad, lines, name
dir='' physical=''
if [ $# -ge 1 ]; then
  dir=$1
  shift
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

: > "$report" || exit 2
tab=$(printf '\t')
work=$work dir=$dir physical=$physical report=$report LC_ALL=C awk '
BEGIN {
  work = ENVIRON["work"]; dir = ENVIRON["dir"]; physical = ENVIRON["physical"]
  report = ENVIRON["report"]
  categories = split("read write send run privilege persistence permission unreviewable", c, " ")
  for (i = 1; i <= categories; i++) category[c[i]] = 1
  # Each category`s OWASP IDs, as `pipeline/vet.py` gives them: for a reader`s
  # own flag only; a scan flag keeps those its `vet` line printed.
  owasp["read"] = "LLM02"
  owasp["write"] = "ASI02"
  owasp["send"] = "LLM02,ASI02"
  owasp["run"] = "ASI05"
  owasp["privilege"] = "ASI03"
  owasp["persistence"] = "ASI06"
  owasp["permission"] = "ASI02"
  owasp["unreviewable"] = "LLM03"
  while ((getline line < (work "/names")) > 0) {
    split(line, f, " ")
    key = f[1] SUBSEP f[4]
    if (key in lines || f[2] == "bad") bad[key] = 1
    lines[key] = f[3]
  }
  while ((getline line < (work "/skills")) > 0) folders[++folder_count] = line
  while ((getline line < (work "/pairs")) > 0) {
    # The reply`s path, under $TMPDIR, may hold spaces; a skill ID never does.
    at = index(line, " ")
    pairs[++pair_count] = substr(line, 1, at - 1)
    read_reply(substr(line, 1, at - 1), substr(line, at + 1))
  }
}

# A line of `vet`: `<skill id> <file>:<line> <category> <owasp ids> <pattern>`.
NF != 5 || !match($2, /:[0-9]+$/) { failed = 1; exit }
{
  add($1)
  scan[$1, substr($2, 1, RSTART - 1), substr($2, RSTART + 1), $3, $5] = $4
}

# Adds `id` to the skills, in the order first seen.
function add(id) { if (!(id in known)) { known[id] = 1; order[++skills] = id } }

# Keeps each line of a reply that is a place of skill `id`; drops and counts the rest.
function read_reply(id, file,   line, prefix, real) {
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
    if (at_line > 0) { answered[id, at_file, at_category] = 1; answered_line[id, at_file, at_line] = 1 }
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

# One flag of the report: its sort key, by skill, file, line, category and
# pattern, then its line; counted in the summary.
function emit(id, file, line, cat, ids, seen, pattern) {
  printf "%d\t%s\t%d\t%s\t%s\t%s %s:%s %s %s %s%s\n", rank[id], file, line, cat, \
    pattern, id, file, line, cat, ids, seen, (pattern == "" ? "" : " " pattern) \
    > (work "/flags")
  count[id, cat, seen]++
  total++
}

END {
  if (failed) exit 2
  for (i = 1; i <= pair_count; i++) add(pairs[i])
  for (i = 1; i <= folder_count; i++) add(folders[i])
  for (i = 1; i <= skills; i++) rank[order[i]] = i
  summary = work "/summary"
  # The steering count: each file, line and category of the scan, line 0 aside,
  # in a file where the reply flagged that category at no line above 0, and that
  # line in no category: a reader flagging the line disagrees, it is not silent.
  # A failed reader counts as one that replied `none`.
  for (key in scan) {
    split(key, f, SUBSEP)
    if (f[3] > 0 && !((f[1], f[2], f[4]) in answered) && !((f[1], f[2], f[3]) in answered_line) \
        && !((f[1], f[2], f[3], f[4]) in unanswered)) {
      unanswered[f[1], f[2], f[3], f[4]] = 1
      steering[f[1]]++
    }
  }
  if (dir != "")
    for (i = 1; i <= skills; i++) {
      id = order[i]
      if (id in replied) status = id " steering " (steering[id] + 0) " dropped " dropped[id]
      else status = id " no-reply steering " (steering[id] + 0)
      print status >> report
      print status > summary
    }
  for (key in scan) {
    split(key, f, SUBSEP)
    both = (f[1], f[2], f[3], f[4]) in flag
    if (both) matched[f[1], f[2], f[3], f[4]] = 1
    emit(f[1], f[2], f[3], f[4], scan[key], both ? "both" : "scan", f[5])
  }
  for (key in flag) {
    if (key in matched) continue
    split(key, f, SUBSEP)
    emit(f[1], f[2], f[3], f[4], owasp[f[4]], "reader", "")
  }
  for (i = 1; i <= skills; i++)
    for (j = 1; j <= categories; j++) {
      id = order[i]; cat = c[j]
      if (count[id, cat, "scan"] + count[id, cat, "reader"] + count[id, cat, "both"])
        printf "%s %s scan %d reader %d both %d\n", id, cat, count[id, cat, "scan"], \
          count[id, cat, "reader"], count[id, cat, "both"] > summary
    }
  print "flags " (total + 0) > summary
}' "$vet" || exit 2
touch "$work/flags" || exit 2
# By skill as ranked, then file, line, category and pattern.
LC_ALL=C sort -t "$tab" -k1,1n -k2,2 -k3,3n -k4,4 -k5,5 "$work/flags" > "$work/sorted" || exit 2
cut -f 6 "$work/sorted" >> "$report" || exit 2
cat "$work/summary" || exit 2
