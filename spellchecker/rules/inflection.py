from __future__ import annotations
from typing import Set, List
from spellchecker.rules.skip import should_skip_token
from spellchecker.settings import Settings

_ENCLITICS = ("lah", "kah", "tah", "pun", "nya", "kan", "i", "an")
_PREFIXES_SIMPLE = ("di", "ke", "se", "ber", "ter", "per", "pe", "me")

def _strip_enclitic(tok: str) -> str:
    for suf in _ENCLITICS:
        if tok.endswith(suf) and len(tok) > len(suf) + 2:
            return tok[: -len(suf)]
    return tok

def _strip_suffix_once(tok: str) -> List[str]:
    cands = {tok}
    if tok.endswith("nya") and len(tok) > 5:
        cands.add(tok[:-3])
    for suf in ("kan", "i", "an"):
        if tok.endswith(suf) and len(tok) > len(suf) + 2:
            base = tok[: -len(suf)]
            cands.add(base)
            if base.endswith("nya") and len(base) > 5:
                cands.add(base[:-3])
    return list(cands)

def _men_peN_stem_candidates(word: str, prefix_type: str) -> List[str]:
    cands = set()
    if word.startswith(prefix_type + "ny") and len(word) > 5:
        rest = word[len(prefix_type + "ny"):]
        cands.add("s" + rest)
        cands.add(rest)
    if word.startswith(prefix_type + "ng") and len(word) > 5:
        rest = word[len(prefix_type + "ng"):]
        cands.add(rest)
        cands.add("k" + rest)
    if word.startswith(prefix_type + "n") and len(word) > 4:
        rest = word[len(prefix_type + "n"):]
        cands.add(rest)
        cands.add("t" + rest)
    if word.startswith(prefix_type + "m") and len(word) > 4:
        rest = word[len(prefix_type + "m"):]
        cands.add(rest)
        cands.add("p" + rest)
    return [c for c in cands if len(c) >= 3]

def is_probably_valid_inflection(tok: str, known_vocab: Set[str], cfg: Settings) -> bool:
    if not tok or should_skip_token(tok, cfg):
        return False
    if tok in known_vocab:
        return True

    t0 = _strip_enclitic(tok)
    suffix_stripped = _strip_suffix_once(t0)

    for t in suffix_stripped:
        if t in known_vocab:
            return True

        for pref in _PREFIXES_SIMPLE:
            if t.startswith(pref) and len(t) > len(pref) + 2:
                base = t[len(pref):]
                if base in known_vocab:
                    return True

        if t.startswith("me") and len(t) > 4:
            for cand in _men_peN_stem_candidates(t, "me"):
                if cand in known_vocab:
                    return True

        if t.startswith("pe") and len(t) > 4:
            for cand in _men_peN_stem_candidates(t, "pe"):
                if cand in known_vocab:
                    return True

        for pref in ("ber", "ter", "per"):
            if t.startswith(pref) and len(t) > len(pref) + 2:
                base = t[len(pref):]
                if base in known_vocab:
                    return True

        if t.startswith("ke") and t.endswith("an") and len(t) > 6:
            mid = t[2:-2]
            if mid in known_vocab:
                return True
        if t.startswith("pe") and t.endswith("an") and len(t) > 6:
            mid = t[2:-2]
            if mid in known_vocab:
                return True

    return False
