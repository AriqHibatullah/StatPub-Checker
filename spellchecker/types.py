from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Finding:
    file: str
    page: str
    token: str
    snippet: str
    status: str
    suggestions: List[Dict]
