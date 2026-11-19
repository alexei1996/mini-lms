"""Local site server. The teacher password stays in a gitignored file."""

import base64
import binascii
import json
import re
import secrets
import shutil
import subprocess
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import catalog
import import_deck
import publish_site
import scoring

DATA = ROOT / "data"
LOGIN_FILE = DATA / "teacher-login.json"
COURSES_FILE = DATA / "teacher-courses.json"
SLIDE_DIR = DATA / "slide-images"
TEST_IMAGE_DIR = DATA / "test-images"
ATTEMPTS_FILE = DATA / "attempts.json"
SLIDE_URL = re.compile(r"^/api/slide/([^/]+)/([^/]+)/(\d+)\.png$")
TEST_IMAGE_URL = re.compile(r"^/api/test-image/([a-f0-9]{16}\.(?:png|jpg))$")
SESSIONS = set()


def load_json(path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_login():
    if LOGIN_FILE.exists():
        return
    save_json(LOGIN_FILE, {
        "email": "teacher@localhost",
        "password": secrets.token_urlsafe(9),
    })


def courses():
    items = load_json(COURSES_FILE, [])
    for course in items:
        catalog.ensure_sections(course)
    return items


def save_courses(items):
    save_json(COURSES_FILE, items)
    publish_site.sync_published(ROOT, items)
    push_published_files()


def push_published_files():
    git = ["git", "-C", str(ROOT)]
    subprocess.run(git + ["add", "-A", "--", "published/catalog.json", "slides/published"], check=False)
    staged = subprocess.run(git + ["diff", "--cached", "--quiet"])
    if staged.returncode != 0:
        subprocess.run(
            git + [
                "-c", "user.name=alexei1996",
                "-c", "user.email=alexei1996@users.noreply.github.com",
                "commit", "-m", "Publish slide images",
            ],
            check=False,
        )
    ahead = subprocess.run(
        git + ["rev-list", "--count", "origin/main..HEAD"],
        capture_output=True,
        text=True,
    )
    if ahead.returncode != 0 or ahead.stdout.strip() in ("", "0"):
        return
    subprocess.run(
        git + ["-c", "http.postBuffer=524288000", "-c", "http.version=HTTP/1.1", "push", "origin", "HEAD"],
        check=False,
    )


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.route_get(parsed)
            return
        if self.hidden(parsed.path):
            self.send_error(404)
            return
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.route_post(parsed.path)
            return
        self.send_error(404)

    def hidden(self, path):
        lowered = path.lower()
        return lowered.startswith("/data/") or lowered.startswith("/.git")

    def route_get(self, parsed):
        if parsed.path == "/api/me":
            self.respond({"signedIn": self.signed_in()})
            return
        if parsed.path == "/api/public-courses":
            self.respond([
                {"id": course["id"], "title": course["title"]}
                for course in courses()
            ])
            return
        if parsed.path == "/api/public-course":
            course_id = parse_qs(parsed.query).get("id", [""])[0]
            course = self.find(course_id)
            if course is None:
                self.respond({"error": "missing"}, 404)
                return
            self.respond(catalog.public_course(course))
            return
        slide = SLIDE_URL.match(parsed.path)
        if slide:
            self.serve_slide(slide.group(1), slide.group(2), int(slide.group(3)))
            return
        if parsed.path == "/api/attempts":
            if not self.signed_in():
                self.respond({"error": "auth"}, 401)
                return
            self.respond(load_json(ATTEMPTS_FILE, []))
            return
        image = TEST_IMAGE_URL.match(parsed.path)
        if image:
            self.serve_test_image(image.group(1))
            return
        if parsed.path == "/api/courses":
            if not self.signed_in():
                self.respond({"error": "auth"}, 401)
                return
            self.respond(courses())
            return
        self.respond({"error": "missing"}, 404)

    def route_post(self, path):
        body = self.read_json()
        if path == "/api/login":
            login = load_json(LOGIN_FILE, None)
            if login and catalog.password_matches(login, body.get("email", ""), body.get("password", "")):
                token = secrets.token_urlsafe(24)
                SESSIONS.add(token)
                self.respond({"signedIn": True}, set_cookie=token)
                return
            self.respond({"signedIn": False}, 401)
            return
        if path == "/api/logout":
            SESSIONS.discard(self.cookie())
            self.respond({"signedIn": False}, clear_cookie=True)
            return
        if path == "/api/attempt":
            self.submit_attempt(body)
            return
        if not self.signed_in():
            self.respond({"error": "auth"}, 401)
            return
        items = courses()
        if path == "/api/upload":
            self.upload(body, items)
            return
        if path == "/api/test-image":
            self.save_test_image(body)
            return
        if path == "/api/courses":
            try:
                course = catalog.create_course(body.get("title", ""), items)
            except ValueError:
                self.respond({"error": "title"}, 400)
                return
            items.append(course)
            save_courses(items)
            self.respond(course)
            return
        course = self.find(body.get("courseId", ""), items)
        if course is None:
            self.respond({"error": "missing"}, 404)
            return
        if path == "/api/presentations":
            catalog.add_prepared_presentation(course)
        elif path == "/api/publish":
            try:
                catalog.set_published(course, body.get("presentationId", ""), body.get("published"))
            except KeyError:
                self.respond({"error": "missing"}, 404)
                return
        elif path == "/api/section":
            try:
                catalog.set_section(
                    course,
                    body.get("sectionId", ""),
                    body.get("text", ""),
                    body.get("published"),
                )
            except KeyError:
                self.respond({"error": "missing"}, 404)
                return
        elif path == "/api/tests":
            test = catalog.add_test(course, body.get("title", ""))
            save_courses(items)
            self.respond(test)
            return
        elif path == "/api/tests/save":
            try:
                test = catalog.save_test(
                    course,
                    body.get("testId", ""),
                    body.get("title", ""),
                    body.get("allowRetake", True),
                    body.get("questions") or [],
                    body.get("published"),
                )
            except KeyError:
                self.respond({"error": "missing"}, 404)
                return
            except ValueError:
                self.respond({"error": "incomplete"}, 400)
                return
        elif path == "/api/delete":
            self.delete(body, items, course)
            return
        else:
            self.respond({"error": "missing"}, 404)
            return
        save_courses(items)
        self.respond(course)

    def delete(self, body, items, course):
        try:
            if body.get("testId"):
                catalog.delete_test(course, body.get("testId"))
            elif body.get("presentationId"):
                catalog.delete_presentation(course, body.get("presentationId"))
                shutil.rmtree(SLIDE_DIR / course["id"] / body.get("presentationId"), ignore_errors=True)
            else:
                items[:] = catalog.delete_course(items, course["id"])
                shutil.rmtree(SLIDE_DIR / course["id"], ignore_errors=True)
        except KeyError:
            self.respond({"error": "missing"}, 404)
            return
        save_courses(items)
        self.respond({"ok": True})

    def upload(self, body, items):
        course = self.find(body.get("courseId", ""), items)
        if course is None:
            self.respond({"error": "missing"}, 404)
            return
        filename = Path(body.get("filename") or "").name
        try:
            images = import_deck.import_deck(
                base64.b64decode(body.get("contentBase64") or ""),
                filename,
            )
        except import_deck.DeckError as error:
            code = "render" if str(error) == "render" else "type"
            self.respond({"error": code}, 400)
            return
        except (ValueError, binascii.Error):
            self.respond({"error": "type"}, 400)
            return
        title = Path(filename).stem or "Презентация"
        presentation = catalog.add_uploaded_presentation(course, title, [])
        folder = SLIDE_DIR / course["id"] / presentation["id"]
        folder.mkdir(parents=True, exist_ok=True)
        urls = []
        for index, png in enumerate(images, start=1):
            (folder / ("%d.png" % index)).write_bytes(png)
            urls.append("/api/slide/%s/%s/%d.png" % (course["id"], presentation["id"], index))
        presentation["slides"] = urls
        save_courses(items)
        self.respond(presentation)

    def save_test_image(self, body):
        try:
            raw = base64.b64decode(body.get("contentBase64") or "")
        except (ValueError, binascii.Error):
            self.respond({"error": "type"}, 400)
            return
        if raw.startswith(b"\x89PNG"):
            extension = "png"
        elif raw.startswith(b"\xff\xd8"):
            extension = "jpg"
        else:
            self.respond({"error": "type"}, 400)
            return
        image_id = "%s.%s" % (secrets.token_hex(8), extension)
        TEST_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        (TEST_IMAGE_DIR / image_id).write_bytes(raw)
        self.respond({"id": image_id})

    def serve_test_image(self, image_id):
        if not self.signed_in():
            self.send_error(404)
            return
        path = TEST_IMAGE_DIR / image_id
        if not path.is_file():
            self.send_error(404)
            return
        payload = path.read_bytes()
        kind = "image/jpeg" if image_id.endswith(".jpg") else "image/png"
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def submit_attempt(self, body):
        items = courses()
        course = self.find(body.get("courseId", ""), items)
        if course is None:
            self.respond({"error": "missing"}, 404)
            return
        try:
            test = catalog.find_test(course, body.get("testId", ""))
        except KeyError:
            self.respond({"error": "missing"}, 404)
            return
        if not test.get("published"):
            self.respond({"error": "missing"}, 404)
            return
        prior = load_json(ATTEMPTS_FILE, [])
        try:
            attempt = scoring.prepare_attempt(
                test,
                course["id"],
                course["title"],
                body.get("name", ""),
                body.get("email", ""),
                body.get("answers") or {},
                prior,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )
        except scoring.AttemptError as error:
            status = 409 if error.code == "retake" else 400
            self.respond({"error": error.code}, status)
            return
        attempt["id"] = secrets.token_hex(8)
        prior.append(attempt)
        save_json(ATTEMPTS_FILE, prior)
        self.respond({
            "status": "sent",
            "score": attempt["score"],
            "total": attempt["total"],
            "attemptNumber": attempt["attemptNumber"],
        })

    def serve_slide(self, course_id, presentation_id, index):
        course = self.find(course_id)
        presentation = None
        if course is not None:
            for item in course["presentations"]:
                if item["id"] == presentation_id:
                    presentation = item
        if presentation is None or (not presentation["published"] and not self.signed_in()):
            self.send_error(404)
            return
        path = SLIDE_DIR / course_id / presentation_id / ("%d.png" % index)
        if not path.is_file():
            self.send_error(404)
            return
        payload = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def find(self, course_id, items=None):
        for course in items if items is not None else courses():
            if course["id"] == course_id:
                return course
        return None

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def cookie(self):
        header = self.headers.get("Cookie", "")
        for part in header.split(";"):
            name, _, value = part.strip().partition("=")
            if name == "lms_teacher":
                return value
        return ""

    def signed_in(self):
        return self.cookie() in SESSIONS

    def respond(self, payload, status=200, set_cookie=None, clear_cookie=False):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        if set_cookie:
            self.send_header(
                "Set-Cookie",
                "lms_teacher=%s; HttpOnly; SameSite=Lax; Path=/" % set_cookie,
            )
        if clear_cookie:
            self.send_header(
                "Set-Cookie",
                "lms_teacher=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0",
            )
        self.end_headers()
        self.wfile.write(raw)


def main():
    ensure_login()
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
