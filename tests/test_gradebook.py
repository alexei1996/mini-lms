import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import gradebook


def sample_test():
    return {
        "id": "t1",
        "title": "Тема 1",
        "allowRetake": True,
        "gradePublishedOn": "2026-11-23",
        "questions": [{
            "id": "q1",
            "prompt": [{"type": "text", "text": "Вопрос"}],
            "image": "",
            "options": [
                {"id": "a", "text": "один", "image": "", "correct": True},
                {"id": "b", "text": "два", "image": "pic.png", "correct": False},
            ],
        }],
    }


class GradebookTest(unittest.TestCase):
    def test_payload_has_the_four_facts_and_no_clock(self):
        payload = gradebook.grade_payload("Курс", sample_test(), "  Анна   Иванова ", 7)
        self.assertEqual(payload["name"], "Анна Иванова")
        self.assertEqual(payload["score"], 7)
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["courseTitle"], "Курс")
        self.assertEqual(payload["testTitle"], "Тема 1")
        self.assertEqual(payload["publishedOn"], "2026-11-23")
        self.assertNotIn("date", payload)
        self.assertNotIn("number", payload)

    def test_empty_name_is_rejected(self):
        with self.assertRaises(gradebook.GradeError) as caught:
            gradebook.grade_payload("Курс", sample_test(), "   ", 0)
        self.assertEqual(caught.exception.code, "identity")

    def test_same_questions_keep_the_sheet_and_retake_switch_does_not(self):
        original = sample_test()
        again = sample_test()
        again["allowRetake"] = False
        self.assertTrue(gradebook.continues_sheet(original, again))
        renamed = sample_test()
        renamed["title"] = "Тема 2"
        self.assertFalse(gradebook.continues_sheet(original, renamed))
        edited = sample_test()
        edited["questions"][0]["options"][0]["correct"] = False
        edited["questions"][0]["options"][1]["correct"] = True
        self.assertFalse(gradebook.continues_sheet(original, edited))

    def test_first_row_creates_the_sheet_and_the_header(self):
        test = sample_test()
        payload = gradebook.grade_payload("Химия", test, "Анна", 1)
        book = {}
        result = gradebook.append_grade(book, payload, "23.11.2026 10:00")
        self.assertTrue(result["ok"])
        sheet = book["sheets"][payload["edition"]]
        self.assertEqual(sheet["title"], "Химия — Тема 1")
        self.assertEqual(sheet["header"], ["№", "ФИО", "Результат (1)", "Дата"])
        self.assertEqual(sheet["rows"], [{
            "number": 1,
            "name": "Анна",
            "score": 1,
            "date": "23.11.2026 10:00",
        }])

    def test_second_accepted_attempt_gets_the_next_number(self):
        test = sample_test()
        book = {}
        first = gradebook.grade_payload("Химия", test, "Анна", 1)
        second = gradebook.grade_payload("Химия", test, "Борис", 0)
        gradebook.append_grade(book, first, "23.11.2026 10:00")
        gradebook.append_grade(book, second, "23.11.2026 10:05")
        rows = book["sheets"][first["edition"]]["rows"]
        self.assertEqual([row["number"] for row in rows], [1, 2])
        self.assertEqual(len(book["sheets"]), 1)

    def test_closed_retake_rejects_the_same_name(self):
        test = sample_test()
        test["allowRetake"] = False
        book = {}
        payload = gradebook.grade_payload("Химия", test, "Анна  ", 1)
        gradebook.append_grade(book, payload, "23.11.2026 10:00")
        again = gradebook.grade_payload("Химия", test, "  Анна", 0)
        result = gradebook.append_grade(book, again, "23.11.2026 10:05")
        self.assertEqual(result, {"ok": False, "error": "retake"})
        self.assertEqual(len(book["sheets"][payload["edition"]]["rows"]), 1)


if __name__ == "__main__":
    unittest.main()
