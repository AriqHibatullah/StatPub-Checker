from __future__ import annotations
import re
from typing import Set
from spellchecker.settings import Settings
from spellchecker.rules.text import RE_URL, RE_DOMAIN

RE_NUMERIC = re.compile(r"^\d+([.,]\d+)*$", re.UNICODE)
RE_ALNUM_CODE = re.compile(r"^[a-z]*\d+[a-z0-9\-\/]*$", re.I)
RE_ROMANLIKE = re.compile(r"^(?=[mdclxvi]+$)[mdclxvi]+$", re.I)
RE_DEGREE_TOKEN = re.compile(r"^[a-z]{1,4}(?:_[a-z]{1,6}){1,4}$", re.IGNORECASE)
REDUP_RE = re.compile(r"^([a-z]+)_([a-z]+)$", re.IGNORECASE)

STOPWORDS_NAME_BOUNDARY = {
    "oleh","dari","kepada","pada","dan","yang","sebagai","untuk","dengan",
    "dalam","atau","di","ke","dari","ini","itu","adalah","merupakan"
}

def should_skip_token(tok: str, cfg: Settings) -> bool:
    if len(tok) < cfg.min_token_len or len(tok) > cfg.max_token_len:
        return True
    if RE_NUMERIC.match(tok):
        return True
    if RE_ALNUM_CODE.match(tok):
        return True
    if RE_ROMANLIKE.match(tok):
        return True
    if RE_URL.match(tok) or RE_DOMAIN.match(tok):
        return True
    if tok == "__url__":
        return True
    return False

def is_valid_reduplication(tok: str, known_vocab: Set[str]) -> bool:
    m = REDUP_RE.match(tok)
    if not m:
        return False
    a, b = m.group(1).lower(), m.group(2).lower()
    if a == b:
        return True
    return (a in known_vocab) and (b in known_vocab)
