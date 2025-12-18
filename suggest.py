# suggest.py
from __future__ import annotations

import os
import json
import math
import pickle
import re
from typing import Dict, List, Tuple, Set, Any

# =========================
# CONFIG
# =========================
INDEX_PKL = "data/models/symspell_id.pkl"
UNIGRAM_JSON = "data/models/unigram_freq.json"

CONFUSIONS_JSON = "data/models/confusion.json"
SPLIT_JOIN_JSON = "data/models/split_join_rules.json"

# Optional filters (untuk "ignore word", bukan untuk kandidat Indo)
OUTPUT_EN_TXT = "data/dictionaries/kamus_inggris.txt"
INPUT_ABBR = "data/dictionaries/singkatan.txt"

# Candidate settings
MAX_EDIT = 2
TOPK = 5
PREFIX_LEN = 7  # must match index build (kalau beda, tetap jalan tapi kurang optimal)

# =========================
# Loaders
# =========================

def load_txt_set(path: str) -> Set[str]:
    if not path or not os.path.exists(path):
        return set()
    out = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            w = line.strip().lower()
            if w and not w.startswith("#"):
                out.add(w)
    return out

def load_json(path: str) -> Any:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def load_unigram_freq(path: str) -> Dict[str, int]:
    data = load_json(path)
    if isinstance(data, dict) and "freq" in data and isinstance(data["freq"], dict):
        # meta format
        return {k: int(v) for k, v in data["freq"].items()}
    if isinstance(data, dict):
        # simple format
        return {k: int(v) for k, v in data.items()}
    return {}

# =========================
# Normalization & basic skip
# =========================

RE_NONWORD = re.compile(r"[^\w\s]+", re.UNICODE)

def normalize_token(tok: str) -> str:
    tok = tok.replace("\u00a0", " ").strip().lower()
    tok = RE_NONWORD.sub("", tok)  # remove punctuation inside token
    return tok

# =========================
# SymSpell deletes + lookup
# =========================

def gen_deletes(term: str, max_edit: int = 2, prefix_len: int = 7) -> Set[str]:
    t = term[:prefix_len] if prefix_len and len(term) > prefix_len else term
    out = {t}
    for _ in range(max_edit):
        new = set()
        for s in out:
            if len(s) <= 1:
                continue
            for i in range(len(s)):
                new.add(s[:i] + s[i+1:])
        out |= new
    out.discard(t)
    return out

def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins = cur[j - 1] + 1
            dele = prev[j] + 1
            sub = prev[j - 1] + (ca != cb)
            cur.append(min(ins, dele, sub))
        prev = cur
    return prev[-1]

def symspell_candidates(term: str, index: Dict[str, Set[str]], vocab: Set[str],
                        max_edit: int = 2, prefix_len: int = 7) -> Set[str]:
    if term in vocab:
        return {term}

    keys = gen_deletes(term, max_edit=max_edit, prefix_len=prefix_len)
    keys.add(term[:prefix_len] if prefix_len and len(term) > prefix_len else term)

    out = set()
    for k in keys:
        if k in index:
            out |= index[k]
    return out

# =========================
# Ranker
# =========================
def base_confidence(dist: int, freq: int) -> float:
    # distance part: 1.0, 0.6, 0.35, 0.2, ...
    dist_part = 1.0 / (1.0 + dist)

    # freq part: saturating (0..1)
    # tau=200 berarti ~200 kemunculan sudah cukup kuat untuk naik tinggi
    tau = 200.0
    freq_part = 1.0 - math.exp(-freq / tau)

    # gabungkan: distance lebih dominan
    conf = 0.7 * dist_part + 0.3 * freq_part
    return max(0.0, min(1.0, conf))

def margin_boost(score1: float, score2: float | None) -> float:
    if score2 is None:
        return 0.15  # hanya ada 1 kandidat -> boost sedikit
    diff = score1 - score2
    # squashing ke 0..0.25
    return 0.25 * (1.0 - math.exp(-max(0.0, diff)))

def is_adjacent_transposition(a: str, b: str) -> bool:
    if len(a) != len(b):
        return False
    diffs = [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y]
    if len(diffs) != 2:
        return False
    (i1, x1, y1), (i2, x2, y2) = diffs
    return i2 == i1 + 1 and x1 == y2 and x2 == y1

