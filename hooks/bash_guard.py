#!/usr/bin/env python3
"""Claude Code PreToolUse hook (Bash): refuse editing project files through the shell — `sed -i`, `perl -i`,
`cat > file <<`, `python3 -` heredocs that write files. Edit/Write replace exactly and pay only the change; shell
edits pay the whole text in output and break on escaping. Exit 2 = blocked, stderr goes back to the agent.
Allowed: temporary files (/tmp, $TMPDIR, /dev). Not covered on purpose: `echo/printf/tee > file` (small writes);
a multi-line quoted string whose line starts like an edit is a known false positive."""
import json
import re
import sys

TEMP = ("/tmp/", "$TMPDIR", "${TMPDIR", "/dev/")
SHELL = [  # on every command line outside heredoc bodies, quoted strings removed; -i anywhere in the arguments
    (r"\bsed\b[^|;&]*?\s(?:-[a-zA-Z]*i\b|--in-place)", "sed -i"),
    (r"\bperl\b[^|;&]*?\s-[a-zA-Z]*i", "perl -i"),
    (r"\bcat\s*>>?\s*([^\s&|;<>]+)\s*<<", "cat > file <<"),
]
PY_HEREDOC = re.compile(r"\bpython3?\s+-\s*<<")
PY_WRITES = re.compile(r"\.write_(?:text|bytes)\(|\bopen\([^)]*['\"][wax]b?\+?['\"]")


def split(cmd):
    """(command lines with quoted strings removed, heredoc bodies)."""
    lines, bodies, end = [], [], None
    for raw in cmd.split("\n"):
        if end is not None:
            if raw.strip() == end:
                end = None
            else:
                bodies.append(raw)
            continue
        m = re.search(r"(?<!<)<<(?!<)-?\s*['\"]?([A-Za-z_]\w*)", re.sub(r"'(\w+)'|\"(\w+)\"", r"\1\2", raw))
        bare = re.sub(r"'[^']*'|\"[^\"]*\"", "''", raw)  # quoted text removed: `git commit -m 'sed -i …'`
        lines.append(re.sub(r"'[^']*\s[^']*'|\"[^\"]*\s[^\"]*\"", "''", raw).replace('"', "").replace("'", ""))
        if m and re.search(r"(?<!<)<<(?!<)", bare):  # a heredoc opened outside quotes (`'EOF'` delimiters are fine)
            end = m[1]
    return lines, "\n".join(bodies)


def edits(ln):
    for rx, what in SHELL:
        m = re.search(rx, ln)
        if not m:
            continue
        target = m.group(1) if m.groups() else (ln[m.end():].split() or [""])[-1]
        if not target.startswith(TEMP):  # temporary files are not project files
            return what
    return None


def main():
    try:
        cmd = (json.load(sys.stdin).get("tool_input") or {}).get("command") or ""
    except (ValueError, AttributeError):
        return 0
    lines, body = split(cmd)
    hits = [w for w in map(edits, lines) if w]
    if any(PY_HEREDOC.search(ln) for ln in lines) and PY_WRITES.search(body):
        hits.append("python3 - writing files")
    if not hits:
        return 0
    print(f"dpcli: {hits[0]} edits project files through the shell — use the Edit tool (exact replacement) or Write "
          f"(new file); read with Read. Temporary files (/tmp, $TMPDIR) are fine.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
