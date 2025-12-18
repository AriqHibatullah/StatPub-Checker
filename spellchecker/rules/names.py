from __future__ import annotations
import re
from typing import List, Set, Tuple
from spellchecker.rules.skip import STOPWORDS_NAME_BOUNDARY, should_skip_token, RE_DEGREE_TOKEN
from spellchecker.settings import Settings

def _is_name_like_token(tok_orig: str, tok_norm: str, known_vocab: Set[str], cfg: Settings) -> int:
    if not tok_norm or should_skip_token(tok_norm, cfg):
        return -3
    if tok_norm in STOPWORDS_NAME_BOUNDARY:
        return -3

    score = 0
    if tok_orig[:1].isupper() and tok_orig[1:].islower():
        score += 2
    elif tok_orig.isupper() and len(tok_orig) <= 5:
        score += 0
    else:
        score -= 1

    if tok_norm not in known_vocab:
        score += 1
    if len(tok_norm) <= 2:
        score -= 1
    return score

def protect_name_degree_spans(
    toks_norm: List[str],
    toks_orig: List[str],
    known_vocab: Set[str],
    cfg: Settings,
    max_back: int = 5,
    max_forward: int = 4,
    min_span_score: int = 2,
) -> Set[int]:
    protected: Set[int] = set()
    n = len(toks_norm)

    i = 0
    while i < n:
        if not RE_DEGREE_TOKEN.match(toks_norm[i]):
            i += 1
            continue

        left = i - 1
        span_score = 0
        left_count = 0

        while left >= 0 and left_count < max_back:
            tnorm = toks_norm[left]
            torig = toks_orig[left]

            if tnorm in STOPWORDS_NAME_BOUNDARY:
                break
            if should_skip_token(tnorm, cfg):
                break

            s = _is_name_like_token(torig, tnorm, known_vocab, cfg)
            if s < 0:
                break

            span_score += s
            left -= 1
            left_count += 1

        left += 1

        right = i
        right_count = 0
        while right + 1 < n and right_count < max_forward:
            nxt = toks_norm[right + 1]
            if RE_DEGREE_TOKEN.match(nxt):
                right += 1
                right_count += 1
                continue
            break

        span_len = (right - left + 1)
        if span_len >= 2 and span_score >= min_span_score:
            for k in range(left, right + 1):
                protected.add(k)

        i = right + 1

    return protected
