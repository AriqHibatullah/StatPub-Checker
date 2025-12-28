import streamlit as st
import pandas as pd

EDITOR_KEY = "tabel_seleksi"

def apply_maps_to_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["ignore"] = out["_rid"].map(st.session_state.salah_koreksi).fillna(False).astype(bool)
    out["fix_choice"] = out["_rid"].map(st.session_state.pilihan_koreksi).fillna(pd.NA)
    out["fix_custom"] = out["_rid"].map(st.session_state.koreksi_manual).fillna(pd.NA).astype(str)

    mask = out["ignore"] == True
    out.loc[mask, "fix_choice"] = pd.NA
    out.loc[mask, "fix_custom"] = pd.NA

    return out

def commit_from_editor_state():
    state = st.session_state.get(EDITOR_KEY, {})
    edited_rows = state.get("edited_rows", {})

    rid_order = st.session_state.get("_rid_order_for_editor", [])
    for row_idx, changes in edited_rows.items():
        rid = int(rid_order[int(row_idx)])

        if "ignore" in changes:
            st.session_state.salah_koreksi[rid] = bool(changes["ignore"])

        ignore_now = bool(st.session_state.salah_koreksi.get(rid, False))

        if ignore_now:
            st.session_state.pilihan_koreksi[rid] = None
            st.session_state.koreksi_manual[rid] = None
            continue

        if "fix_choice" in changes:
            val = changes["fix_choice"]
            st.session_state.pilihan_koreksi[rid] = None if val in (None, "") else str(val)

            if st.session_state.pilihan_koreksi[rid] != "➕ Manual":
                st.session_state.koreksi_manual[rid] = None

        if "fix_custom" in changes:
            if st.session_state.pilihan_koreksi.get(rid) == "➕ Manual":
                st.session_state.koreksi_manual[rid] = str(changes["fix_custom"])
            else:
                st.session_state.koreksi_manual[rid] = None
