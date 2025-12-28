from typing import List, Tuple, Optional, Dict, Any

def detect_space_error_nya(
    triples: List[Tuple[str, str, str, str, int, int]],
    idx: int,
) -> Optional[Dict[str, Any]]:
    if idx <= 0 or idx >= len(triples):
        return None

    tok, tok_orig, snippet, snippet_raw, start, end = triples[idx]
    if tok != "nya":
        return None

    prev_tok, prev_orig, *_rest = triples[idx - 1]

    if not prev_tok or not prev_tok.isalpha():
        return None

    prev_orig_clean = (prev_orig or "").strip()
    while prev_orig_clean and not prev_orig_clean[-1].isalnum():
        prev_orig_clean = prev_orig_clean[:-1]

    if not prev_orig_clean:
        return None

    join_term = prev_orig_clean + (tok_orig or "nya")

    return {
        "join_term": join_term,
        "prev": prev_orig_clean,
        "idx_prev": idx - 1,
        "idx_nya": idx,
    }