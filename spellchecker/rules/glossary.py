from __future__ import annotations
from typing import Set, Dict, Any, List
from spellchecker.settings import Settings
from spellchecker.rules.skip import STOPWORDS_NAME_BOUNDARY

def is_doc_term_candidate(tok: str, known_vocab: Set[str], english_vocab: Set[str], cfg: Settings) -> bool:
    if not tok.isalpha():
        return False
    if len(tok) < cfg.auto_glossary_min_token_len or len(tok) > cfg.auto_glossary_max_token_len:
        return False
    if tok in known_vocab or tok in english_vocab:
        return False
    if tok in STOPWORDS_NAME_BOUNDARY:
        return False
    return True

def is_strong_typo_from_suggestions(suggs: List[Dict[str, Any]], cfg: Settings) -> bool:
    if not suggs:
        return False
    top1 = suggs[0].get("confidence")
    top2 = suggs[1].get("confidence") if len(suggs) > 1 else None

    if isinstance(top1, (int, float)) and top1 >= cfg.auto_glossary_conf_strong:
        return True
    if isinstance(top1, (int, float)) and isinstance(top2, (int, float)):
        if (top1 - top2) >= cfg.auto_glossary_margin and top1 >= cfg.auto_glossary_conf_weak:
            return True
    return False
