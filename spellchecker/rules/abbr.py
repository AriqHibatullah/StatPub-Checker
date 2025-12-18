from __future__ import annotations
import re
from typing import Set

RE_PAREN_ABBR = re.compile(
    r"\(\s*("
    r"(?:[A-Za-z]{2,10}(?:\.[A-Za-z]{1,6})*\.?)(?:\s*(?:/|-)\s*"
    r"(?:[A-Za-z]{2,10}(?:\.[A-Za-z]{1,6})*\.?)"
    r")*"
    r")\s*\)"
)

def paren_abbrev_from_snippet(snippet: str) -> Set[str]:
    out: Set[str] = set()
    if not snippet:
        return out
    for m in RE_PAREN_ABBR.finditer(snippet):
        inner = m.group(1).strip()
        parts = re.split(r"\s*(?:/|-)\s*", inner)
        for p in parts:
            p = p.strip().lower()
            if not p:
                continue
            p_norm = p.strip(".")
            p_norm = re.sub(r"\.+", "_", p_norm)
            p_norm = re.sub(r"_+", "_", p_norm).strip("_")
            if 2 <= len(p_norm) <= 20:
                out.add(p_norm)
    return out

def is_probable_paren_abbrev(tok: str, snippet: str) -> bool:
    return tok in paren_abbrev_from_snippet(snippet)

RE_ACRONYM_TOKEN = re.compile(
    r"^(?:"
    r"[A-Z]{2,10}(?:\d{1,3})?"
    r"|(?:[A-Z]\.){2,10}[A-Z]?"
    r"|[A-Z]{2,10}(?:/[A-Z]{2,10})+"
    r")$"
)

def is_acronym_like_orig(tok_orig: str) -> bool:
    if not tok_orig:
        return False
    t = tok_orig.strip().strip("()[]{}.,;:")
    if not t:
        return False
    if "/" in t:
        parts = t.split("/")
        if all(p[:1].isupper() and len(p) >= 2 for p in parts):
            return True
    return bool(RE_ACRONYM_TOKEN.match(t))

RE_ACRONYM_IN_TEXT = re.compile(
    r"\b(?:"
    r"(?:[A-Z]\.){2,10}[A-Z]?"
    r"|[A-Z]{2,10}(?:\d{1,3})?"
    r"|[A-Z]{2,10}(?:/[A-Z][A-Za-z]{1,9})+"
    r")\b"
)

def is_acronym_like_pdf(tok_norm: str, snippet_raw: str) -> bool:
    if not tok_norm or not snippet_raw:
        return False
    for m in RE_ACRONYM_IN_TEXT.finditer(snippet_raw):
        a = m.group(0)
        if a.lower() == tok_norm:
            return True
        if a.replace(".", "").lower() == tok_norm:
            return True
    return False
