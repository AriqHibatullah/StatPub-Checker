from __future__ import annotations
import re, unicodedata
from typing import Iterable, Tuple, List, Set

RE_PUNCT = re.compile(r"[^\w\s]+", re.UNICODE)
RE_URL = re.compile(r"(?i)\b(?:https?://|ftp://|www\.)\S+")
RE_DOMAIN = re.compile(
    r"(?i)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"(?:ac\.id|co\.id|go\.id|or\.id|sch\.id|web\.id|id|com|org|net|edu|gov|info)\b"
)

_SUBSCRIPT_MAP = str.maketrans({
    "₀":"0","₁":"1","₂":"2","₃":"3","₄":"4","₅":"5","₆":"6","₇":"7","₈":"8","₉":"9",
    "ₐ":"a","ₑ":"e","ₕ":"h","ᵢ":"i","ⱼ":"j","ₖ":"k","ₗ":"l","ₘ":"m","ₙ":"n",
    "ₒ":"o","ₚ":"p","ₛ":"s","ₜ":"t","ᵤ":"u","ᵥ":"v","ₓ":"x",
})

def protect_urls(text: str) -> str:
    text = RE_URL.sub(" __URL__ ", text)
    text = RE_DOMAIN.sub(" __URL__ ", text)
    return text

def normalize_math_text(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.translate(_SUBSCRIPT_MAP)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def normalize_text(s: str) -> str:
    s = normalize_math_text(s)
    s = protect_urls(s)
    s = s.replace("\u00a0", " ")
    s = s.replace("\u00ad", "")

    # gelar bertitik -> underscore
    s = re.sub(r"\b([A-Za-z]{1,4})\.([A-Za-z]{1,6})\.([A-Za-z]{1,6})\.?\b", r"\1_\2_\3", s)
    s = re.sub(r"\b([A-Za-z]{1,4})\.([A-Za-z]{1,6})\.?\b", r"\1_\2", s)

    # reduplikasi: masing-masing -> masing_masing
    s = re.sub(r"\b([A-Za-z]+)-([A-Za-z]+)\b", r"\1_\2", s)

    return s.lower()

def normalize_text_keep_case(s: str) -> str:
    s = normalize_math_text(s)
    s = protect_urls(s)
    s = s.replace("\u00a0", " ").replace("\u00ad", "")
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u02BC", "'").replace("`", "'")
    s = s.replace("'", "")

    s = re.sub(r"\b([A-Za-z]{1,4})\.([A-Za-z]{1,6})\.([A-Za-z]{1,6})\.?\b", r"\1_\2_\3", s)
    s = re.sub(r"\b([A-Za-z]{1,4})\.([A-Za-z]{1,6})\.?\b", r"\1_\2", s)
    s = re.sub(r"\b([A-Za-z]+)-([A-Za-z]+)\b", r"\1_\2", s)
    return s

def tokenize_with_context(text: str, window: int = 120):
    raw = normalize_text(text)
    cleaned = RE_PUNCT.sub(" ", raw)

    for m in re.finditer(r"\S+", cleaned):
        tok = m.group(0).strip()
        if not tok:
            continue
        start = max(0, m.start() - window)
        end = min(len(raw), m.end() + window)
        snippet_raw = raw[start:end].strip().lower()
        snippet = cleaned[start:end].strip().lower()
        yield tok.lower(), snippet, snippet_raw

def tokenize_docx_paragraph_with_context(text: str, window: int = 45):
    raw = normalize_text_keep_case(text)
    cleaned = RE_PUNCT.sub(" ", raw)

    out = []
    for m in re.finditer(r"\S+", cleaned):
        tok_orig = m.group(0).strip()
        if not tok_orig:
            continue
        tok_norm = tok_orig.lower()

        start = max(0, m.start() - window)
        end = min(len(raw), m.end() + window)

        snippet_raw = raw[start:end].strip().lower()
        snippet_clean = cleaned[start:end].strip().lower()

        out.append((tok_norm, tok_orig, snippet_clean, snippet_raw))
    return out
