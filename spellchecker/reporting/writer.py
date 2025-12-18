from __future__ import annotations
import csv, json, time
from typing import List, Dict, Any, Optional
from spellchecker.types import Finding

def findings_to_rows(findings: List[Finding], topk: int) -> List[List[Any]]:
    rows = []
    for fd in findings:
        sug = fd.suggestions or []
        row = [fd.file, fd.page, fd.token, fd.status]
        for i in range(topk):
            if i < len(sug):
                row += [sug[i].get("suggestion", ""), sug[i].get("confidence", "")]
            else:
                row += ["", ""]
        row.append(fd.snippet)
        rows.append(row)
    return rows

def write_csv(path: str, findings: List[Finding], topk: int):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        header = ["file","page","token","status"]
        for i in range(1, topk+1):
            header += [f"suggestion_{i}", f"confidence_{i}"]
        header += ["snippet"]
        w.writerow(header)
        for row in findings_to_rows(findings, topk):
            w.writerow(row)

def write_jsonl(path: str, findings: List[Finding], meta: Dict[str, Any]):
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"__meta__": meta}, ensure_ascii=False) + "\n")
        for fd in findings:
            f.write(json.dumps({
                "file": fd.file,
                "page": fd.page,
                "token": fd.token,
                "status": fd.status,
                "snippet": fd.snippet,
                "suggestions": fd.suggestions,
            }, ensure_ascii=False) + "\n")
