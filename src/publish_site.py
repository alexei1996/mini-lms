import json
import shutil
from pathlib import Path


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
            "tests": [],
        })
    return catalog


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
    catalog_path = root / "published" / "catalog.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return catalog
