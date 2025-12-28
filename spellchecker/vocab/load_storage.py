from __future__ import annotations

import io
import csv
import json
import pickle
from typing import Dict, Set

import streamlit as st

from spellchecker.vocab.read_storage import download_private_bytes
from spellchecker.pipeline import build_vocabs

def _read_txt_set_from_bytes(b: bytes, encoding: str = "utf-8") -> Set[str]:
    txt = b.decode(encoding, errors="replace")
    out = set()
    for line in txt.splitlines():
        s = line.strip()
        if not s:
            continue
        out.add(s.lower())
    return out

def _read_kbbi_csv_from_bytes(b: bytes, encoding: str = "utf-8") -> Set[str]:
    txt = b.decode(encoding, errors="replace")
    f = io.StringIO(txt)
    reader = csv.DictReader(f)

    out = set()
    for row in reader:
        word = row.get("word").strip()
        if word:
            out.add(word.lower())
    return out

def load_json_from_bytes(b: bytes) -> Any:
    if not b:
        return {}
    return json.loads(b.decode("utf-8", errors="replace"))

def load_unigram_freq_from_obj(data: Any) -> Dict[str, int]:
    if isinstance(data, dict) and "freq" in data and isinstance(data["freq"], dict):
        return {k: int(v) for k, v in data["freq"].items()}
    if isinstance(data, dict):
        return {k: int(v) for k, v in data.items()}
    return {}

def _sb() -> tuple[str, str]:
    url = st.secrets["URL"]
    key = st.secrets["ROLE_KEY"]
    return url, key
    
@st.cache_data(show_spinner="Memuat model SuggestEngine…")
def load_suggest_models_from_storage(bucket: str, version: str) -> dict:
    url = st.secrets["URL"]
    key = st.secrets["ROLE_KEY"]

    def get(path: str) -> bytes:
        return download_private_bytes(
            supabase_url=url,
            service_role_key=key,
            bucket=bucket,
            path=path,
        )

    index_payload = pickle.loads(get("models/symspell_id.pkl"))

    unigram_obj = load_json_from_bytes(get("models/unigram_freq.json"))
    unigram = load_unigram_freq_from_obj(unigram_obj)

    confusions = load_json_from_bytes(get("models/confusion.json")) or {}
    split_join = load_json_from_bytes(get("models/split_join_rules.json")) or {}

    return {
        "index_payload": index_payload,
        "unigram": unigram,
        "confusions": confusions,
        "split_join": split_join,
    }
    
@st.cache_data(show_spinner="Cek versi kamus…")
def load_storage_version(bucket: str, version_path: str = "meta/version.txt") -> str:
    supabase_url, service_key = _sb()
    try:
        vbytes = download_private_bytes(
            supabase_url=supabase_url,
            service_role_key=service_key,
            bucket=bucket,
            path=version_path,
        )
        v = vbytes.decode("utf-8", errors="replace").strip()
        return v or "no-version"
    except Exception:
        return "no-version"
        
@st.cache_data(show_spinner="Memuat kamus dari Data Storage…")
def load_resources_from_storage_versioned(
    *,
    bucket: str,
    version: str,
) -> Dict[str, Set[str]]:
    supabase_url, service_key = _sb()

    def get(path: str) -> bytes:
        return download_private_bytes(
            supabase_url=supabase_url,
            service_role_key=service_key,
            bucket=bucket,
            path=path,
        )

    # ===== DICT =====
    kbbi = _read_kbbi_csv_from_bytes(get("dict/kbbi.csv"))
    kamus_id = _read_txt_set_from_bytes(get("dict/kamus_indonesia.txt"))
    dictionary_en = _read_txt_set_from_bytes(get("dict/dictionary_en.txt"))
    kamus_en = _read_txt_set_from_bytes(get("dict/kamus_inggris.txt"))
    singkatan = _read_txt_set_from_bytes(get("dict/singkatan.txt"))
    domain_terms = _read_txt_set_from_bytes(get("dict/domain_terms.txt"))

    english_vocab = dictionary_en | kamus_en | singkatan

    # ===== WL =====
    nama_tempat = _read_txt_set_from_bytes(get("wl/nama_tempat.txt"))
    sidoarjo_terms = _read_txt_set_from_bytes(get("wl/sidoarjo_terms.txt"))
    satuan = _read_txt_set_from_bytes(get("wl/satuan_unit.txt"))
    ignore_vocab = nama_tempat | sidoarjo_terms | satuan

    protected_phrases = _read_txt_set_from_bytes(get("dict/protected_phrase.txt"))

    protected_names_raw = _read_txt_set_from_bytes(get("wl/protected_names.txt"))
    protected_name_tokens = set()
    for line in protected_names_raw:
        for w in line.split():
            protected_name_tokens.add(w.lower())

    known_vocab, english_vocab2, known_vocab_for_names = build_vocabs(
        kbbi=kbbi,
        kamus_id=kamus_id,
        domain_terms=domain_terms,
        kamus_en=english_vocab,
        singkatan=singkatan,
        ignore_vocab=ignore_vocab,
    )

    return dict(
        kbbi=kbbi,
        kamus_id=kamus_id,
        domain_terms=domain_terms,
        known_vocab=known_vocab,
        english_vocab=english_vocab2,
        known_vocab_for_names=known_vocab_for_names,
        ignore_vocab=ignore_vocab,
        protected_phrases=protected_phrases,
        protected_name_tokens=protected_name_tokens,

        kamus_en=kamus_en,
        singkatan=singkatan,
        dictionary_en=dictionary_en,
    )
