import pandas as pd

_BAD_STRINGS = {"", "none", "null", "nan", "-", "—", "n/a"}

def _clean_str(x) -> str:
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    s = str(x).strip()
    if s.lower() in _BAD_STRINGS:
        return ""
    return s

def resolve_fix_final(row) -> str:
    choice = _clean_str(row.get("fix_choice", ""))
    manual = _clean_str(row.get("fix_custom", ""))

    s1 = _clean_str(row.get("suggestion_1", ""))
    s2 = _clean_str(row.get("suggestion_2", ""))
    s3 = _clean_str(row.get("suggestion_3", ""))

    if choice:
        c = choice.strip().lower()

        if c in {"saran 1", "1", "suggestion_1"}:
            return s1 or manual or s1
        if c in {"saran 2", "2", "suggestion_2"}:
            return s2 or manual or s1
        if c in {"saran 3", "3", "suggestion_3"}:
            return s3 or manual or s1
        if "manual" in c or c in {"custom", "➕ manual"}:
            return manual or s1

        return manual or s1

    if manual:
        return manual

    return s1
