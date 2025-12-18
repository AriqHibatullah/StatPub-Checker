from __future__ import annotations
import re

RE_BIB_CITATION_LINE = re.compile(r"""
    ^\s*
    (
      [A-Z][A-Za-z'’\-]+
      (?:\s+[A-Z][A-Za-z'’\-]+)*
      (?:\s*,\s*[A-Z][A-Za-z\.]{1,6})?
    )
    (?:
      \s*(?:,|&|dan)\s*
      [A-Z][A-Za-z'’\-]+
      (?:\s+[A-Z][A-Za-z'’\-]+)*
      (?:\s*,\s*[A-Z][A-Za-z\.]{1,6})?
    )*
    \s*[\.,]\s*
    (?:\(|\[)?\s*(17|18|19|20)\d{2}\s*(?:\)|\])?
    \s*[\.,]\s*
    """, re.VERBOSE)

def is_bibliography_citation_line(s: str) -> bool:
    return bool(RE_BIB_CITATION_LINE.match((s or "").strip()))
