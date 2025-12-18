from __future__ import annotations
import re

RE_ADDR_INLINE = re.compile(r"(?i)\balamat\s*:\s*\S")

def should_skip_address_token(tok: str, snippet_raw: str) -> bool:
    if not snippet_raw:
        return False
    s = snippet_raw.lower()
    if not RE_ADDR_INLINE.search(s):
        return False
    after = re.split(r"(?i)\balamat\s*:\s*", s, maxsplit=1)
    if len(after) < 2:
        return False
    addr_part = after[1]
    return bool(re.search(rf"\b{re.escape(tok.lower())}\b", addr_part))

RE_PAREN_AUTHOR_VERB = re.compile(
    r"\(\s*([a-z][a-z'’\-]+(?:\s+[a-z][a-z'’\-]+){0,3})\s*\)\s*"
    r"(mengemukakan|menyatakan|berpendapat|menjelaskan|menegaskan|mengungkapkan|mengatakan)\b",
    re.IGNORECASE
)

def should_skip_paren_author_verb(tok: str, snippet_raw: str) -> bool:
    if not tok or not snippet_raw:
        return False
    s = snippet_raw.lower()
    for m in RE_PAREN_AUTHOR_VERB.finditer(s):
        names = m.group(1).lower().split()
        if tok.lower() in names:
            return True
    return False

YEAR = r"(?:1[7-9]\d{2}|20\d{2})"
NAME_PARTICLES = r"(?:bin|binti|ibn|van|von|de|da|di|del|della|al)"
NAME_TOKEN = r"(?:[A-Za-z][A-Za-z'’\-\.]*)"
AUTHOR_CORE = rf"""
{NAME_TOKEN}
(?:\s+(?:{NAME_PARTICLES}\s+)?{NAME_TOKEN}){{0,4}}
(?:\s*(?:dkk\.?|et\.?\s*al\.?))?
"""

TRIGGERS = r"(?:oleh|hukum|menurut|dari|berdasarkan|rujukan|mengacu\s+pada)"
RE_AUTHOR_YEAR_WITH_TRIGGER = re.compile(
    rf"""
    \b{TRIGGERS}\b\s+
    (?P<author>
        {AUTHOR_CORE}
        (?:\s+(?:dan|&)\s+{AUTHOR_CORE})*
    )
    \s*(?:,\s*|\s+)
    (?P<year>\(?\s*{YEAR}\s*\)?)
    """, re.IGNORECASE | re.VERBOSE
)

RE_AUTHOR_YEAR_NO_TRIGGER = re.compile(
    rf"""
    (?<!\w)
    (?P<author>
        {AUTHOR_CORE}
        (?:\s*,\s*{AUTHOR_CORE})*
        (?:\s*,?\s*(?:dan|&)\s+{AUTHOR_CORE})?
    )
    \s*(?:,\s*|\s+)
    (?P<year>\(?\s*{YEAR}\s*\)?)
    """, re.IGNORECASE | re.VERBOSE
)

RE_PAREN_AUTHORLIST_YEAR = re.compile(
    rf"""
    \(\s*
    (?P<author>
        {AUTHOR_CORE}
        (?:\s*,\s*{AUTHOR_CORE})*
        (?:\s*,?\s*(?:dan|&)\s*{AUTHOR_CORE})?
    )
    \s*(?:,\s*|\s+)
    (?P<year>{YEAR})
    (?:
        \s*,\s*
        (?P<pages>\d{{1,5}}(?:\s*[-–—]\s*\d{{1,5}})?)
    )?
    \s*\)
    """, re.IGNORECASE | re.VERBOSE
)

NAME_WORDS = re.compile(r"[a-z][a-z'’\-]*", re.IGNORECASE)

def should_skip_author_year(tok: str, snippet_raw: str) -> bool:
    if not tok or not snippet_raw or not tok.isalpha():
        return False
    s = snippet_raw.lower()
    t = tok.lower()
    for pat in (RE_AUTHOR_YEAR_WITH_TRIGGER, RE_AUTHOR_YEAR_NO_TRIGGER, RE_PAREN_AUTHORLIST_YEAR):
        for m in pat.finditer(s):
            author_text = (m.group("author") or "").lower()
            names = NAME_WORDS.findall(author_text)
            if t in names:
                return True
    return False
