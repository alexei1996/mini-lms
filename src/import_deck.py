import io
import subprocess
import tempfile
import threading
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pymupdf
from PIL import Image, ImageDraw, ImageFont

SLIDE_SIZE = (1280, 720)
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


class DeckError(ValueError):
    pass


def import_deck(data, filename):
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return pdf_slides(data)
    if suffix == ".pptx":
        return pptx_slides(data)
    raise DeckError("unsupported file")


def pdf_slides(data):
    try:
        document = pymupdf.open(stream=data, filetype="pdf")
    except Exception as error:
        raise DeckError("unreadable pdf") from error
    if document.page_count < 1:
        raise DeckError("empty pdf")
    slides = []
    for page in document:
        slides.append(page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False).tobytes("png"))
    return slides


OFFICE_LOCK = threading.Lock()
POWERPOINT = Path(r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE")
SOFFICE = Path(r"C:\Program Files\LibreOffice\program\soffice.exe")


def pptx_slides(data):
    if office_package(data):
        images = rendered_slides(data)
        if not images:
            raise DeckError("render")
        return images
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        texts = slide_texts(archive)
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as error:
        raise DeckError("unreadable powerpoint") from error
    if not texts:
        raise DeckError("empty powerpoint")
    return [text_slide(text) for text in texts]


def office_package(data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
    except zipfile.BadZipFile:
        return False
    return any(
        name.startswith("ppt/slideMasters/") or name == "docProps/app.xml"
        for name in names
    )


def rendered_slides(data):
    with OFFICE_LOCK:
        if POWERPOINT.exists():
            images = powerpoint_slides(data)
            if images:
                return images
        if SOFFICE.exists():
            return libreoffice_slides(data)
    return None


def powerpoint_slides(data):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "deck.pptx"
        source.write_bytes(data)
        out = root / "slides"
        out.mkdir()
        script = root / "export.ps1"
        script.write_text(POWERPOINT_EXPORT, encoding="utf-8-sig")
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-File", str(script), str(source), str(out)],
                check=False,
                timeout=600,
                capture_output=True,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        paths = sorted(out.glob("*.png"), key=lambda path: int(path.stem))
        images = [path.read_bytes() for path in paths if path.stat().st_size > 0]
        return images or None


POWERPOINT_EXPORT = r"""
param($Source, $OutDir)
$started = $false
try {
  $app = [Runtime.InteropServices.Marshal]::GetActiveObject("PowerPoint.Application")
} catch {
  $app = New-Object -ComObject PowerPoint.Application
  $started = $true
}
$app.Visible = -1
$presentation = $app.Presentations.Open($Source, $true, $false, $false)
try {
  $number = 1
  foreach ($slide in $presentation.Slides) {
    $target = Join-Path $OutDir ($number.ToString() + ".png")
    $slide.Export($target, "PNG", 1920, 1080)
    $number++
  }
} finally {
  $presentation.Close()
  if ($started) { $app.Quit() }
}
"""


def libreoffice_slides(data):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "deck.pptx"
        source.write_bytes(data)
        profile = (root / "profile").resolve().as_uri()
        try:
            subprocess.run(
                [
                    str(SOFFICE),
                    "--headless",
                    "--nologo",
                    "--nofirststartwizard",
                    "--norestore",
                    "-env:UserInstallation=%s" % profile,
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(root),
                    str(source),
                ],
                check=False,
                timeout=600,
                capture_output=True,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        pdf = root / "deck.pdf"
        if not pdf.is_file():
            return None
        try:
            return pdf_slides(pdf.read_bytes())
        except DeckError:
            return None


def slide_texts(archive):
    presentation = ElementTree.fromstring(archive.read("ppt/presentation.xml"))
    rels = ElementTree.fromstring(archive.read("ppt/_rels/presentation.xml.rels"))
    targets = {}
    for rel in rels:
        targets[rel.attrib["Id"]] = rel.attrib["Target"]
    texts = []
    for slide_id in presentation.findall(".//{%s}sldId" % P_NS):
        rel_id = slide_id.attrib["{%s}id" % R_NS]
        target = targets[rel_id]
        if not target.startswith("ppt/"):
            target = "ppt/" + target.lstrip("/")
        slide = ElementTree.fromstring(archive.read(target))
        parts = [node.text or "" for node in slide.findall(".//{%s}t" % A_NS)]
        texts.append(" ".join(part for part in parts if part).strip())
    return texts


def text_slide(text):
    image = Image.new("RGB", SLIDE_SIZE, "#f7f4ee")
    draw = ImageDraw.Draw(image)
    font = slide_font()
    draw.rectangle((0, 0, SLIDE_SIZE[0], 16), fill="#1f4d3a")
    y = 80
    for line in wrap_text(text or " ", font, SLIDE_SIZE[0] - 144):
        draw.text((72, y), line, fill="#1c1915", font=font)
        y += 48
        if y > SLIDE_SIZE[1] - 48:
            break
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def slide_font():
    for path in (
        Path(r"C:\Windows\Fonts\segoeui.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ):
        if path.exists():
            return ImageFont.truetype(str(path), 36)
    return ImageFont.load_default()


def wrap_text(text, font, width):
    words = text.split()
    if not words:
        return [""]
    lines = []
    current = words[0]
    for word in words[1:]:
        trial = current + " " + word
        if font.getlength(trial) <= width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines
