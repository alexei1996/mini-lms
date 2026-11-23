import re
from datetime import datetime
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

import gradebook
import pictures
import scoring

_RICH_TAG = re.compile(r"<(?:p|div|br|strong|em|b|i|a)\b", re.I)
_ALIGN = re.compile(r"text-align\s*:\s*(left|center|right|justify)", re.I)
_SAFE_URL = re.compile(r"^(https?:|mailto:)", re.I)
_ALLOWED = {"p", "div", "br", "strong", "em", "a"}

PREPARED_TITLE = "Подготовленная презентация"
PREPARED_SLIDES = [
    "slides/intro/01.svg",
    "slides/intro/02.svg",
    "slides/intro/03.svg",
]


def create_course(title, existing):
    cleaned = " ".join(title.split())
    if not cleaned:
        raise ValueError("empty title")
    taken = {course["id"] for course in existing}
    number = 1
    while "c%d" % number in taken:
        number += 1
    return {
        "id": "c%d" % number,
        "title": cleaned,
        "presentations": [],
        "tests": [],
    }


def add_uploaded_presentation(course, title, slide_urls):
    taken = {presentation["id"] for presentation in course["presentations"]}
    number = 1
    while "p%d" % number in taken:
        number += 1
    presentation = {
        "id": "p%d" % number,
        "title": title or "Презентация",
        "published": False,
        "slides": list(slide_urls),
    }
    course["presentations"].append(presentation)
    return presentation


def add_prepared_presentation(course):
    for presentation in course["presentations"]:
        if presentation["id"] == "prepared":
            return presentation
    presentation = {
        "id": "prepared",
        "title": PREPARED_TITLE,
        "published": False,
        "slides": list(PREPARED_SLIDES),
    }
    course["presentations"].append(presentation)
    return presentation


METHOD_SECTION = {
    "id": "method",
    "title": "Методические материалы",
}
ANNOUNCE_SECTION = {
    "id": "announce",
    "title": "Объявления",
}
COURSE_SECTIONS = (METHOD_SECTION, ANNOUNCE_SECTION)


def ensure_sections(course):
    sections = course.setdefault("sections", [])
    for spec in COURSE_SECTIONS:
        if not any(section["id"] == spec["id"] for section in sections):
            sections.append({
                "id": spec["id"],
                "title": spec["title"],
                "text": "",
                "published": False,
            })
    return sections


def set_section(course, section_id, text, published):
    for section in ensure_sections(course):
        if section["id"] == section_id:
            section["text"] = clean_section_html("" if text is None else str(text))
            section["published"] = bool(published)
            return section
    raise KeyError(section_id)


def clean_section_html(text):
    raw = "" if text is None else str(text)
    if not _RICH_TAG.search(raw):
        return raw
    parser = _SectionCleaner()
    parser.feed(raw)
    parser.close()
    while parser.stack:
        parser.parts.append("</%s>" % parser.stack.pop())
    return "".join(parser.parts)


