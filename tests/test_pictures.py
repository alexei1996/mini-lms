import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pictures


class PicturePercentTest(unittest.TestCase):
    def test_empty_without_previous_is_twenty(self):
        self.assertEqual(pictures.picture_percent("", None), 20)
        self.assertEqual(pictures.picture_percent(None, None), 20)
        self.assertEqual(pictures.picture_percent("  ", None), 20)

    def test_bounds_are_kept(self):
        self.assertEqual(pictures.picture_percent(10, None), 10)
        self.assertEqual(pictures.picture_percent("20", 30), 20)
        self.assertEqual(pictures.picture_percent(40, None), 40)

    def test_invalid_keeps_previous_or_twenty(self):
        self.assertEqual(pictures.picture_percent(9, 30), 30)
        self.assertEqual(pictures.picture_percent(41, 30), 30)
        self.assertEqual(pictures.picture_percent(20.5, 30), 30)
        self.assertEqual(pictures.picture_percent("много", 30), 30)
        self.assertEqual(pictures.picture_percent(9, None), 20)
        self.assertEqual(pictures.picture_percent("", 30), 30)


if __name__ == "__main__":
    unittest.main()
