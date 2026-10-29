#!/usr/bin/env python3
"""Claude Code PreToolUse hook (Bash): refuse editing files through the shell — `sed -i`, `perl -i`, `cat > file <<`,
`python3 -` heredocs that write files. Edit/Write replace exactly and pay only the change; shell edits pay the whole
text in output and break on escaping. Exit 2 = blocked, stderr goes back to the agent.
Not covered on purpose: `echo/printf/tee > file` (small writes)."""
import json
import re
import sys

SHELL = [  # matched on every command line outside heredoc bodies, quoted strings removed
    (r"\bsed\s+(?:-[a-zA-Z]*i\b|--in-place)", "sed -i"),
    (r"\bperl\s+-[a-zA-Z]*i", "perl -i"),
    (r"\bcat\s*>>?\s*[^\s&|;<>]+\s*<<", "cat > file <<"),
]
PY_HEREDOC = re.compile(r"\bpython3?\s+-\s*<<")
PY_WRITES = re.compile(r"\.write_(?:text|bytes)\(|\bopen\([^)]*['\"][wax]b?\+?['\"]")


def split(cmd):
    """(command lines, heredoc bodies)."""
    lines, bodies, end = [], [], None
    for ln in cmd.split("\n"):
        if end is not None:
            if ln.strip() == end:
                end = None
            else:
                bodies.append(ln)
            continue
        lines.append(re.sub(r"'[^']*'|\"[^\"]*\"", "''", ln))
        m = re.search(r"<<-?\s*['\"]?(\w+)", ln)
        if m:
            end = m[1]
    return lines, "\n".join(bodies)


def main():
    try:
        cmd = (json.load(sys.stdin).get("tool_input") or {}).get("command") or ""
    except (ValueError, AttributeError):
        return 0
    lines, body = split(cmd)
    hits = [w for rx, w in SHELL for ln in lines if re.search(rx, ln)]
    if any(PY_HEREDOC.search(ln) for ln in lines) and PY_WRITES.search(body):
        hits.append("python3 - writing files")
    if not hits:
        return 0
    print(f"dpcli: {hits[0]} edits files through the shell — use the Edit tool (exact replacement) or Write "
          f"(new file); read with Read. The same change in many files: Edit per file, or ast-grep run -p … -r … -U.",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
