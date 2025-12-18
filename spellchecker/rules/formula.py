from __future__ import annotations
import re
from typing import Any, Dict, Optional, List, Tuple, Set
from spellchecker.rules.text import normalize_math_text

RE_VAR_DEF = re.compile(
    r"^\s*(?:[-–—•]\s*)?\(?\s*"
    r"([A-Za-z]{1,3}(?:_[A-Za-z0-9]{1,3})?(?:\d{1,2})?)"
    r"\s*\)?\s*(?:=|:)\s+"
)

MATH_OP_CHARS = set("=+-*/^<>∑Σ√()[]|·×÷±≈≠≤≥")

def looks_like_formula_line(s: str) -> bool:
    t = normalize_math_text(s)
    if not t:
        return False
    if "=" in t:
        sep = "="
    elif ":" in t:
        sep = ":"
    else:
        return False
    lhs, rhs = t.split(sep, 1)
    lhs, rhs = lhs.strip(), rhs.strip()
    if not lhs or not rhs:
        return False
    if len(lhs) > 20 or len(lhs.split()) > 2:
        return False
    ops_rhs = sum(ch in MATH_OP_CHARS for ch in rhs)
    words_rhs = [w for w in rhs.split() if any(c.isalpha() for c in w)]
    if ops_rhs >= 1 and len(words_rhs) <= 2:
        return True
    return False
