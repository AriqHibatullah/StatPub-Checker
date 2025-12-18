from __future__ import annotations
from typing import Dict, Any, List, Optional

# You already have SuggestEngine in suggest.py at project root.
# This wrapper only normalizes keys so downstream code can rely on:
# - suggestions[i]["suggestion"] and suggestions[i]["confidence"]
try:
    from suggest import SuggestEngine  # type: ignore
except Exception as e:  # pragma: no cover
    SuggestEngine = None  # type: ignore

def build_engine() -> Any:
    if SuggestEngine is None:
        raise ImportError("SuggestEngine not found. Make sure suggest.py is available in PYTHONPATH.")
    return SuggestEngine()

def normalize_suggestions(suggs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for s in suggs or []:
        cand = s.get("suggestion") or s.get("term") or s.get("word")
        if not cand:
            continue
        out.append({
            "suggestion": cand,
            "term": cand,
            "confidence": s.get("confidence"),
            "_synthetic": s.get("_synthetic", False),
            **{k:v for k,v in s.items() if k not in ("suggestion","term","word")}
        })
    return out

def suggest(eng: Any, query: str, topk: int) -> Dict[str, Any]:
    res = eng.suggest(query, topk=topk) or {}
    res["suggestions"] = normalize_suggestions(res.get("suggestions", []))
    return res
