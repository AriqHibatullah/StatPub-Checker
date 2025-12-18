from __future__ import annotations
from typing import Set
from spellchecker.rules.skip import should_skip_token
from spellchecker.settings import Settings

_EN_SUFFIX_HINTS = ("tion", "sion", "ment", "ness", "ship", "able", "ible", "ally", "ically", "ing", "ed")
_EN_PREFIX_HINTS = ("pre", "post", "inter", "trans", "multi", "non", "anti", "sub", "super", "hyper", "micro", "macro")

def looks_englishish(tok: str, english_vocab: Set[str], cfg: Settings, snippet: str = "") -> bool:
    if not tok or should_skip_token(tok, cfg):
        return False
    if tok in english_vocab:
        return True

    if "-" in tok or "_" in tok:
        if any("a" <= c <= "z" for c in tok) and len(tok) >= 5:
            return True

    if len(tok) >= 6:
        for suf in _EN_SUFFIX_HINTS:
            if tok.endswith(suf):
                return True
        for pref in _EN_PREFIX_HINTS:
            if tok.startswith(pref):
                return True

    if snippet:
        if any(x in snippet for x in ("et al", "doi", "vol.", "no.", "pp.", "http", "https")):
            return True

    return False
