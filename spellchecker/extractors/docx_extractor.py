from __future__ import annotations
from typing import Iterable, Tuple
from docx import Document

def iter_docx_paragraph_texts(path: str) -> Iterable[str]:
    doc = Document(path)
    for p in doc.paragraphs:
        if p.text:
            yield p.text
