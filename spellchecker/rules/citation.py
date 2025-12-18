from __future__ import annotations
import re
from typing import List, Set, Tuple
from spellchecker.rules.skip import STOPWORDS_NAME_BOUNDARY
from spellchecker.rules.skip import should_skip_token
from spellchecker.settings import Settings

RE_YEAR_PAREN = re.compile(r"\(\s*(?:1[7-9]\d{2}|20\d{2})\s*\)")
RE_PAREN_NAME = re.compile(r"\(\s*[a-z][a-z'’\-]+(?:\s+[a-z][a-z'’\-]+){0,3}\s*\)")

CITATION_TRIGGERS = (
    "menurut", "berdasarkan", "mengacu", "rujuk", "rujukan",
    "teori", "model", "metode", "pendekatan", "konsep", "hukum",
)

def is_year_token(t: str, lo: int = 1700, hi: int = 2099) -> bool:
    return t.isdigit() and len(t) == 4 and lo <= int(t) <= hi

def is_citation_like_context(snippet: str) -> bool:
    s = (snippet or "").lower()
    if not any(tr in s for tr in CITATION_TRIGGERS):
        return False
    return bool(RE_YEAR_PAREN.search(s) or RE_PAREN_NAME.search(s))

def protect_citation_spans_docx(
    toks_norm: List[str],
    toks_orig: List[str],
    cfg: Settings,
    max_span: int = 10,
) -> Set[int]:
    protected: Set[int] = set()
    n = len(toks_norm)
    triggers = set(CITATION_TRIGGERS)
    boundary = {"bahwa","yang","tentang","dalam","pada","di","ke","dari","ini","itu","tersebut"}
    connectors = {"&","dan","dkk","dkk.","et","al","al."}

    i = 0
    while i < n:
        if toks_norm[i] not in triggers:
            i += 1
            continue

        j = i + 1
        year_idx = None
        while j < min(n, i + 1 + max_span + 4):
            t = toks_norm[j].strip("()")
            if is_year_token(t, 1700, 2099):
                year_idx = j
                break
            j += 1

        if year_idx is not None:
            start, end = i + 1, year_idx - 1
            if end >= start:
                name_like = 0
                for k in range(start, min(end + 1, start + max_span)):
                    tn = toks_norm[k]
                    if tn in boundary or should_skip_token(tn, cfg):
                        break
                    if tn in connectors:
                        protected.add(k)
                        continue
                    to = toks_orig[k]
                    if to[:1].isupper() and len(tn) >= 3:
                        name_like += 1
                        protected.add(k)
                    else:
                        protected.add(k)

                if name_like == 0:
                    for k in range(start, min(end + 1, start + max_span)):
                        protected.discard(k)

            i = year_idx + 1
            continue

        # fallback: trigger + Name (no year)
        start = i + 1
        end = min(n - 1, i + 1 + 4)
        name_like = 0
        for k in range(start, end + 1):
            tn = toks_norm[k]
            if tn in boundary or should_skip_token(tn, cfg):
                break
            to = toks_orig[k]
            if to[:1].isupper() and len(tn) >= 3:
                name_like += 1
                protected.add(k)
            else:
                break

        if name_like == 0:
            for k in range(start, end + 1):
                protected.discard(k)

        i += 1

    return protected

def should_skip_as_citation_name_pdf(tok: str, snippet: str, known_vocab: Set[str], english_vocab: Set[str], cfg: Settings) -> bool:
    if not is_citation_like_context(snippet):
        return False
    if not tok.isalpha() or len(tok) < 3:
        return False
    if tok in known_vocab or tok in english_vocab:
        return False
    if tok in STOPWORDS_NAME_BOUNDARY:
        return False
    return True
