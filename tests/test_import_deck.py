import io
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import import_deck


class ImportDeckTest(unittest.TestCase):
    def test_one_page_pdf_becomes_one_slide(self):
        slides = import_deck.import_deck(one_page_pdf(), "lecture.pdf")
        self.assertEqual(len(slides), 1)
        self.assertTrue(slides[0].startswith(b"\x89PNG"))

    def test_pptx_slides_follow_document_order_not_file_names(self):
        slides = import_deck.import_deck(two_slide_pptx(), "lecture.pptx")
        first_only = import_deck.import_deck(one_slide_pptx("FIRST"), "one.pptx")
        self.assertEqual(len(slides), 2)
        self.assertEqual(slides[0], first_only[0])
        self.assertNotEqual(slides[0], slides[1])

    def test_other_file_types_are_rejected(self):
        with self.assertRaises(import_deck.DeckError):
            import_deck.import_deck(b"hello", "notes.txt")


def one_page_pdf():
    stream = b"BT /F1 24 Tf 72 120 Td (PDF) Tj ET"
    objects = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(b"2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj\n")
    objects.append(
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
    )
    objects.append(b"4 0 obj << /Length %d >> stream\n%s\nendstream endobj\n" % (len(stream), stream))
    objects.append(b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
    body = b"%PDF-1.4\n"
    offsets = [0]
    for obj in objects:
        offsets.append(len(body))
        body += obj
    xref = len(body)
    body += b"xref\n0 6\n"
    body += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        body += b"%010d 00000 n \n" % offset
    body += b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % xref
    return body


def one_slide_pptx(text):
    return pptx_with_slides([("slide2.xml", text)])


def two_slide_pptx():
    # slide2.xml is listed first on purpose: file-name order would swap the slides.
    return pptx_with_slides([("slide2.xml", "FIRST"), ("slide1.xml", "SECOND")])


def pptx_with_slides(slides):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types(len(slides)))
        archive.writestr("_rels/.rels", ROOT_RELS)
        archive.writestr("ppt/presentation.xml", presentation_xml(len(slides)))
        archive.writestr("ppt/_rels/presentation.xml.rels", presentation_rels(slides))
        for name, text in slides:
            archive.writestr("ppt/slides/" + name, slide_xml(text))
    return buffer.getvalue()


def content_types(count):
    extras = "".join(
        '<Override PartName="/ppt/slides/slide%d.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        % (index + 1)
        for index in range(count)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        + extras +
        "</Types>"
    )


ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="ppt/presentation.xml"/>'
    "</Relationships>"
)


def presentation_xml(count):
    ids = "".join(
        '<p:sldId id="%d" r:id="rId%d"/>' % (256 + index, index + 1)
        for index in range(count)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<p:sldIdLst>%s</p:sldIdLst></p:presentation>" % ids
    )


def presentation_rels(slides):
    rows = "".join(
        '<Relationship Id="rId%d" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
        'Target="slides/%s"/>' % (index + 1, name)
        for index, (name, _text) in enumerate(slides)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + rows +
        "</Relationships>"
    )


def slide_xml(text):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        "<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>%s</a:t></a:r></a:p>"
        "</p:txBody></p:sp></p:spTree></p:cSld></p:sld>" % text
    )


if __name__ == "__main__":
    unittest.main()
