from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import streamlit as st
from supabase import create_client


@dataclass(frozen=True)
class SBStorageCfg:
    url: str
    service_role_key: str
    bucket: str
    manifest_path: str


@st.cache_resource
def _sb_cfg() -> SBStorageCfg:
    return SBStorageCfg(
        url=st.secrets["URL"],
        service_role_key=st.secrets["ROLE_KEY"],
        bucket=st.secrets.get("DATA_BUCKET", "data"),
        manifest_path=st.secrets.get("MANIFEST_PATH", "manifest.json"),
    )


@st.cache_resource
def _sb_client():
    cfg = _sb_cfg()
    return create_client(cfg.url, cfg.service_role_key)


def _download_bytes(path: str) -> bytes:
    cfg = _sb_cfg()
    sb = _sb_client()
    return sb.storage.from_(cfg.bucket).download(path)


@st.cache_data(show_spinner=False)
def load_manifest() -> Dict[str, Any]:
    cfg = _sb_cfg()
    b = _download_bytes(cfg.manifest_path)
    return json.loads(b.decode("utf-8"))


def _parse_txt_set_from_bytes(b: bytes) -> set[str]:
    out: set[str] = set()
    text = b.decode("utf-8", errors="ignore")
    for line in text.splitlines():
        w = line.strip().lower()
        if w:
            out.add(w)
    return out


@st.cache_data(show_spinner=False)
def load_txt_set_from_storage(path: str, version: str) -> set[str]:
    b = _download_bytes(path)
    return _parse_txt_set_from_bytes(b)


def download_to_tempfile(path: str, suffix: str, version: str) -> Path:
    b = _download_bytes(path)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(b)
    tmp.flush()
    tmp.close()
    return Path(tmp.name)

