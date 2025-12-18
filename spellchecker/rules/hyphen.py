from __future__ import annotations
import re
from typing import Set, List, Tuple

HYPHENS = ("-", "‐", "-")

def fix_hyphenation_block(text: str) -> str:
    return re.sub(r"([A-Za-z]{2,})-\s*\n\s*([A-Za-z]{2,})", r"\1\2", text)

def fix_hyphenation_block_with_vocab(text: str, valid_join_vocab: Set[str]) -> str:
    pattern = re.compile(r"(?i)([a-z]{2,})[-‐-]\s+([a-z]{2,})")

    def repl(m: re.Match) -> str:
        joined = (m.group(1) + m.group(2)).lower()
        return joined if joined in valid_join_vocab else m.group(0)

    return pattern.sub(repl, text)

def protect_hyphen_join_spans_docx(
    triples: List[Tuple[str, str, str, str]],
    valid_join_vocab: Set[str],
) -> Set[int]:
    protected: Set[int] = set()
    toks_norm = [t[0] for t in triples]
    toks_orig = [t[1] for t in triples]

    for i in range(len(triples) - 1):
        left_norm = toks_norm[i]
        right_norm = toks_norm[i + 1]
        left_orig = toks_orig[i] or ""

        if not left_orig.endswith(HYPHENS):
            continue
        if not left_norm.isalpha() or not right_norm.isalpha():
            continue

        joined = left_norm + right_norm
        if joined in valid_join_vocab:
            protected.add(i)
            protected.add(i + 1)

    return protected
