# graft-check's report filter: sh report-filter.sh <mode> <skill id> <name>... < <reply>
# Prints a reader's reply, normalized, when it is in the report shape.

reply=$(mktemp) || exit 2
trap 'rm -f "$reply"' EXIT
LC_ALL=C tr -d '\015' > "$reply" || exit 2

LC_ALL=C awk '
BEGIN {
  for (i = 1; i < ARGC; i++) delete ARGV[i]
  order["finding"] = "skill file text vendored kind why"
  order["use"] = "use file line text means"
}

function close_block(   type, n, keys, i, out) {
  if (!open) return
  type = ("skill" in block) ? "finding" : "use"
  n = split(order[type], keys, " ")
  out = ""
  for (i = 1; i <= n; i++)
    if (keys[i] in block)
      out = out keys[i] ":" (block[keys[i]] == "" ? "" : " " block[keys[i]]) "\n"
  blocks[++count] = out
  split("", block)
  open = 0
}

{ sub(/ +$/, "") }
$0 == "" || $0 == "```" || $0 == "```text" { close_block(); next }
$0 == "findings: none" || $0 == "uses: none" {
  close_block()
  blocks[++count] = $0 "\n"
  next
}
{
  at = index($0, ": ")
  if (at) { key = substr($0, 1, at - 1); value = substr($0, at + 2) }
  else { key = substr($0, 1, length($0) - 1); value = "" }
  block[key] = value
  open = 1
}

END {
  close_block()
  for (i = 1; i <= count; i++) printf "%s%s", (i > 1 ? "\n" : ""), blocks[i]
}
' "$@" < "$reply"
