from __future__ import annotations

import io
import re
import json
import uuid
import zipfile
import tempfile
from docx import Document
from pathlib import Path
from typing import List, Dict, Any
from supabase import create_client
from datetime import datetime

import pandas as pd
import streamlit as st

# =========================
# Fixed project paths
# =========================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

DICT_DIR = DATA_DIR / "dictionaries"
WL_DIR = DATA_DIR / "whitelist"
MODEL_DIR = DATA_DIR / "models"

from spellchecker.vocab.loaders import load_kbbi_words, load_txt_set
from spellchecker.pipeline import run_on_file, build_vocabs
from spellchecker.settings import Settings

# =========================
# Streamlit config
# =========================
st.set_page_config(page_title="StatPub Checker Beta", layout="wide")
st.markdown("""
    <style>
    header[data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important;
    }
    .stApp {
        background: linear-gradient(135deg, #f7fff7 0%, #c3cfe2 100%);
    }
    .stApp, .stApp * {
        color: #1a535c;
    }
    .stButton > button:not([disabled]) {
        background-color: #ffe66d !important;
        color: white !important;
        border: none !important;
    }
    .stButton > button:not([disabled]):hover {
        background-color: #ffe246 !important;
        color: white !important;
    }
    .stButton > button[kind="secondary"]:not([disabled]) {
        background-color: #f7fff7 !important;
        color: #1a535c !important;
        border: 1px solid rgba(26, 83, 92, 0.4) !important;
    }
    .stButton > button[kind="secondary"]:not([disabled]):hover {
        background-color: #F0F2F6 !important;
        color: #1a535c !important;
        border: 1px solid rgba(26, 83, 92, 0.4) !important;
    }
    [data-testid="stSidebar"] {
        background: #fafcfa !important;
    }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("📊 StatPub Checker Beta 📃")
    st.caption("Lihat demo Web App StatPub Checker [di sini](https://docs.streamlit.io).")
    with st.expander("📘 Cara penggunaan"):
        st.markdown("""
            Panduan lengkap bagaimana cara menggunakan StatPub Checker tersedia [di sini](https://docs.streamlit.io).
        """)
    with st.expander("ℹ️ Release Note Terbaru"):
        st.markdown("""
            ## v0.2.0\n
            - Menambahkan fitur Review & Seleksi untuk mengoptimalkan output.
            - Mengubah file output agar lebih memudahkan pengguna.
        """)
    st.info("Version 0.2.0")

    st.write(" ")
    st.write(" ")
    st.markdown("""
        <div style="padding: 10px; border-radius: 10px">
            <p style="margin:0; font-size:0.8rem; color:#1a535c;">Developed By:</p>
            <p style="margin:0; font-weight:bold; color:#4ecdc4;">Firdaini Azmi &  </p>
            <p style="margin:0; font-weight:bold; color:#4ecdc4;">Muhammad Ariq Hibatullah</p>
        </div>
    """, unsafe_allow_html=True)

st.title("📂 Masukkan file untuk diperiksa")
st.caption("Upload DOCX/PDF → sistem menghasilkan temuan typo + saran koreksi.")

# =========================
# Resource loading (cached)
# =========================
@st.cache_resource
def load_resources():
    kbbi = load_kbbi_words(DICT_DIR / "kbbi.csv")
    kamus_id = load_txt_set(DICT_DIR / "kamus_indonesia.txt")
    dictionary_en = load_txt_set(DICT_DIR / "dictionary_en.txt")
    kamus_en = load_txt_set(DICT_DIR / "kamus_inggris.txt")
    singkatan = load_txt_set(DICT_DIR / "singkatan.txt")
    english_vocab = dictionary_en| kamus_en | singkatan
    domain_terms = load_txt_set(DICT_DIR / "domain_terms.txt")

    prov = load_txt_set(WL_DIR / "provinsi.txt") if (WL_DIR / "provinsi.txt").exists() else set()
    kabkot = load_txt_set(WL_DIR / "kabupaten_kota.txt") if (WL_DIR / "kabupaten_kota.txt").exists() else set()
    kec = load_txt_set(WL_DIR / "kecamatan_sda.txt") if (WL_DIR / "kecamatan_sda.txt").exists() else set()
    negara = load_txt_set(WL_DIR / "negara.txt") if (WL_DIR / "negara.txt").exists() else set()
    satuan = load_txt_set(WL_DIR / "satuan_unit.txt") if (WL_DIR / "satuan_unit.txt").exists() else set()
    ignore_vocab = prov | kabkot | kec | negara | satuan

    protected_phrases = load_txt_set(WL_DIR / "protected_phrases.txt") if (WL_DIR / "protected_phrases.txt").exists() else set()

    protected_names_raw = load_txt_set(WL_DIR / "protected_names.txt") if (WL_DIR / "protected_names.txt").exists() else set()
    protected_name_tokens = set()
    for line in protected_names_raw:
        for w in line.split():
            protected_name_tokens.add(w.lower())

    known_vocab, english_vocab, known_vocab_for_names = build_vocabs(
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
        english_vocab=english_vocab,
        known_vocab_for_names=known_vocab_for_names,
        ignore_vocab=ignore_vocab,
        protected_phrases=protected_phrases,
        protected_name_tokens=protected_name_tokens,
    )

resources = load_resources()

# =========================
# UI Controls
# =========================
uploads = st.file_uploader(
        "Upload file DOCX/PDF, bisa upload banyak",
        type=["docx", "pdf"],
        accept_multiple_files=True,
        help = "Untuk file pdf, disarankan agar file tidak mempunyai watermark untuk performa optimal."
    )

colA1, colA2, = st.columns([2,1])

with colA1:
    colB, colC = st.columns([1, 1])

    with colB:
        topk = st.number_input("Top-K saran", min_value=1, max_value=10, value=3, step=1, help="Masukkan jumlah saran yang akan diberikan program (Saran optimal: 3)")

        show_only_top1_if_conf_ge = st.slider(
            "Jika conf ≥ ini, tampilkan Top-1 saja",
            min_value=0.0,
            max_value=1.0,
            value=0.72,
            step=0.01,
            format="%.2f",
            help="Masukkan skor Confidence dari saran kata yang dianggap 'pasti benar'"
        )

    with colC:
        max_findings = st.number_input("Max temuan per file", min_value=50, max_value=5000, value=200, step=50)

with colA2:
    user_vocab_text = st.text_area(
            "Masukkan kata tambahan",
            height = 150,
            placeholder = "Contoh:\nStunting\nBig Data\n...",
            help = "Masukan kata yang khusus dan tidak ada di KBBI, seperti nama orang atau tempat"
        )

run_btn = st.button("Jalankan pemeriksaan", type="primary", disabled=not uploads)

if "df" not in st.session_state:
    st.session_state.df = None
if "report_ready" not in st.session_state:
    st.session_state.report_ready = False
if "csv_ready" not in st.session_state:
    st.session_state.csv_ready = False

def parse_user_vocab(text: str) -> set[str]:
    vocab = set()
    for line in (text or "").splitlines():
        w = line.strip().lower()
        if not w:
            continue
        for tok in w.split():
            if tok.isalpha() and len(tok) >= 2:
                vocab.add(tok)
    return vocab

user_vocab = parse_user_vocab(user_vocab_text)
st.session_state.user_vocab = sorted(list(user_vocab))

def findings_to_dataframe(findings: List[Any]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for f in findings:
        if isinstance(f, dict):
            file = f.get("file", "")
            page = f.get("page", "")
            token = f.get("token", "")
            status = f.get("status", "")
            snippet = f.get("snippet", "")
            suggs = f.get("suggestions", []) or []
        else:
            file = getattr(f, "file", "")
            page = getattr(f, "page", "")
            token = getattr(f, "token", "")
            status = getattr(f, "status", "")
            snippet = getattr(f, "snippet", "")
            suggs = getattr(f, "suggestions", []) or []

        row = {"file": file, "page": page, "token": token, "status": status}
        for i in range(1, 4):
            if len(suggs) >= i:
                s = suggs[i - 1]
                if isinstance(s, dict):
                    sug = s.get("suggestion") or s.get("term") or s.get("word") or ""
                    conf = s.get("confidence", "")
                else:
                    sug = getattr(s, "suggestion", "") or getattr(s, "term", "") or ""
                    conf = getattr(s, "confidence", "")
            else:
                sug, conf = "", ""
            row[f"suggestion_{i}"] = sug
            row[f"confidence_{i}"] = conf
        row["snippet"] = snippet
        rows.append(row)

    cols = [
        "file", "page", "token", "status",
        "suggestion_1", "confidence_1",
        "suggestion_2", "confidence_2",
        "suggestion_3", "confidence_3",
        "snippet",
    ]
    df = pd.DataFrame(rows)
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df[cols]

def parse_id_ranges(text: str) -> set[int]:
    ids: set[int] = set()
    if not text:
        return ids

    parts = [p.strip() for p in text.split(",") if p.strip()]
    for part in parts:
        if "-" in part:
            a, b = [x.strip() for x in part.split("-", 1)]
            if a.isdigit() and b.isdigit():
                start, end = int(a), int(b)
                if start > end:
                    start, end = end, start
                ids.update(range(start, end + 1))
        else:
            if part.isdigit():
                ids.add(int(part))
    return ids

def run_pipeline_on_paths(paths: List[str]) -> List[Any]:
    cfg = Settings(
        topk=int(topk),
        max_findings_per_file=int(max_findings),
        show_only_top1_if_conf_ge=float(show_only_top1_if_conf_ge),
    )

    known_vocab_plus = set(resources["known_vocab"]) | set(user_vocab or set())

    all_findings: List[Any] = []
    for p in paths:
        findings, meta = run_on_file(
            path=p,
            cfg=cfg,
            known_vocab=known_vocab_plus,
            english_vocab=resources["english_vocab"],
            known_vocab_for_names=resources["known_vocab_for_names"],
            ignore_vocab=resources["ignore_vocab"],
            domain_terms=resources["domain_terms"],
            protected_phrases=resources["protected_phrases"],
            protected_name_tokens=resources["protected_name_tokens"],
        )
        all_findings.extend(findings)

    return all_findings

def replace_in_docx_bytes(docx_bytes: bytes, replacements: dict[str, str]) -> bytes:
    doc = Document(io.BytesIO(docx_bytes))

    # sort by length desc biar token panjang menang dulu (mengurangi partial replace)
    keys = sorted([k for k in replacements.keys() if k], key=len, reverse=True)
    if not keys:
        return docx_bytes

    pattern = re.compile("|".join(re.escape(k) for k in keys))

    def sub_func(m):
        return replacements.get(m.group(0), m.group(0))

    def repl_in_paragraph(p):
        for run in p.runs:
            t = run.text
            if t:
                run.text = pattern.sub(sub_func, t)

    for p in doc.paragraphs:
        repl_in_paragraph(p)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    repl_in_paragraph(p)

    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()

def upload_to_supabase(bucket: str, path: str, content: bytes, content_type: str = "text/csv", upsert: bool = True):
    supabase = create_client(
        st.secrets["URL"],
        st.secrets["ROLE_KEY"],
    )

    file_options = {
        "content-type": content_type,
        "x-upsert": "true" if upsert else "false",
    }

    supabase.storage.from_(bucket).upload(
        path,
        content,
        file_options=file_options,
    )

if run_btn:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        saved_paths: List[str] = []

        if "upload_bytes_by_name" not in st.session_state:
            st.session_state.upload_bytes_by_name = {}

        for up in uploads:
            out_path = tmpdir / up.name
            b = up.getbuffer().tobytes()
            out_path.write_bytes(b)
            saved_paths.append(str(out_path))

            st.session_state.upload_bytes_by_name[up.name] = b

        st.info(f"Memproses {len(saved_paths)} file…")

        with st.spinner("Running spellcheck…"):
            findings = run_pipeline_on_paths(saved_paths)

        df = findings_to_dataframe(findings)

        st.session_state.run_id = str(uuid.uuid4())
        st.session_state.run_ts_utc = datetime.utcnow().isoformat()

        df_raw_dev = df.copy()
        if "_rid" not in df_raw_dev.columns:
            df_raw_dev["_rid"] = range(len(df_raw_dev))
        st.session_state.df_raw_dev = df_raw_dev

        if "_rid" not in df.columns:
            df["_rid"] = range(len(df))

        st.session_state.df = df
        st.session_state.report_ready = True
        st.session_state.review_mode = False
        st.session_state.csv_ready = False

if st.session_state.report_ready and st.session_state.df is not None:
    df_raw = st.session_state.df

    STATUS_MAP = {
        "symspell": "🔴 Kesalahan penulisan",
        "no_candidates": "⚪ Kata tidak dikenali",
        "space_error": "🟡 Kesalahan spasi",
        "abbr_candidate": "⚪ Singkatan tidak dikenali",
        "confusion": "🔴 Kesalahan penulisan",
        "affix_typo": "🔴 Kesalahan penulisan",
    }
    df_view = df_raw[df_raw["status"] != "abbr_confirmed"].copy()
    if "status" in df_view.columns:
        df_view["status"] = df_view["status"].map(STATUS_MAP).fillna(df_view["status"])

    st.subheader("Report Pemeriksaan")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total temuan", int(len(df_view)))
    c2.metric("Jumlah file", int(df_view["file"].nunique()) if "file" in df_view.columns else 0)
    c3.metric("Jumlah halaman (unik)", int(df_view["page"].nunique()) if "page" in df_view.columns else 0)
    try:
        avg_conf1 = pd.to_numeric(df_view["confidence_1"], errors="coerce").mean()
        c4.metric("Rata-rata conf Top-1", f"{avg_conf1:.2f}" if pd.notna(avg_conf1) else "-")
    except Exception:
        c4.metric("Rata-rata conf Top-1", "-")

    tab3, tab1, tab2 = st.tabs(["Preview Detail", "Ringkasan", "Per File"])

    with tab1:
        if "status" in df_view.columns and len(df_view) > 0:
            st.markdown("**Ringkasan status**")
            status_summary = (
                df_view["status"]
                .value_counts(dropna=False)
                .rename_axis("Status")
                .reset_index(name="Jumlah")
            )
            st.dataframe(status_summary, width='stretch')

        st.markdown("**Kata yang paling sering muncul**")
        if "token" in df_view.columns and len(df_view) > 0:
            top_tokens = (
                df_view["token"]
                .value_counts(dropna=False)
                .head(10)
                .rename_axis("Kata")
                .reset_index(name="Jumlah")
            )
            st.dataframe(top_tokens, width='stretch')

    with tab2:
        st.markdown("**Temuan per file**")
        if "file" in df_view.columns and len(df_view) > 0:
            by_file = (
                df_view.groupby("file", dropna=False)
                .size()
                .sort_values(ascending=False)
                .rename("Jumlah")
                .reset_index()
            )
            st.dataframe(by_file, width='stretch')

    with tab3:
        st.markdown("**Preview detail**")
        st.caption("Silahkan diperiksa terlebih dahulu hasil deteksi di bawah, terlebih lagi yang berstatus ⚪ (tidak dikenali).")
        DISPLAY_COLS = [
            "file",
            "token",
            "status",
            "suggestion_1",
            "suggestion_2",
            "suggestion_3",
            "snippet",
        ]
        pre_detail = (
            df_view
            .loc[:, DISPLAY_COLS]
            .rename(columns={
                "file": "File",
                "token": "Kata",
                "suggestion_1": "Saran 1",
                "suggestion_2": "Saran 2",
                "suggestion_3": "Saran 3",
                "status": "Status",
                "snippet": "Pada kalimat"
            })
        )
        st.dataframe(pre_detail.head(500), width='stretch', height=520)

    st.markdown("---")
    start_review = st.button("Mulai Review pilihan typo", type="primary")
    if start_review:
        st.session_state.review_mode = True

if st.session_state.get("review_mode", False) and st.session_state.df is not None:
    df_raw = st.session_state.df.copy()

    status_map = {
        "symspell": "🔴 Kesalahan penulisan",
        "no_candidates": "⚪ Kata tidak dikenali",
        "space_error": "🟡 Kesalahan spasi",
        "abbr_candidate": "⚪ Singkatan tidak dikenali",
        "confusion": "🔴 Kesalahan penulisan",
        "affix_typo": "🔴 Kesalahan penulisan",
    }
    df = df_raw[df_raw["status"] != "abbr_confirmed"].copy()

    if "fix_choice" not in df.columns:
        df["fix_choice"] = ""
    if "fix_custom" not in df.columns:
        df["fix_custom"] = ""
    if "fix_final" not in df.columns:
        df["fix_final"] = ""
    if "ignore" not in df.columns:
        df["ignore"] = False
    if "ignore_reason" not in df.columns:
        df["ignore_reason"] = ""
    if "ignore_note" not in df.columns:
        df["ignore_note"] = ""

    st.subheader("Review & Seleksi")
    st.write("Silahkan seleksi jika ada kata yang salah koreksi oleh sistem. Centanglah kata yang bukan typo/salah koreksi.")
    st.caption(
        "Segmen pada table review: 🟦 Informasi; 🟩 Fix; 🟨 Review.  \n"  
        "Bantu perkembangan sistem ini dengan mengisi kolom pada segmen 🟨 Review, agar sistem dapat lebih mengoreksi lebih optimal."
    )

    cols = st.columns(3)
    with cols[0]:
        file_filter = (
            st.multiselect("Filter file", sorted(df["file"].dropna().unique().tolist()))
            if "file" in df.columns else []
        )
    with cols[1]:
        if "status" in df.columns:
            df["status_disp"] = df["status"].map(status_map).fillna(df["status"].astype(str))
        else:
            df["status_disp"] = ""

        status_filter = (
            st.multiselect("Filter status", sorted(df["status_disp"].dropna().unique().tolist()))
            if "status_disp" in df.columns else []
        )
    with cols[2]:
        st.write(" ")
        show_only_fixable = st.checkbox("Hanya tampilkan yang akan diperbaiki", value=False)

    review_cols = ["ignore", "fix_choice", "fix_custom", "ignore_reason", "ignore_note"]
    info_cols = [c for c in ["token", "status_disp", "suggestion_1", "suggestion_2", "suggestion_3"] if c in df.columns]

    filtered = df
    if file_filter and "file" in filtered.columns:
        filtered = filtered[filtered["file"].isin(file_filter)]
    if status_filter and "status_disp" in filtered.columns:
        filtered = filtered[filtered["status_disp"].isin(status_filter)]
    if show_only_fixable:
        filtered = filtered[filtered["ignore"] == False]

    display_cols = ["_rid"] + info_cols + review_cols
    view = filtered[display_cols].copy()

    reason_options = ["", "Kata yg benar", "Saran salah", "Nama/istilah khusus", "Singkatan", "Bahasa campuran", "Lainnya"]

    edited = st.data_editor(
        view,
        key="review_editor",
        width='stretch',
        height=520,
        num_rows="fixed",
        column_config={
            "token": st.column_config.TextColumn("🟦 Kata"),
            "status_disp": st.column_config.TextColumn("🟦 Status"),
            "suggestion_1": st.column_config.TextColumn("🟦 Saran 1"),
            "suggestion_2": st.column_config.TextColumn("🟦 Saran 2"),
            "suggestion_3": st.column_config.TextColumn("🟦 Saran 3"),
            "ignore": st.column_config.CheckboxColumn(
                "🟩 Salah koreksi",
                help="Centang jika ini BUKAN typo dan tidak perlu diperbaiki atau koreksi salah",
                default=False,
            ),
            "fix_choice": st.column_config.TextColumn(
                "🟩 Pilih koreksi",
                help="Isi 1 untuk Saran 1, 2 untuk Saran 2, 3 untuk Saran 3. Kosong = pakai custom.",
            ),
            "fix_custom": st.column_config.TextColumn(
                "🟩 Koreksi manual",
                help="Isi jika pilih 'custom'",
            ),
            "ignore_reason": st.column_config.SelectboxColumn(
                "🟨 Alasan",
                options=reason_options,
                help="Pilih alasan kenapa diabaikan",
            ),
            "ignore_note": st.column_config.TextColumn(
                "🟨 Catatan (opsional)",
                help="Misal: kata yang benar, konteks, atau saran alternatif",
            ),
            "_rid": st.column_config.NumberColumn("ID", disabled=True),
        },
        disabled=[c for c in view.columns if c not in review_cols]
    )

    base = df.set_index("_rid")
    ed = edited.set_index("_rid")

    base.loc[ed.index, review_cols] = ed[review_cols]
    df = base.reset_index()

    AUTO_IGNORE_STATUSES = {"no_candidates", "abbr_candidate"}

    def _final_fix(row):    
        if row.get("status") in AUTO_IGNORE_STATUSES:
            return ""

        if bool(row.get("ignore", False)):
            return ""

        choice = str(row.get("fix_choice", "") or "").strip()
        custom = str(row.get("fix_custom", "") or "").strip()

        if choice == "":
            if custom:
                return custom
            return str(row.get("suggestion_1", "") or "").strip()

        if choice in ("1", "2", "3"):
            return str(row.get(f"suggestion_{choice}", "") or "").strip()

        if choice in ("suggestion_1", "suggestion_2", "suggestion_3"):
            return str(row.get(choice, "") or "").strip()

        if custom:
            return custom
        return str(row.get("suggestion_1", "") or "").strip()
    
    df["fix_final"] = df.apply(_final_fix, axis=1)
    st.session_state.df = df

    colB1, colB2, = st.columns([2,3])
    with colB1:
        auto_text = st.text_input(
            "Masukkan rentang yang salah koreksi",
            placeholder="Misal: 1-5, 7-9",
            key="auto_ignore_ranges",
        )
        apply_auto = st.button("Centang kata", type="secondary")

    if apply_auto:
        ids = parse_id_ranges(auto_text)
        if "_rid" in df.columns and ids:
            df.loc[df["_rid"].isin(ids), "ignore"] = True
            st.session_state.df = df
            st.rerun()
        else:
            st.warning("Tidak ada ID valid yang terdeteksi, atau kolom _rid belum tersedia.")

    st.markdown("---")
    st.caption("Setelah review selesai, klik Perbaiki typo untuk membuat output berdasarkan pilihanmu.")
    fix_btn = st.button("Perbaiki typo", type="secondary")

    if fix_btn:
        with st.spinner("Membuat dokumen revisi + log perubahan..."):
            df_all = st.session_state.df.copy()

            run_id = st.session_state.get("run_id") or str(uuid.uuid4())
            st.session_state.run_id = run_id
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            ts_utc = st.session_state.get("run_ts_utc") or datetime.utcnow().isoformat()

            df_all["action"] = df_all.apply(
                lambda r: "ignored" if r.get("ignore", False)
                else (
                    "replaced"
                    if (str(r.get("fix_final", "")).strip()
                        and str(r.get("fix_final", "")).strip() != str(r.get("token", "")).strip())
                    else "no_fix"
                ),
                axis=1
            )

            df_audit_user = df_all[df_all["action"] == "replaced"].copy()
            cols_user = [c for c in ["file", "token", "fix_final", "snippet"] if c in df_audit_user.columns]
            df_audit_user = df_audit_user.loc[:, cols_user].rename(columns={
                "file": "File",
                "token": "Kata sebelum",
                "fix_final": "Kata sesudah",
                "snippet": "Pada Kalimat",
            })
            user_log_bytes = df_audit_user.to_csv(index=False).encode("utf-8")

            df_fix = df_all[
                (df_all["ignore"] == False) &
                (df_all["fix_final"].astype(str).str.strip().str.len() > 0)
            ].copy()

            if "status" in df_all.columns:
                df_fix = df_fix[~df_fix["status"].isin({"no_candidates", "abbr_candidate"})]

            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("log_perubahan.csv", user_log_bytes)

                groups = list(df_fix.groupby("file"))
                prog = st.progress(0)
                total = max(len(groups), 1)

                for i, (fname, g) in enumerate(groups, start=1):
                    prog.progress(i / total)

                    src_bytes = st.session_state.upload_bytes_by_name.get(fname)
                    if not src_bytes:
                        continue

                    repl = {}
                    for _, r in g.iterrows():
                        old = str(r.get("token", "")).strip()
                        new = str(r.get("fix_final", "")).strip()
                        if old and new and old != new:
                            repl[old] = new

                    if fname.lower().endswith(".docx"):
                        revised = replace_in_docx_bytes(src_bytes, repl)
                        z.writestr(f"revisi_{fname}", revised)
                    else:
                        z.writestr(
                            f"README_{fname}.txt",
                            "File ini bukan DOCX, revisi otomatis belum didukung. Lihat log_perubahan.csv"
                        )

                prog.empty()

            zip_buf.seek(0)

            st.download_button(
                "Download hasil revisi (ZIP)",
                data=zip_buf.getvalue(),
                file_name="hasil_revisi.zip",
                mime="application/zip",
            )

            try:
                df_raw_dev = st.session_state.get("df_raw_dev")
                if df_raw_dev is None:
                    df_raw_dev = df_all.copy()

                df_eval_full = df_all.copy()
                
                abbr_confirmed_count = 0
                if "status" in df_eval_full.columns:
                    abbr_confirmed_count = int((df_eval_full["status"] == "abbr_confirmed").sum())

                replaced = int((df_eval_full["action"] == "replaced").sum())
                ignored  = int((df_eval_full["action"] == "ignored").sum())
                total    = int(len(df_eval_full))
                
                den = replaced + ignored
                acceptance_rate = (replaced / den) if den > 0 else None

                custom_used = int(((df_eval_full["action"] == "replaced") & (df_eval_full["fix_custom"].astype(str).str.strip().str.len() > 0)).sum()) if "fix_custom" in df_eval_full.columns else None
                custom_rate = (custom_used / replaced) if (custom_used is not None and replaced > 0) else None

                non_top1_count = 0
                if replaced > 0:
                    non_top1_count = int((
                        (df_eval_full["action"] == "replaced") &
                        (
                            (df_eval_full["fix_choice"].isin(["suggestion_2", "suggestion_3", "custom"])) |
                            (df_eval_full["fix_custom"].astype(str).str.strip().str.len() > 0)
                        )
                    ).sum())
                
                non_top1_rate = (non_top1_count / replaced) if replaced > 0 else None

                meta = {
                    "run_id": run_id,
                    "ts_utc": ts_utc,
                    "files": sorted(list(st.session_state.get("upload_bytes_by_name", {}).keys())),
                    "config": {
                        "topk": int(topk),
                        "max_findings": int(max_findings),
                        "show_only_top1_if_conf_ge": float(show_only_top1_if_conf_ge),
                    },
                    "summary": {
                        "total_findings": int(len(df_eval_full)),
                        "replaced": int((df_eval_full["action"] == "replaced").sum()) if "action" in df_eval_full.columns else None,
                        "ignored": int((df_eval_full["action"] == "ignored").sum()) if "action" in df_eval_full.columns else None,
                        "non_top1_count": non_top1_count,
                        "abbr_confirmed": abbr_confirmed_count,
                    },
                    "accuracy": {
                        "precision_proxy": acceptance_rate,
                        "custom_rate": custom_rate,
                        "non_top1_rate": non_top1_rate,
                    },
                    "user_vocab": st.session_state.get("user_vocab", []),
                    "user_vocab_count": len(st.session_state.get("user_vocab", [])),
                    "app_version": "0.2.0",
                }

                bucket = "dev-reports"
                base_path = f"{date_str}/{run_id}"

                upload_to_supabase(
                    bucket=bucket,
                    path=f"{base_path}/raw_findings.csv",
                    content=df_raw_dev.to_csv(index=False).encode("utf-8"),
                    content_type="text/csv",
                )

                upload_to_supabase(
                    bucket=bucket,
                    path=f"{base_path}/eval_full.csv",
                    content=df_eval_full.to_csv(index=False).encode("utf-8"),
                    content_type="text/csv",
                )

                upload_to_supabase(
                    bucket=bucket,
                    path=f"{base_path}/meta.json",
                    content=json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"),
                    content_type="application/json",
                )

                uv = "\n".join(st.session_state.get("user_vocab", [])) + "\n"
                upload_to_supabase(
                    bucket=bucket,
                    path=f"{base_path}/user_vocab.txt",
                    content=uv.encode("utf-8"),
                    content_type="text/plain",
                )

            except Exception as e:
                st.warning(f"(Dev) Upload report gagal: {e}")

st.markdown("---")
st.caption(
    "Catatan: Beta ini memakai kamus & model yang masih dikembangkan. "
    "Data akan selalu diupdate untuk memaksimalkan performa."
)
