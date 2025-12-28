from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

from supabase import create_client


@dataclass(frozen=True)
class SupabaseConfig:
    url: str
    service_role_key: str


def _client(cfg: SupabaseConfig):
    return create_client(cfg.url, cfg.service_role_key)


def upload_bytes(
    *,
    cfg: SupabaseConfig,
    bucket: str,
    path: str,
    content: bytes,
    content_type: str,
    upsert: bool = True,
) -> None:
    sb = _client(cfg)
    sb.storage.from_(bucket).upload(
        path,
        content,
        file_options={"content-type": content_type, "upsert": upsert},
    )


def upload_dev_run_report(
    *,
    cfg: SupabaseConfig,
    bucket: str,
    base_path: str,  # contoh: "2025-12-23/<run_id>"
    raw_findings_csv: bytes,
    eval_full_csv: bytes,
    meta: Dict[str, Any],
    user_vocab_txt: bytes,
) -> None:
    upload_bytes(
        cfg=cfg,
        bucket=bucket,
        path=f"{base_path}/raw_findings.csv",
        content=raw_findings_csv,
        content_type="text/csv",
    )
    upload_bytes(
        cfg=cfg,
        bucket=bucket,
        path=f"{base_path}/eval_full.csv",
        content=eval_full_csv,
        content_type="text/csv",
    )
    upload_bytes(
        cfg=cfg,
        bucket=bucket,
        path=f"{base_path}/meta.json",
        content=json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"),
        content_type="application/json",
    )
    upload_bytes(
        cfg=cfg,
        bucket=bucket,
        path=f"{base_path}/user_vocab.txt",
        content=user_vocab_txt,
        content_type="text/plain",
    )
