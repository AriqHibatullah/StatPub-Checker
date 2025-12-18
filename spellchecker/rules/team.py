from __future__ import annotations
import re

def is_tim_penyusun_page(page_text: str) -> bool:
    t = re.sub(r"\s+", " ", page_text).upper()
    head = t[:3000]
    head_compact = re.sub(r"[^A-Z]", "", head)
    return (
        ("TIM PENYUSUN" in head)
        or ("TIMPENYUSUN" in head_compact)
        or ("DEWAN REDAKSI" in head)
        or ("PENYUNTING" in head)
        or ("EDITOR" in head)
    )

# Simple filters for DOCX sections
RE_DAFTAR_PUSTAKA = re.compile(r"^\s*(daftar\s+pustaka|references|bibliography)\s*$", re.IGNORECASE)
RE_TIM_PENYUSUN = re.compile(r"^\s*(?:tim\s+penyusun|dewan\s+redaksi|penyusun\s+naskah|susunan\s+redaksi|tim\s+penulis|tim\s+editor)\s*:?\.?\s*$", re.IGNORECASE)
RE_KATA_PENGANTAR = re.compile(r"^\s*(?:kata\s+pengantar|pengantar|preface|foreword)\s*:?\.?\s*$", re.IGNORECASE)

# Name+degree line removal for PDF crew pages
NAME_DEGREE_LINE_RE = re.compile(
    r"""^\s*
    (?P<name>[A-Za-z][A-Za-z'\-\.]+(?:\s+[A-Za-z][A-Za-z'\-\.]+){0,4})
    \s*,\s*
    (?P<degrees>(?:(?:[A-Za-z]{1,4}\.(?:[A-Za-z]{1,6}\.)+)(?:\s*,\s*)?){1,3})
    \s*$""",
    re.VERBOSE
)
RE_ONLY_DEGREE_LINE = re.compile(
    r"^\s*(?:[A-Za-z]{1,4}\.(?:[A-Za-z]{1,6}\.)+)(?:\s*,\s*(?:[A-Za-z]{1,4}\.(?:[A-Za-z]{1,6}\.)+))*\s*$"
)

def drop_name_degree_lines(page_text: str) -> str:
    out_lines = []
    for line in page_text.splitlines():
        raw = line.strip()
        if not raw:
            continue
        cleaned = re.sub(r"\s+[A-Za-z]{1,3}\s*$", "", raw)
        if NAME_DEGREE_LINE_RE.match(cleaned) or RE_ONLY_DEGREE_LINE.match(cleaned):
            continue
        out_lines.append(raw)
    return "\n".join(out_lines)
