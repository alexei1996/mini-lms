import copy

import gradebook


class AttemptError(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def to_student_test(test, course_id):
    questions = []
    for question in test.get("questions") or []:
        options = []
        for option in question.get("options") or []:
            options.append({
                "id": option["id"],
                "text": option.get("text") or "",
                "image": option_image_path(course_id, test["id"], question["id"], option),
                "correct": bool(option.get("correct")),
            })
        student_question = {
            "id": question["id"],
            "prompt": copy.deepcopy(question.get("prompt") or []),
            "options": options,
        }
        picture = question_image_path(course_id, test["id"], question)
        if picture:
            student_question["image"] = picture
        questions.append(student_question)
    return {
        "id": test["id"],
        "title": test.get("title") or "Тест",
        "allowRetake": bool(test.get("allowRetake", True)),
        "edition": gradebook.grade_edition(test),
        "publishedOn": test.get("gradePublishedOn") or "",
        "questions": questions,
    }


def student_tests(course):
    visible = []
    for test in course.get("tests") or []:
        if not test.get("published"):
            continue
        visible.append(to_student_test(test, course["id"]))
    return visible


def question_image_path(course_id, test_id, question):
    image = question.get("image") or ""
    if not image:
        return ""
    return "tests/published/%s/%s/%s-%s" % (course_id, test_id, question["id"], image)


def option_image_path(course_id, test_id, question_id, option):
    image = option.get("image") or ""
    if not image:
        return ""
    return "tests/published/%s/%s/%s-%s-%s" % (
        course_id, test_id, question_id, option["id"], image
    )


def ready_to_publish(test):
    questions = test.get("questions") or []
    if not questions:
        return False
    for question in questions:
        options = question.get("options") or []
        if len(options) < 2:
            return False
        if not any(option.get("correct") for option in options):
            return False
    return True


def score_attempt(test, answers):
    score = 0
    questions = test.get("questions") or []
    for question in questions:
        if selection_matches(question, answers):
            score += 1
    return {"score": score, "total": len(questions)}


def selection_matches(question, answers):
    option_ids = {option["id"] for option in question.get("options") or []}
    correct = {
        option["id"]
        for option in question.get("options") or []
        if option.get("correct")
    }
    chosen = chosen_ids(answers, question["id"])
    if not chosen <= option_ids:
        return False
    return chosen == correct


def chosen_ids(answers, question_id):
    if not isinstance(answers, dict):
        return set()
    raw = answers.get(question_id)
    if not isinstance(raw, list):
        return set()
    return {str(item) for item in raw}


def prepare_attempt(test, course_id, course_title, name, email, answers, prior, submitted_at):
    name_key = " ".join((name or "").split())
    email_key = (email or "").strip().lower()
    if not name_key:
        raise AttemptError("identity")
    same = [
        item for item in prior
        if item.get("nameKey") == name_key
        and item.get("emailKey") == email_key
        and item.get("testId") == test["id"]
        and item.get("courseId") == course_id
    ]
    if not test.get("allowRetake", True) and same:
        raise AttemptError("retake")
    result = score_attempt(test, answers if isinstance(answers, dict) else {})
    return {
        "courseId": course_id,
        "courseTitle": course_title,
        "testId": test["id"],
        "testTitle": test.get("title") or "Тест",
        "name": (name or "").strip(),
        "email": (email or "").strip(),
        "nameKey": name_key,
        "emailKey": email_key,
        "answers": answers if isinstance(answers, dict) else {},
        "snapshot": copy.deepcopy(test.get("questions") or []),
        "score": result["score"],
        "total": result["total"],
        "attemptNumber": len(same) + 1,
        "submittedAt": submitted_at,
    }
