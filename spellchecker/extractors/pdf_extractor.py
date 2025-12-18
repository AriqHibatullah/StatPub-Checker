from __future__ import annotations
from typing import Iterable, Tuple
import pdfplumber

def iter_pdf_pages_raw(path: str) -> Iterable[Tuple[int, str]]:
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            t = page.extract_text() or ""
            if t.strip():
                yield i, t
