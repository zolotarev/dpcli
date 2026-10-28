"""gc: a merged copy that another copy links into is skipped; the scan is one git status per copy."""
import os
import unittest

from helpers import Project, git


class Gc(unittest.TestCase):
    def test_symlinked_copy_skipped(self):
        p = Project()
        self.addCleanup(p.cleanup)
        r = p.root
        (r / ".gitignore").write_text("node_modules/\n")
        p.commit_all("ignore")
        a, b = p.copies / "a", p.copies / "b"
        for name, path in (("ta", a), ("tb", b)):
            git("worktree", "add", "-q", "-b", name, str(path), "main", cwd=r)
            (path / f"{name}.txt").write_text(name)
            git("add", f"{name}.txt", cwd=path)
            git("commit", "-q", "-m", name, cwd=path)
            git("merge", "-q", "--no-ff", "-m", f"m {name}", name, cwd=r)
        (a / "node_modules").mkdir()
        os.symlink(a / "node_modules", b / "node_modules")
        out = p.ok("gc")
        self.assertRegex(out, r"skip ta .*symlinks from other copies")
        self.assertIn("tb @", out)


if __name__ == "__main__":
    unittest.main()