def rank_candidates(term: str, cands: Set[str], unigram: Dict[str, int],
                    max_edit: int = 2, topk: int = 5) -> List[Dict[str, Any]]:
    scored: List[Tuple[float, str, int, int]] = []

    for w in cands:
        dist = levenshtein(term, w)
        if dist > max_edit:
            continue

        freq = unigram.get(w, 0)
        score = math.log(freq + 1) - 2.0 * dist

        # bonus jika typo adalah swap karakter bersebelahan
        if is_adjacent_transposition(term, w):
            score += 0.5

        # penalty kalau tidak pernah muncul di unigram
        if freq == 0:
            score -= 1.0

        scored.append((score, w, dist, freq))

    scored.sort(reverse=True)

    # optional: drop freq=0 kalau ada yang freq>0
    has_in_corpus = any(freq > 0 for _, _, _, freq in scored)
    if has_in_corpus:
        scored = [t for t in scored if t[3] > 0]

    if not scored:
        return []

    # compute margin using top-2 scores (after filtering)
    score1 = scored[0][0]
    score2 = scored[1][0] if len(scored) > 1 else None
    boost = margin_boost(score1, score2) if score2 is not None else 0.0

    out = []
    for score, w, dist, freq in scored[:topk]:
        conf = base_confidence(dist, freq)
        if w == scored[0][1]:
            conf = min(1.0, conf + boost)

        out.append({
            "suggestion": w,
            "distance": dist,
            "freq": freq,
            "confidence": round(conf, 3)
        })

    return out

# =========================
# Main Suggest Engine
# =========================

class SuggestEngine:
    def __init__(
        self,
        index_pkl: str = INDEX_PKL,
        unigram_json: str = UNIGRAM_JSON,
        confusions_json: str = CONFUSIONS_JSON,
        split_join_json: str = SPLIT_JOIN_JSON,
        output_en_txt: str = OUTPUT_EN_TXT,
        input_abbr: str = INPUT_ABBR,
    ):
        payload = self._load_index(index_pkl)
        self.index = payload["index"]
        self.vocab = payload["vocab"]
        self.meta = payload.get("__meta__", {})

        self.unigram = load_unigram_freq(unigram_json)
        self.confusions = load_json(confusions_json) or {}
        self.split_join = load_json(split_join_json) or {}

        self.en_vocab = load_txt_set(output_en_txt)
        self.abbr_vocab = load_txt_set(input_abbr)

    def _load_index(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Index not found: {path}. Run build_candidate_index.py first.")
        with open(path, "rb") as f:
            payload = pickle.load(f)
        # payload could be {"__meta__":..., "index":..., "vocab":...}
        if "index" not in payload or "vocab" not in payload:
            raise ValueError("Invalid index payload. Rebuild the index.")
        return payload

    def suggest(self, token: str, topk: int = TOPK, max_edit: int = MAX_EDIT) -> Dict[str, Any]:
        raw = token
        tok = normalize_token(token)

        if not tok:
            return {"token": raw, "normalized": tok, "status": "empty", "suggestions": []}

        # If it's already known (vocab Indo) or it's recognized English/abbr, "ok"
        if tok in self.vocab or tok in self.en_vocab or tok in self.abbr_vocab:
            return {"token": raw, "normalized": tok, "status": "ok", "suggestions": []}

        # 1) Confusions direct map (support both {"a":"b"} and richer dict)
        if tok in self.confusions:
            v = self.confusions[tok]
            if isinstance(v, str):
                suggs = [{"suggestion": v, "distance": levenshtein(tok, v), "freq": self.unigram.get(v, 0)}]
            elif isinstance(v, dict) and "suggestions" in v:
                suggs = [{"suggestion": s, "distance": levenshtein(tok, s), "freq": self.unigram.get(s, 0)}
                         for s in v["suggestions"]]
            else:
                suggs = []
            return {"token": raw, "normalized": tok, "status": "confusion", "suggestions": suggs[:topk]}

        # 2) Split/join direct rule
        if tok in self.split_join:
            v = self.split_join[tok]
            # split_join bisa "di atas" (string) atau dict meta juga
            if isinstance(v, str):
                sug = v
            elif isinstance(v, dict) and "suggestion" in v:
                sug = v["suggestion"]
            else:
                sug = None
            if sug:
                return {
                    "token": raw,
                    "normalized": tok,
                    "status": "split_join",
                    "suggestions": [{"suggestion": sug, "distance": 1, "freq": self.unigram.get(sug, 0)}]
                }

        # 3) SymSpell
        cands = symspell_candidates(tok, self.index, self.vocab, max_edit=max_edit, prefix_len=PREFIX_LEN)
        ranked = rank_candidates(tok, cands, self.unigram, max_edit=max_edit, topk=topk)

        status = "no_candidates" if not ranked else "symspell"
        return {"token": raw, "normalized": tok, "status": status, "suggestions": ranked}


# =========================
# CLI demo (optional)
# =========================
if __name__ == "__main__":
    eng = SuggestEngine()
    print("[INFO] Loaded engine.")
    print("[INFO] Type words to get suggestions. Ctrl+C to exit.\n")
    try:
        while True:
            s = input(">> ").strip()
            if not s:
                continue
            result = eng.suggest(s)
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except KeyboardInterrupt:
        print("\nBye.")

    # eng = SuggestEngine()
    # print("hasil in vocab:", "hasil" in eng.vocab)
    # print("hasil freq:", eng.unigram.get("hasil", 0))
    # print("hail in vocab:", "hail" in eng.vocab)
    # print("hail freq:", eng.unigram.get("hail", 0))
    #