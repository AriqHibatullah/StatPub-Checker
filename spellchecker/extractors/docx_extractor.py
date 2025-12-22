from __future__ import annotations
from typing import Iterable, Tuple
from docx import Document
from docx2pdf import convert
import os, tempfile

def iter_docx_paragraph_texts(path: str) -> Iterable[str]:
    doc = Document(path)
    for p in doc.paragraphs:
        if p.text:
            yield p.text

def docx_bytes_to_pdf_bytes(docx_bytes: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = os.path.join(tmpdir, "input.docx")
        pdf_path = os.path.join(tmpdir, "output.pdf")

        with open(docx_path, "wb") as f:
            f.write(docx_bytes)

        convert(docx_path, pdf_path)
        with open(pdf_path, "rb") as f:
            return f.read()
