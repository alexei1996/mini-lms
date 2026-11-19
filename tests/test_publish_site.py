import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import publish_site


class PublishSiteTest(unittest.TestCase):
    def test_draft_images_stay_out_of_the_public_catalog(self):
        courses = [{
            "id": "c1",
            "title": "Курс",
            "presentations": [{
                "id": "p1",
                "title": "Лекция",
                "published": False,
                "slides": ["/api/slide/c1/p1/1.png"],
            }],
            "tests": [{"id": "secret"}],
        }]
        catalog = publish_site.published_catalog(courses)
        self.assertEqual(catalog[0]["presentations"], [])
        self.assertEqual(catalog[0]["tests"], [])
        self.assertEqual(catalog[0]["sections"], [])

    def test_published_upload_points_at_repo_images_not_the_source_file(self):
        courses = [{
            "id": "c1",
            "title": "Курс",
            "presentations": [{
                "id": "p1",
                "title": "Лекция",
                "published": True,
                "slides": ["/api/slide/c1/p1/1.png", "/api/slide/c1/p1/2.png"],
            }],
            "tests": [],
        }]
        slides = publish_site.published_catalog(courses)[0]["presentations"][0]["slides"]
        self.assertEqual(slides, [
            "slides/published/c1/p1/1.png",
            "slides/published/c1/p1/2.png",
        ])

    def test_sync_copies_only_published_pngs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            origin = root / "data" / "slide-images" / "c1" / "p1"
            origin.mkdir(parents=True)
            (origin / "1.png").write_bytes(b"png-1")
            (origin / "2.png").write_bytes(b"png-2")
            courses = [{
                "id": "c1",
                "title": "Курс",
                "presentations": [
                    {
                        "id": "p1",
                        "title": "Лекция",
                        "published": True,
                        "slides": ["/api/slide/c1/p1/1.png"],
                    },
                    {
                        "id": "p2",
                        "title": "Черновик",
                        "published": False,
                        "slides": ["/api/slide/c1/p2/1.png"],
                    },
                ],
                "tests": [],
            }]
            publish_site.sync_published(root, courses)
            self.assertEqual((root / "slides" / "published" / "c1" / "p1" / "1.png").read_bytes(), b"png-1")
            self.assertFalse((root / "slides" / "published" / "c1" / "p2").exists())
            catalog = json.loads((root / "published" / "catalog.json").read_text(encoding="utf-8"))
            self.assertEqual(len(catalog[0]["presentations"]), 1)
            self.assertNotIn(".pptx", json.dumps(catalog))
            self.assertNotIn(".pdf", json.dumps(catalog))

    def test_only_published_section_text_reaches_the_catalog(self):
        courses = [{
            "id": "c1",
            "title": "Курс",
            "presentations": [],
            "tests": [],
            "sections": [
                {
                    "id": "method",
                    "title": "Методические материалы",
                    "text": "видно ученику",
                    "published": True,
                },
                {
                    "id": "draft",
                    "title": "Черновик",
                    "text": "скрыто",
                    "published": False,
                },
            ],
        }]
        sections = publish_site.published_catalog(courses)[0]["sections"]
        self.assertEqual([item["text"] for item in sections], ["видно ученику"])
        self.assertNotIn("published", sections[0])

    def test_published_test_omits_the_answer_key(self):
        courses = [{
            "id": "c1",
            "title": "Курс",
            "presentations": [],
            "tests": [{
                "id": "t1",
                "title": "Проверка",
                "published": True,
                "allowRetake": True,
                "questions": [{
                    "id": "q1",
                    "prompt": [{"type": "text", "text": "Сколько?"}],
                    "options": [
                        {"id": "a", "text": "один", "image": "", "correct": True},
                        {"id": "b", "text": "два", "image": "", "correct": False},
                    ],
                }],
            }],
            "sections": [],
        }]
        catalog = publish_site.published_catalog(courses)
        dumped = json.dumps(catalog)
        self.assertNotIn("correct", dumped)
        self.assertEqual(catalog[0]["tests"][0]["questions"][0]["options"][0]["text"], "один")


if __name__ == "__main__":
    unittest.main()
