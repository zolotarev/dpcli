import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from dpcli.util import append_jsonl, read_jsonl  # noqa: E402


class AppendJsonl(unittest.TestCase):
    def test_after_torn_write_next_record_stays_valid(self):
        # a write cut short (disk full) leaves a line without "\n"; the next record must not glue onto it
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "events.jsonl"
            p.write_text('{"a": 1}\n{"t": "x", "ev"')
            append_jsonl(p, {"b": 2})
            self.assertEqual(read_jsonl(p), [{"a": 1}, {"b": 2}])


if __name__ == "__main__":
    unittest.main()
