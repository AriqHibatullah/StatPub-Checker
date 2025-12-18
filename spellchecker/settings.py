from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class Settings:
    # Output gating
    topk: int = 3
    max_findings_per_file: int = 2000
    show_only_top1_if_conf_ge: float = 0.72

    # English gating (optional)
    en_min_freq: int = 3

    # Token filtering
    min_token_len: int = 2
    max_token_len: int = 40

    # Tim penyusun (PDF)
    enable_tim_penyusun_filter: bool = True
    tim_page_limit: int = 8
    crew_pages_span: int = 3

    # One-pass auto glossary
    auto_glossary_min_freq: int = 3
    auto_glossary_conf_strong: float = 0.72
    auto_glossary_conf_weak: float = 0.45
    auto_glossary_margin: float = 0.18
    auto_glossary_max_doc_terms: int = 500
    auto_glossary_min_token_len: int = 3
    auto_glossary_max_token_len: int = 30

    # Acronym candidate threshold
    abbr_cand_min_count: int = 3

    # Special status
    status_affix_typo: str = "affix_typo"

    debug: bool = False
