import streamlit as st
from spellchecker.session.document_helpers import reset_doc_dependent_state, compute_docs_fingerprint

def ensure_session_state():
    defaults = {
        "preview_show": False,
        "preview_file": None,

        "salah_koreksi": {},
        "pilihan_koreksi": {},
        "koreksi_manual": {},

        "review_alasan": {},
        "review_catatan": {},

        "docs_fingerprint": None,
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    upload_map = st.session_state.get("upload_bytes_by_name", {}) or {}

    if not upload_map:
        if st.session_state.get("docs_fingerprint") is not None:
            reset_doc_dependent_state()
            st.session_state.docs_fingerprint = None
        return

    new_fp = compute_docs_fingerprint(upload_map)
    old_fp = st.session_state.get("docs_fingerprint")

    if old_fp is None:
        st.session_state.docs_fingerprint = new_fp
    elif old_fp != new_fp:
        reset_doc_dependent_state()

        st.session_state.docs_fingerprint = new_fp

        st.session_state.preview_show = False
        st.session_state.preview_file = None
        st.session_state.salah_koreksi = {}
        st.session_state.pilihan_koreksi = {}
        st.session_state.koreksi_manual = {}
        st.session_state.review_alasan = {}
        st.session_state.review_catatan = {}

def sync_uploaded_files_and_autoreset(uploads):
    current_names = set()
    if uploads:
        current_names = {u.name for u in uploads}

    stored = st.session_state.get("upload_bytes_by_name", {}) or {}
    stored_names = set(stored.keys())

    removed = stored_names - current_names
    if removed:
        for name in removed:
            stored.pop(name, None)
        st.session_state.upload_bytes_by_name = stored

        reset_doc_dependent_state()
        st.session_state.docs_fingerprint = None

        st.session_state.preview_show = False
        st.session_state.preview_file = None
