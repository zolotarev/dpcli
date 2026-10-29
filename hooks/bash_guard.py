#!/usr/bin/env python3
"""Claude Code PreToolUse hook (Bash): refuse editing files through the shell — `sed -i`, `perl -pi`, `cat > file <<`,
`python3 -` scripts that write files. Edit/Write replace exactly and pay only the change; shell edits pay the whole
text in output and break on escaping. Exit 2 = blocked, stderr goes back to the agent. A deliberate bulk edit across
many files passes with the marker `# bulk-edit` in the command."""
import json
import re
import sys

SHELL = [  # matched on the command with quoted strings removed: `git commit -m 'sed -i …'` is not an edit
    (r"\bsed\s+(?:-[a-zA-Z]*i\b|--in-place)", "sed -i"),
    (r"\bperl\s+-[a-zA-Z]*i", "perl -i"),
    (r"\bcat\s*>>?\s*[^\s&|;<>]+\s*<<", "cat > file <<"),
]
SCRIPT = [(r"\bpython3?\s+-\s*<<[\s\S]*?(?:write_text|write_bytes|\.write\(|open\([^)]*['\"][wa]\+?['\"])",
           "python3 - writing files")]


def main():
    try:
        cmd = (json.load(sys.stdin).get("tool_input") or {}).get("command") or ""
    except (ValueError, AttributeError):
        return 0
    if "# bulk-edit" in cmd:
        return 0
    head = re.sub(r"'[^']*'|\"[^\"]*\"", "''", cmd.split("\n", 1)[0])
    hits = [w for rx, w in SHELL if re.search(rx, head)] + [w for rx, w in SCRIPT if re.search(rx, cmd)]
    if not hits:
        return 0
    print(f"dpcli: {hits[0]} edits files through the shell — use the Edit tool (exact replacement) or Write "
          f"(new file); read with Read. The same change across many files: ast-grep run -p … -r … -U, "
          f"or add `# bulk-edit` to the command.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
