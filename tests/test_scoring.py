import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import scoring


def question(correct_ids, question_id="q1"):
    options = []
    for name in ("a", "b", "c"):
        options.append({
            "id": name,
            "text": name,
            "image": "",
            "correct": name in correct_ids,
        })
    return {"id": question_id, "prompt": [{"type": "text", "text": "Вопрос"}], "options": options}


class ScoringTest(unittest.TestCase):
    def test_student_view_has_no_correct_flag(self):
        test = {
            "id": "t1",
            "title": "Проверка",
            "allowRetake": True,
            "published": True,
            "questions": [question({"a"})],
        }
        student = scoring.to_student_test(test, "c1")
        self.assertNotIn("correct", str(student))
        self.assertEqual(student["questions"][0]["options"][0]["id"], "a")

    def test_score_matches_only_the_whole_set(self):
        test = {"questions": [
            question({"a"}, "one"),
            question({"a", "b"}, "many"),
            question({"a"}, "extra"),
            question({"a", "b"}, "partial"),
            question({"a"}, "empty"),
            question({"a"}, "foreign"),
        ]}
        answers = {
            "one": ["a"],
            "many": ["b", "a"],
            "extra": ["a", "b"],
            "partial": ["a"],
            "empty": [],
            "foreign": ["nope"],
        }
        result = scoring.score_attempt(test, answers)
        self.assertEqual(result, {"score": 2, "total": 6})

    def test_retake_switch_and_attempt_number(self):
        test = {"id": "t1", "title": "Проверка", "allowRetake": True, "questions": [question({"a"})]}
        first = scoring.prepare_attempt(test, "c1", "Курс", "  Анна   Иванова ", "A@Example.com", {"q1": ["a"]}, [], "t")
        self.assertEqual(first["attemptNumber"], 1)
        self.assertEqual(first["nameKey"], "Анна Иванова")
        self.assertEqual(first["emailKey"], "a@example.com")
        self.assertEqual(first["score"], 1)
        second = scoring.prepare_attempt(
            test, "c1", "Курс", "Анна Иванова", "a@example.com", {"q1": []}, [first], "t2"
        )
        self.assertEqual(second["attemptNumber"], 2)
        test["allowRetake"] = False
        with self.assertRaises(scoring.AttemptError) as caught:
            scoring.prepare_attempt(test, "c1", "Курс", "Анна Иванова", "a@example.com", {"q1": ["a"]}, [first, second], "t3")
        self.assertEqual(caught.exception.code, "retake")

    def test_blank_name_or_email_is_rejected(self):
        test = {"id": "t1", "allowRetake": True, "questions": [question({"a"})]}
        with self.assertRaises(scoring.AttemptError):
            scoring.prepare_attempt(test, "c1", "Курс", "   ", "a@example.com", {}, [], "t")
        with self.assertRaises(scoring.AttemptError):
            scoring.prepare_attempt(test, "c1", "Курс", "Анна", "  ", {}, [], "t")

    def test_saved_snapshot_keeps_the_submitted_wording(self):
        test = {"id": "t1", "title": "Проверка", "allowRetake": True, "questions": [question({"a"})]}
        attempt = scoring.prepare_attempt(test, "c1", "Курс", "Анна", "a@example.com", {"q1": ["a"]}, [], "t")
        test["questions"][0]["prompt"][0]["text"] = "Другой вопрос"
        self.assertEqual(attempt["snapshot"][0]["prompt"][0]["text"], "Вопрос")
        self.assertTrue(attempt["snapshot"][0]["options"][0]["correct"])

    def test_one_option_or_no_correct_answer_cannot_publish(self):
        lone = {"questions": [{"id": "q1", "options": [{"id": "a", "correct": True}]}]}
        none = {"questions": [question(set())]}
        good = {"questions": [question({"b"})]}
        self.assertFalse(scoring.ready_to_publish(lone))
        self.assertFalse(scoring.ready_to_publish(none))
        self.assertTrue(scoring.ready_to_publish(good))
        self.assertFalse(scoring.ready_to_publish({"questions": []}))


if __name__ == "__main__":
    unittest.main()
