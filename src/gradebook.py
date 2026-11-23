import hashlib
import json


class GradeError(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def grade_edition(test):
    material = {
        "title": clean_name(test.get("title")) or "Тест",
        "questions": [question_material(item) for item in test.get("questions") or []],
    }
    raw = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def continues_sheet(previous, published):
    return grade_edition(previous) == grade_edition(published)


def grade_payload(course_title, test, name, score):
    cleaned = clean_name(name)
    if not cleaned:
        raise GradeError("identity")
    return {
        "name": cleaned,
        "score": int(score),
        "total": len(test.get("questions") or []),
        "courseTitle": clean_name(course_title) or "Курс",
        "testTitle": clean_name(test.get("title")) or "Тест",
        "edition": grade_edition(test),
        "allowRetake": bool(test.get("allowRetake", True)),
        "publishedOn": test.get("gradePublishedOn") or "",
    }


def append_grade(book, payload, now):
    cleaned = clean_name(payload.get("name"))
    if not cleaned:
        return {"ok": False, "error": "identity"}
    sheets = book.setdefault("sheets", {})
    edition = payload["edition"]
    if edition not in sheets:
        total = int(payload["total"])
        sheets[edition] = {
            "title": sheet_title(book, payload),
            "header": ["№", "ФИО", "Результат (%s)" % total, "Дата"],
            "rows": [],
        }
    sheet = sheets[edition]
    if payload.get("allowRetake") is False and any(row["name"] == cleaned for row in sheet["rows"]):
        return {"ok": False, "error": "retake"}
    sheet["rows"].append({
        "number": len(sheet["rows"]) + 1,
        "name": cleaned,
        "score": int(payload["score"]),
        "date": now,
    })
    return {"ok": True}


def sheet_title(book, payload):
    course = clean_name(payload.get("courseTitle")) or "Курс"
    test = clean_name(payload.get("testTitle")) or "Тест"
    base = fit_sheet_name(course + " — " + test)
    taken = {sheet["title"] for sheet in book.get("sheets", {}).values()}
    if base not in taken:
        return base
    published = clean_name(payload.get("publishedOn"))
    with_date = fit_sheet_name(base + " " + published) if published else base
    if with_date not in taken:
        return with_date
    counter = 2
    while fit_sheet_name(with_date + " " + str(counter)) in taken:
        counter += 1
    return fit_sheet_name(with_date + " " + str(counter))


def fit_sheet_name(name):
    cleaned = "".join(" " if char in ":\\/?*[]" else char for char in str(name))
    cleaned = " ".join(cleaned.split())
    return (cleaned or "Тест")[:99]


def question_material(question):
    return {
        "prompt": question.get("prompt") or [],
        "image": question.get("image") or "",
        "options": [{
            "text": option.get("text") or "",
            "image": option.get("image") or "",
            "correct": bool(option.get("correct")),
        } for option in question.get("options") or []],
    }


def clean_name(value):
    return " ".join(str(value or "").split())
