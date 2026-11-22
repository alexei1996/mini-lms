import json
import shutil
from pathlib import Path

import catalog
import scoring


def published_catalog(courses):
    catalog = []
    for course in courses:
        presentations = []
        for presentation in course["presentations"]:
            if not presentation["published"]:
                continue
            presentations.append({
                "id": presentation["id"],
                "title": presentation["title"],
                "slides": public_slide_paths(course["id"], presentation),
            })
        catalog.append({
            "id": course["id"],
            "title": course["title"],
            "presentations": presentations,
            "sections": public_sections(course),
            "tests": scoring.student_tests(course),
        })
    return catalog


def public_sections(course):
    visible = []
    for section in course.get("sections", []):
        if not section.get("published"):
            continue
        visible.append({
            "id": section["id"],
            "title": section["title"],
            "text": catalog.clean_section_html(section.get("text") or ""),
        })
    return visible


def public_slide_paths(course_id, presentation):
    paths = []
    number = 1
    for source in presentation["slides"]:
        if str(source).startswith("/api/slide/"):
            paths.append("slides/published/%s/%s/%d.png" % (course_id, presentation["id"], number))
            number += 1
        else:
            paths.append(source)
    return paths


def sync_published(root, courses):
    root = Path(root)
    catalog = published_catalog(courses)
    published = root / "slides" / "published"
    if published.exists():
        shutil.rmtree(published)
    published.mkdir(parents=True)
    for course in courses:
        for presentation in course["presentations"]:
            if not presentation["published"]:
                continue
            number = 1
            for source in presentation["slides"]:
                if not str(source).startswith("/api/slide/"):
                    continue
                origin = root / "data" / "slide-images" / course["id"] / presentation["id"] / ("%d.png" % number)
                target = published / course["id"] / presentation["id"] / ("%d.png" % number)
                target.parent.mkdir(parents=True, exist_ok=True)
                if origin.is_file():
                    shutil.copyfile(origin, target)
                number += 1
    copy_test_images(root, courses)
    catalog_path = root / "published" / "catalog.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return catalog


def copy_test_images(root, courses):
    folder = root / "tests" / "published"
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    for course in courses:
        for test in course.get("tests") or []:
            if not test.get("published"):
                continue
            for question in test.get("questions") or []:
                picture = question.get("image") or ""
                if picture:
                    origin = root / "data" / "test-images" / picture
                    target = root / scoring.question_image_path(course["id"], test["id"], question)
                    if origin.is_file():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(origin, target)
                for option in question.get("options") or []:
                    image = option.get("image") or ""
                    if not image:
                        continue
                    origin = root / "data" / "test-images" / image
                    target = root / scoring.option_image_path(
                        course["id"], test["id"], question["id"], option
                    )
                    if origin.is_file():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(origin, target)
