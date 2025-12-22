from __future__ import annotations
from typing import Iterable, Tuple
from docx import Document
from docx2pdf import convert
import tempfile
import os

def iter_docx_paragraph_texts(path: str) -> Iterable[str]:
    doc = Document(path)
    for p in doc.paragraphs:
        if p.text:
            yield p.text

def docx_to_pdf_bytes(uploaded_docx):
    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = os.path.join(tmpdir, "input.docx")
        pdf_path = os.path.join(tmpdir, "output.pdf")

        with open(docx_path, "wb") as f:
            f.write(uploaded_docx.getvalue())

        convert(docx_path, pdf_path)
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

    return pdf_bytes
