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
        "tests": [],
    }


def password_matches(login, email, password):
    expected = login["email"].strip().lower()
    given = email.strip().lower()
    return given == expected and password == login["password"]
