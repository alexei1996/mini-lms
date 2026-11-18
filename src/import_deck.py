import io
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pymupdf
from PIL import Image, ImageDraw

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


def pptx_slides(data):
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        texts = slide_texts(archive)
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as error:
        raise DeckError("unreadable powerpoint") from error
    if not texts:
        raise DeckError("empty powerpoint")
    return [text_slide(text) for text in texts]


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
    draw.rectangle((0, 0, SLIDE_SIZE[0], 16), fill="#1f4d3a")
    draw.text((72, 180), text or " ", fill="#1c1915")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
