# notifier_resend.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Mapping, Any
import requests


@dataclass(frozen=True)
class ResendEmailConfig:
    api_key: str
    from_email: str
    to_email_default: Optional[str] = None


def resend_send_email(
    *,
    cfg: ResendEmailConfig,
    to_email: str,
    subject: str,
    html: str,
    timeout_s: int = 20,
) -> dict:
    payload = {
        "from": cfg.from_email,
        "to": [to_email],
        "subject": subject,
        "html": html,
    }

    r = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout_s,
    )

    if r.status_code >= 400:
        raise RuntimeError(f"Resend error {r.status_code}: {r.text}")

    return r.json()


def resend_config_from_secrets(secrets: Mapping[str, Any]) -> ResendEmailConfig:
    api_key = secrets.get("RESEND_API_KEY")
    if not api_key:
        raise ValueError("RESEND_API_KEY tidak ditemukan")

    from_email = secrets.get("EMAIL_FROM")
    if not from_email:
        raise ValueError("EMAIL_FROM tidak ditemukan (mis: 'StatPub Checker <no-reply@domainmu.com>')")

    return ResendEmailConfig(
        api_key=api_key,
        from_email=from_email,
        to_email_default=secrets.get("EMAIL_TO"),
    )


def send_dev_report_email(
    *,
    secrets: Mapping[str, Any],
    run_id: str,
    base_path: str,
    total_findings: int,
) -> dict:
    cfg = resend_config_from_secrets(secrets)

    to_email = cfg.to_email_default or "ISI_SENDIRI@gmail.com"
    subject = f"[StatPub Checker] Dev report masuk — run_id: {run_id}"
    html = f"""
      <h3>Dev report baru masuk</h3>
      <ul>
        <li><b>run_id</b>: {run_id}</li>
        <li><b>base_path</b>: {base_path}</li>
        <li><b>total_findings</b>: {total_findings}</li>
      </ul>
    """

    return resend_send_email(cfg=cfg, to_email=to_email, subject=subject, html=html)
