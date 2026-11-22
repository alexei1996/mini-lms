import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import catalog


class CatalogTest(unittest.TestCase):
    def test_new_course_has_a_student_link_and_no_materials(self):
        course = catalog.create_course("Новый курс", [])
        self.assertEqual(course["title"], "Новый курс")
        self.assertEqual(course["presentations"], [])
        self.assertEqual(course["tests"], [])
        self.assertTrue(course["id"])

    def test_blank_title_is_rejected(self):
        with self.assertRaises(ValueError):
            catalog.create_course("   ", [])

    def test_draft_is_hidden_from_the_student(self):
        course = catalog.create_course("Курс", [])
        catalog.add_prepared_presentation(course)
        public = catalog.public_course(course)
        self.assertEqual(public["presentations"], [])
        self.assertEqual(public["tests"], [])
        self.assertNotIn("published", str(public))

    def test_publish_then_unpublish(self):
        course = catalog.create_course("Курс", [])
        presentation = catalog.add_prepared_presentation(course)
        catalog.set_published(course, presentation["id"], True)
        public = catalog.public_course(course)
        self.assertEqual(public["presentations"][0]["title"], "Подготовленная презентация")
        self.assertEqual(len(public["presentations"][0]["slides"]), 3)
        self.assertNotIn("published", public["presentations"][0])
        catalog.set_published(course, presentation["id"], False)
        self.assertEqual(catalog.public_course(course)["presentations"], [])

    def test_section_text_stays_hidden_until_published(self):
        course = catalog.create_course("Курс", [])
        catalog.ensure_sections(course)
        self.assertEqual([section["id"] for section in course["sections"]], ["method", "announce"])
        catalog.set_section(course, "method", "Для ученика", False)
        self.assertEqual(catalog.public_course(course)["sections"], [])
        catalog.set_section(course, "method", "Для ученика", True)
        visible = catalog.public_course(course)["sections"]
        self.assertEqual(visible[0]["text"], "Для ученика")
        catalog.set_section(
            course,
            "method",
            '<p style="text-align: center"><strong>Глава</strong> <a href="https://example.com">ссылка</a></p><script>bad</script>',
            True,
        )
        cleaned = catalog.public_course(course)["sections"][0]["text"]
        self.assertIn("<strong>Глава</strong>", cleaned)
        self.assertIn('href="https://example.com"', cleaned)
        self.assertIn("text-align: center", cleaned)
        self.assertNotIn("script", cleaned)
        self.assertNotIn("published", visible[0])

    def test_delete_removes_course_presentation_and_test(self):
        course = catalog.create_course("Курс", [])
        presentation = catalog.add_prepared_presentation(course)
        course["tests"].append({"id": "t1", "title": "Проверка"})
        catalog.delete_presentation(course, presentation["id"])
        catalog.delete_test(course, "t1")
        self.assertEqual(course["presentations"], [])
        self.assertEqual(course["tests"], [])
        self.assertEqual(catalog.delete_course([course], course["id"]), [])

    def test_password_check_does_not_accept_a_wrong_pair(self):
        login = {"email": "teacher@localhost", "password": "secret-pass"}
        self.assertTrue(catalog.password_matches(login, "teacher@localhost", "secret-pass"))
        self.assertFalse(catalog.password_matches(login, "teacher@localhost", "nope"))
        self.assertFalse(catalog.password_matches(login, "other@localhost", "secret-pass"))


if __name__ == "__main__":
    unittest.main()
