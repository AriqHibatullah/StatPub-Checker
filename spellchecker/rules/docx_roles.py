from __future__ import annotations
import re
from typing import Set, List, Tuple
from spellchecker.rules.skip import should_skip_token, STOPWORDS_NAME_BOUNDARY
from spellchecker.settings import Settings

ROLE_LABELS = [
    ("pengarah",),
    ("penanggung", "jawab"),
    ("penyunting",),
    ("penyunting", "editor"),
    ("editor",),
    ("penulis",),
    ("penulis", "naskah"),
    ("pengelola", "data"),
    ("pengolah", "data"),
    ("penata", "letak", "dan", "infografis"),
    ("penata", "letak"),
    ("pembuat", "infografis"),
    ("penerjemah",)
]

ROLE_BOUNDARY_WORDS = {
    "dan","atau","&","dkk","dkk.","et","al","al.",
    "bab","pendahuluan","metodologi","metode","sistematika","tujuan",
}

def is_role_header_paragraph(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    t = re.sub(r"\s*:\s*$", "", t)
    t = t.replace("/", " ")
    t = t.replace("&", " dan ")
    t = re.sub(r"[^a-z\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    if len(t) > 60:
        return False
    if len(t.split()) > 6:
        return False

    toks = t.split()
    for lab in ROLE_LABELS:
        L = len(lab)
        if toks[:L] == list(lab):
            return True

    strong_single = {"pengarah", "penyunting", "editor", "penulis"}
    if len(toks) <= 2 and any(w in toks for w in strong_single):
        return True

    return False

def protect_name_run_in_paragraph(
    triples: List[Tuple[str, str, str, str]],
    known_vocab: Set[str],
    english_vocab: Set[str],
    cfg: Settings,
    min_titlecase: int = 2,
    max_take: int = 8,
) -> Set[int]:
    protected: Set[int] = set()
    toks_norm = [t[0] for t in triples]
    toks_orig = [t[1] for t in triples]

    titlecase_count = 0
    taken = 0

    for i, (tn, to) in enumerate(zip(toks_norm, toks_orig)):
        if taken >= max_take:
            break
        if should_skip_token(tn, cfg):
            break
        if not tn.isalpha():
            break
        if tn in ROLE_BOUNDARY_WORDS or tn in STOPWORDS_NAME_BOUNDARY:
            break
        if tn in known_vocab or tn in english_vocab:
            # if vocab hit, we don't consider this a pure name list anymore
            if protected:
                break
            return set()

        if to[:1].isupper() and len(tn) >= 2:
            titlecase_count += 1
            protected.add(i)
            taken += 1
            continue

        if protected:
            break
        return set()

    return protected if titlecase_count >= min_titlecase else set()
