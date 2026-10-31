# graft-check's report filter: sh report-filter.sh <mode> <skill id> <name>... < <reply>
# Prints a reader's reply, normalized, and exits 0 when it is in the report shape;
# prints nothing and exits 1 when it is not; exits 2 when the filter itself fails.

case $1 in
  full | uses) ;;
  *) exit 2 ;;
esac

trap 'rm -f "$dropped" "$reply"' EXIT
trap 'exit 2' HUP INT TERM
dropped=$(mktemp) || exit 2
reply=$(mktemp) || exit 2
# Carriage returns and UTF-8 continuation bytes go; every other byte outside
# printable ASCII and the line break, a UTF-8 lead byte included, becomes `?`.
LC_ALL=C tr -d '\015\200-\277' > "$dropped" || exit 2
LC_ALL=C tr -c '\n -~' '[?*]' < "$dropped" > "$reply" || exit 2

LC_ALL=C awk '
BEGIN {
  mode = "" ARGV[1]; skill = "" ARGV[2]
  for (i = 3; i < ARGC; i++) names["" ARGV[i]] = 1
  for (i = 1; i < ARGC; i++) delete ARGV[i]
  order["finding"] = "skill file text vendored kind why"
  order["use"] = "use file line text means"
  for (type in order) {
    n = split(order[type], k, " ")
    for (i = 1; i <= n; i++) { allowed[type, k[i]] = 1; known[k[i]] = 1 }
  }
  kinds["missed"] = 1
  kinds["false"] = 1
  kinds["rewrite"] = 1
  kinds["link"] = 1
  kinds["wrong target"] = 1
  # What may come next: "findings" (a finding or findings: none), "more findings"
  # (a finding, a use or uses: none), "uses" (a use or uses: none), "more uses", "".
  next_up = (mode == "full") ? "findings" : "uses"
}

function refuse() { refused = 1; exit 3 }

function valid(key, value) {
  if (!(key in known)) return 0
  if (value == "") return key == "text" || key == "vendored"
  if (key == "skill") return value == skill
  if (key == "use") return value in names
  if (key == "kind") return value in kinds
  if (key == "line") return value ~ /^[1-9][0-9]*$/ && length(value) <= 6
  if (key == "means")
    return value == "none" || \
      (value ~ /^[A-Za-z0-9][A-Za-z0-9._-]*\/[A-Za-z0-9][A-Za-z0-9._-]*$/ && \
       length(value) <= 200)
  return 1
}

# Admits a block of the type "finding", "use", "findings: none" or "uses: none".
function admit(type, out) {
  if (type == "finding" && (next_up == "findings" || next_up == "more findings")) {
    if (++findings > 100) refuse()
    next_up = "more findings"
  } else if (type == "use" && next_up != "findings" && next_up != "") {
    if (++uses > 200) refuse()
    next_up = "more uses"
  } else if (type == "findings: none" && next_up == "findings") next_up = "uses"
  else if (type == "uses: none" && (next_up == "more findings" || next_up == "uses"))
    next_up = ""
  else refuse()
  blocks[++count] = out
}

function close_block(   type, n, keys, i, out) {
  if (!open) return
  type = ("skill" in block) ? "finding" : "use"
  for (i in block) if (!((type, i) in allowed)) refuse()
  n = split(order[type], keys, " ")
  out = ""
  for (i = 1; i <= n; i++)
    if (keys[i] in block)
      out = out keys[i] ":" (block[keys[i]] == "" ? "" : " " block[keys[i]]) "\n"
  if (!("file" in block && "text" in block)) refuse()
  if (type == "finding" && !("kind" in block && "why" in block)) refuse()
  if (type == "use" && !("use" in block && "line" in block && "means" in block)) refuse()
  admit(type, out)
  split("", block)
  open = 0
}

{ sub(/ +$/, "") }
$0 == "" || $0 == "```" || $0 == "```text" { close_block(); next }
$0 == "findings: none" || $0 == "uses: none" {
  if (open) refuse()
  admit($0, $0 "\n")
  next
}
{
  at = index($0, ": ")
  if (at) { key = substr($0, 1, at - 1); value = substr($0, at + 2) }
  else if ($0 ~ /^[a-z]+:$/) { key = substr($0, 1, length($0) - 1); value = "" }
  else refuse()
  # A use written in its slash form, `/<name>`, is that name.
  if (key == "use" && value ~ /^\/[^\/]/) value = substr(value, 2)
  if (key in block || !valid(key, value)) refuse()
  if (key ~ /^(file|text|vendored|why)$/ && length(value) > 200)
    value = substr(value, 1, 197) "..."
  block[key] = value
  open = 1
}

END {
  if (refused) exit 3
  close_block()
  if (next_up != "" && next_up != "more uses") exit 3
  for (i = 1; i <= count; i++) printf "%s%s", (i > 1 ? "\n" : ""), blocks[i]
}
' "$@" < "$reply"

case $? in
  0) exit 0 ;;
  3) exit 1 ;;
  *) exit 2 ;;
esac
