from __future__ import annotations
import os, json, csv as _csv
from typing import Set, Dict

def load_txt_set(path: str) -> Set[str]:
    if not path or not os.path.exists(path):
        return set()
    out: Set[str] = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            w = line.strip().lower()
            if w and not w.startswith("#"):
                out.add(w)
    return out

def load_kbbi_words(csv_path: str) -> Set[str]:
    if not csv_path or not os.path.exists(csv_path):
        return set()
    words: Set[str] = set()
    with open(csv_path, encoding="utf-8") as f:
        reader = _csv.reader(f)
        header = next(reader, None)

        col_idx = 0
        if header:
            lower = [h.strip().lower() for h in header]
            for key in ("word", "kata", "entry", "lemma"):
                if key in lower:
                    col_idx = lower.index(key)
                    break

        for row in reader:
            if not row or col_idx >= len(row):
                continue
            w = (row[col_idx] or "").strip().lower()
            if w:
                words.add(w)
    return words

def load_unigram_freq(path: str) -> Dict[str, int]:
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "freq" in data and isinstance(data["freq"], dict):
        return {k: int(v) for k, v in data["freq"].items()}
    if isinstance(data, dict):
        out: Dict[str, int] = {}
        for k, v in data.items():
            if k == "__meta__":
                continue
            if isinstance(v, int):
                out[k] = v
        return out
    return {}