class _SectionCleaner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.stack = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        self._open(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        self._open(tag, attrs, empty=True)

    def _open(self, tag, attrs, empty=False):
        tag = _plain_tag(tag)
        if self.skip:
            if not empty:
                self.skip += 1
            return
        if tag not in _ALLOWED:
            if not empty:
                self.skip += 1
            return
        if tag == "br":
            self.parts.append("<br>")
            return
        attr = ""
        if tag == "a":
            href = _attr(attrs, "href")
            if not _SAFE_URL.match(href):
                if not empty:
                    self.skip += 1
                return
            attr = ' href="%s"' % _escape(href)
        elif tag in ("p", "div"):
            found = _ALIGN.search(_attr(attrs, "style"))
            if found:
                attr = ' style="text-align: %s"' % found.group(1).lower()
        self.parts.append("<%s%s>" % (tag, attr))
        if not empty:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        tag = _plain_tag(tag)
        if self.skip:
            self.skip -= 1
            return
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
            self.parts.append("</%s>" % tag)

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(_escape(data))


def _plain_tag(tag):
    tag = tag.lower()
    if tag == "b":
        return "strong"
    if tag == "i":
        return "em"
    return tag


def _attr(attrs, name):
    for key, value in attrs:
        if key.lower() == name:
            return (value or "").strip()
    return ""


def _escape(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def delete_course(items, course_id):
    kept = [course for course in items if course["id"] != course_id]
    if len(kept) == len(items):
        raise KeyError(course_id)
    return kept


def delete_presentation(course, presentation_id):
    kept = [item for item in course["presentations"] if item["id"] != presentation_id]
    if len(kept) == len(course["presentations"]):
        raise KeyError(presentation_id)
    course["presentations"] = kept


def add_test(course, title):
    tests = course.setdefault("tests", [])
    taken = {item["id"] for item in tests}
    number = 1
    while "t%d" % number in taken:
        number += 1
    cleaned = " ".join((title or "").split()) or "Тест"
    test = {
        "id": "t%d" % number,
        "title": cleaned,
        "published": False,
        "allowRetake": True,
        "questions": [],
    }
    tests.append(test)
    return test


def save_test(course, test_id, title, allow_retake, questions, published):
    test = find_test(course, test_id)
    updated_questions = normalize_questions(questions, test.get("questions"))
    if published and not scoring.ready_to_publish({"questions": updated_questions}):
        raise ValueError("incomplete")
    test["title"] = " ".join((title or "").split()) or "Тест"
    test["allowRetake"] = bool(allow_retake)
    test["questions"] = updated_questions
    test["published"] = bool(published)
    if published:
        edition = gradebook.grade_edition(test)
        if edition != test.get("gradeEdition") or not test.get("gradePublishedOn"):
            test["gradePublishedOn"] = _moscow_day()
        test["gradeEdition"] = edition
    return test


def _moscow_day():
    return datetime.now(ZoneInfo("Europe/Moscow")).date().isoformat()


def find_test(course, test_id):
    for test in course.get("tests") or []:
        if test["id"] == test_id:
            return test
    raise KeyError(test_id)


def normalize_questions(raw, previous=None):
    questions = []
    seen = set()
    earlier = _by_id(previous)
    for index, item in enumerate(raw or [], start=1):
        if not isinstance(item, dict):
            continue
        question_id = str(item.get("id") or ("q%d" % index))
        while question_id in seen:
            question_id += "x"
        seen.add(question_id)
        image = str(item.get("image") or "")
        if "/" in image or "\\" in image:
            image = ""
        old = earlier.get(question_id, {})
        questions.append({
            "id": question_id,
            "prompt": normalize_prompt(item.get("prompt")),
            "image": image,
            "imagePercent": pictures.picture_percent(item.get("imagePercent"), old.get("imagePercent")),
            "options": normalize_options(item.get("options"), old.get("options")),
        })
    return questions


def normalize_prompt(raw):
    fragments = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        kind = item.get("type") or "text"
        if kind not in ("text", "bold", "italic", "list", "formula"):
            kind = "text"
        fragments.append({"type": kind, "text": str(item.get("text") or "")})
    return fragments


def normalize_options(raw, previous=None):
    options = []
    seen = set()
    earlier = _by_id(previous)
    for index, item in enumerate(raw or [], start=1):
        if not isinstance(item, dict):
            continue
        option_id = str(item.get("id") or ("o%d" % index))
        while option_id in seen:
            option_id += "x"
        seen.add(option_id)
        image = str(item.get("image") or "")
        if "/" in image or "\\" in image:
            image = ""
        old = earlier.get(option_id, {})
        options.append({
            "id": option_id,
            "text": str(item.get("text") or ""),
            "image": image,
            "imagePercent": pictures.picture_percent(item.get("imagePercent"), old.get("imagePercent")),
            "correct": bool(item.get("correct")),
        })
    return options


def _by_id(items):
    found = {}
    for item in items or []:
        if isinstance(item, dict) and item.get("id"):
            found[str(item["id"])] = item
    return found


def delete_test(course, test_id):
    kept = [item for item in course.get("tests", []) if item["id"] != test_id]
    if len(kept) == len(course.get("tests", [])):
        raise KeyError(test_id)
    course["tests"] = kept


def set_published(course, presentation_id, published):
    for presentation in course["presentations"]:
        if presentation["id"] == presentation_id:
            presentation["published"] = bool(published)
            return presentation
    raise KeyError(presentation_id)


def public_course(course):
    presentations = []
    for presentation in course["presentations"]:
        if not presentation["published"]:
            continue
        presentations.append({
            "id": presentation["id"],
            "title": presentation["title"],
            "slides": list(presentation["slides"]),
        })
    return {
        "id": course["id"],
        "title": course["title"],
        "presentations": presentations,
        "sections": public_sections(course),
        "tests": scoring.student_tests(course),
    }


def public_sections(course):
    visible = []
    for section in course.get("sections", []):
        if not section.get("published"):
            continue
        visible.append({
            "id": section["id"],
            "title": section["title"],
            "text": clean_section_html(section.get("text") or ""),
        })
    return visible


def password_matches(login, email, password):
    expected = login["email"].strip().lower()
    given = email.strip().lower()
    return given == expected and password == login["password"]
