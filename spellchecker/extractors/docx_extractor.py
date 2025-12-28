from __future__ import annotations
from typing import Iterable, Tuple
from docx import Document
from pathlib import Path
import os, tempfile, subprocess

def iter_docx_paragraph_texts(path: str) -> Iterable[str]:
    doc = Document(path)
    for p in doc.paragraphs:
        if p.text:
            yield p.text

def docx_bytes_to_pdf_bytes(docx_bytes: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        docx_path = tmpdir / "input.docx"
        docx_path.write_bytes(docx_bytes)

        subprocess.run(
            ["soffice", "--headless", "--nologo", "--nofirststartwizard",
             "--convert-to", "pdf", "--outdir", str(tmpdir), str(docx_path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        pdf_path = tmpdir / "input.pdf"
        if not pdf_path.exists():
            pdfs = list(tmpdir.glob("*.pdf"))
            if not pdfs:
                raise RuntimeError("LibreOffice tidak menghasilkan PDF.")
            pdf_path = pdfs[0]

        return pdf_path.read_bytes()
