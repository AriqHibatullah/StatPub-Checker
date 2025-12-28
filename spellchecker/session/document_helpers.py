import hashlib
import streamlit as st

def compute_docs_fingerprint(upload_bytes_by_name: dict[str, bytes]) -> str:
    h = hashlib.sha1()
    for name in sorted(upload_bytes_by_name.keys()):
        b = upload_bytes_by_name[name]
        h.update(name.encode("utf-8", "ignore"))
        h.update(b"::")
        h.update(hashlib.sha1(b).digest())
        h.update(b"|")
    return h.hexdigest()

DOC_DEP_KEYS = [
    "preview_show", "preview_file",
    "salah_koreksi", "pilihan_koreksi", "koreksi_manual",
    "review_alasan", "review_catatan",
    "df", "df_raw_dev", "report_ready",
    "pdf_cache_by_name", "pdf_preview_hl_cache", "pdf_preview_df_cache",
]

def reset_doc_dependent_state():
    for k in DOC_DEP_KEYS:
        if k in st.session_state:
            del st.session_state[k]