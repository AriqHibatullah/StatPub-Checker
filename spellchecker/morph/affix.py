from __future__ import annotations
import re
from typing import Dict, Tuple, List, Any

_AFFIX_PREFIXES = [
    "memper", "memp", "meng", "meny", "mem", "men", "me",
    "peng", "peny", "pem", "pen", "pe",
    "ber", "ter", "per",
    "di", "ke", "se",
]
_AFFIX_SUFFIXES = ["kannya", "kan", "an", "nya", "lah", "kah", "pun"]

RE_MAYBE_AFFIXED = re.compile(
    r"^(?:"
    r"di|ke|se|"
    r"ber|ter|per|pe|pen|pem|peng|peny|"
    r"me|mem|men|meng|meny|memp|memper|"
    r"se|ke|di"
    r")"
    r".{3,}$"
    r"|^.{3,}(?:kan|i|an|nya|lah|kah|pun)$"
)

def maybe_affixed_id(tok: str) -> bool:
    if not tok.isalpha():
        return False
    if len(tok) < 5:
        return False
    return bool(RE_MAYBE_AFFIXED.match(tok))

def cached_stem(tok: str, stemmer, cache: dict) -> str:
    s = cache.get(tok)
    if s is not None:
        return s
    s = stemmer.stem(tok)
    cache[tok] = s
    return s

def deaffix_for_suggest(tok: str, max_rounds: int = 2) -> Tuple[str, Dict[str, Any]]:
    w = tok
    info: Dict[str, Any] = {"prefixes": [], "suffixes": [], "fixed_boundary": False}

    def _fix_double_boundary(raw: str, pfx: str) -> str:
        if not pfx or len(raw) <= len(pfx):
            return raw
        tail = raw[len(pfx):]
        if tail and pfx[-1] == tail[0]:
            return raw[:len(pfx)] + tail[1:]
        return raw

    for s in sorted(_AFFIX_SUFFIXES, key=len, reverse=True):
        if w.endswith(s) and len(w) > len(s) + 2:
            info["suffixes"].append(s)
            w = w[:-len(s)]
            break

    # special: -nya (repair common "anya" boundary)
    if info["suffixes"] and info["suffixes"][-1] == "nya":
        if w.endswith("a"):
            w = w + "n"
        if len(w) < 3:
            return tok, info
        return w, info

    for _ in range(max_rounds):
        w0 = w

        for p in sorted(_AFFIX_PREFIXES, key=len, reverse=True):
            if w.startswith(p) and len(w) > len(p) + 2:
                fixed = _fix_double_boundary(w, p)
                if fixed != w:
                    info["fixed_boundary"] = True
                    w = fixed
                info["prefixes"].append(p)
                w = w[len(p):]
                break

        for s in sorted(_AFFIX_SUFFIXES, key=len, reverse=True):
            if w.endswith(s) and len(w) > len(s) + 2:
                info["suffixes"].append(s)
                w = w[:-len(s)]
                break

        if w == w0:
            break

    if len(w) < 3:
        return tok, info
    return w, info

def top1_conf(suggs: List[Dict[str, Any]]) -> float:
    if not suggs:
        return -1.0
    c = suggs[0].get("confidence")
    return float(c) if isinstance(c, (int, float)) else -1.0

def pick_best_suggest_query_for_nya(tok: str, eng, topk: int, suggest_fn):
    base = tok[:-3]
    candidates = [base]
    if tok.endswith("anya") and base.endswith("a") and len(base) >= 3:
        candidates.append(base + "n")

    best_q = candidates[0]
    best_res = suggest_fn(eng, best_q, topk)

    for q in candidates[1:]:
        res = suggest_fn(eng, q, topk)

        if best_res.get("status") != "ok" and res.get("status") == "ok":
            best_q, best_res = q, res
            continue
        if best_res.get("status") == "ok" and res.get("status") != "ok":
            continue

        if top1_conf(res.get("suggestions", [])) > top1_conf(best_res.get("suggestions", [])):
            best_q, best_res = q, res

    return best_q, best_res

def reaffix_suggestion(stem_candidate: str, info: Dict[str, Any]) -> str:
    out = stem_candidate
    for s in reversed(info.get("suffixes", [])):
        out = out + s
    for p in reversed(info.get("prefixes", [])):
        out = p + out
    return out



def sugss_get_word(d: Dict[str, Any]):
    return d.get("word")

def top_term(suggs: List[Dict[str, Any]]) -> str:
    if not suggs:
        return ""
    return (suggs[0].get("term") or suggs[0].get("suggestion") or sugss_get_word(suggs[0]) or "").lower()

def is_synth_top(suggs: List[Dict[str, Any]]) -> bool:
    return bool(suggs) and bool(suggs[0].get("_synthetic"))
