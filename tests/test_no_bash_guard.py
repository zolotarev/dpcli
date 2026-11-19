"""The shell-edit guard is gone (F-22): blocks cost agents a round each, and Edit needs a full Read first,
so `sed -i` was the cheaper edit. init drops the hook from settings written by older versions."""
import json
import unittest

from helpers import Project


class NoBashGuard(unittest.TestCase):
    def test_init_drops_the_old_hook(self):
        p = Project()
        self.addCleanup(p.cleanup)
        p.ok("init")
        path = p.root / ".claude" / "settings.json"
        st = json.loads(path.read_text())
        st["hooks"].setdefault("PreToolUse", []).append(
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 .dpcli/hooks/bash_guard.py"}]})
        path.write_text(json.dumps(st))
        p.ok("init")
        self.assertNotIn("bash_guard", path.read_text())


if __name__ == "__main__":
    unittest.main()
