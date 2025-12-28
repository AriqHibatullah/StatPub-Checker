import re

_BOUNDARY = re.compile(r'(?:^|[.!?])\s*["“”\'’)\]\}]*\s*$', re.UNICODE)
_OPEN_PREFIX = re.compile(r'^[\s"“”‘’\(\[\{]+')

def is_sentence_start_from_offset(raw: str, start_idx: int) -> bool:
    if start_idx <= 0:
        return True
    left = raw[:start_idx].rstrip()
    if not left:
        return True
    tail = left[-40:]
    return bool(_BOUNDARY.search(tail))

def is_capitalization_error(tok_orig: str) -> bool:
    t = (tok_orig or "").strip()
    if not t:
        return False
    t = _OPEN_PREFIX.sub("", t)
    if not t or not t[0].isalpha():
        return False
    letters = "".join(ch for ch in t if ch.isalpha())
    if letters.isupper():
        return False
    return t[0].islower()