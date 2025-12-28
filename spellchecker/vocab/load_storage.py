from __future__ import annotations

import io
import csv
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


def _sb() -> tuple[str, str]:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
    return url, key


@st.cache_data(show_spinner="Memuat kamus dari Data Storage…")
def load_resources_from_storage(
    *,
    bucket: str,
    version_path: str = "meta/version.txt",
) -> Dict[str, Set[str]]:
    supabase_url, service_key = _sb()

    try:
        vbytes = download_private_bytes(
            supabase_url=supabase_url,
            service_role_key=service_key,
            bucket=bucket,
            path=version_path,
        )
        version = vbytes.decode("utf-8", errors="replace").strip()
    except Exception:
        version = "no-version"

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
    ignore_vocab = prov | kabkot | kec | negara | satuan

    protected_phrases = _read_txt_set_from_bytes(get("wl/protected_phrases.txt"))

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

    _ = version

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
    )
