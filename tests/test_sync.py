"""tools/sync.py and tools/metrics.py: the CI merges main into a PR and never raises budgets on its own."""
import sys
import unittest

from helpers import REPO

sys.path.insert(0, str(REPO / "tools"))
import metrics  # noqa: E402
import sync  # noqa: E402

BASE = "# Changelog\n\n## 29\n- old.\n"
MAIN = "# Changelog\n\n## 31\n- b.\n\n## 30\n- a.\n\n## 29\n- old.\n"
PR = "# Changelog\n\n## 30\n- mine.\n\n## 29\n- old.\n"


class Sync(unittest.TestCase):
    def test_pr_section_goes_on_top_of_main_renumbered(self):
        self.assertEqual(sync.changelog(MAIN, BASE, PR, 32),
                         "# Changelog\n\n## 32\n- mine.\n\n## 31\n- b.\n\n## 30\n- a.\n\n## 29\n- old.\n")

    def test_no_own_section_keeps_main(self):
        self.assertEqual(sync.changelog(MAIN, BASE, BASE, 32), MAIN)

    def test_version_bump_keeps_the_comment(self):
        self.assertEqual(sync.bumped("x\nVERSION = 31  # bump\n", 32), "x\nVERSION = 32  # bump\n")

    def test_write_budgets_never_raises(self):
        m = {"code_lines": 10, "prompt_tokens": 5, "prompt_max": 3, "duplicate_windows": 0, "risky": {"push": 5, "new": 1}}
        b = {"code_lines": 8, "prompt_tokens": 9, "prompt_max": 3, "duplicate_windows": 0, "risky": {"push": 4}}
        self.assertEqual(metrics.lowered(m, b), {"code_lines": 8, "prompt_tokens": 5, "prompt_max": 3,
                                                 "duplicate_windows": 0, "risky": {"push": 4, "new": 1}})


if __name__ == "__main__":
    unittest.main()
