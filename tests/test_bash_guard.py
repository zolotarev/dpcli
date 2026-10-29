"""PreToolUse hook: file edits through Bash are refused with a pointer to Edit/Write; programs and reads pass."""
import json
import subprocess
import sys
import unittest

from helpers import DIST, Project

GUARD = DIST / "hooks" / "bash_guard.py"


def run(cmd):
    r = subprocess.run([sys.executable, str(GUARD)], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}),
                       capture_output=True, text=True)
    return r.returncode, r.stderr


class BashGuard(unittest.TestCase):
    def test_blocks_shell_edits(self):
        for cmd in ("sed -i 's/a/b/' src/x.ts", "sed -Ei.bak 's/a/b/' f", "perl -pi -e 's/a/b/' f",
                    "cat > src/x.ts <<'EOF'\nx\nEOF", "python3 - <<'EOF'\nfrom pathlib import Path\nPath('a').write_text('x')\nEOF",
                    "python3 - <<'EOF'\nopen('a', 'w').write('x')\nEOF"):
            code, err = run(cmd)
            self.assertEqual(code, 2, cmd)
            self.assertIn("Edit", err)

    def test_allows_programs_reads_and_marked_bulk_edits(self):
        for cmd in ("rg -n foo src", "sed -n '1,20p' f", "python3 - <<'EOF'\nprint(1)\nEOF", "cat f | jq .",
                    "pnpm exec vitest run", ".dpcli/dpcli review X --from - <<'JSON'\n{}\nJSON",
                    "sed -i 's/a/b/' $(rg -l a)  # bulk-edit", "git commit -m 'sed -i is gone'"):
            self.assertEqual(run(cmd)[0], 0, cmd)

    def test_init_installs_the_hook_once(self):
        p = Project()
        self.addCleanup(p.cleanup)
        p.ok("init")
        p.ok("init")
        st = json.loads((p.root / ".claude" / "settings.json").read_text())
        pre = [h["command"] for e in st["hooks"]["PreToolUse"] if e.get("matcher") == "Bash" for h in e["hooks"]]
        self.assertEqual(sum("bash_guard.py" in c for c in pre), 1)


if __name__ == "__main__":
    unittest.main()
