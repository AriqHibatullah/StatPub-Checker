from __future__ import annotations
import requests

def create_signed_url(
    *,
    supabase_url: str,
    service_role_key: str,
    bucket: str,
    path: str,
    expires_in: int = 3600,
    timeout_s: int = 20,
) -> str:
    endpoint = f"{supabase_url.rstrip('/')}/storage/v1/object/sign/{bucket}/{path.lstrip('/')}"
    r = requests.post(
        endpoint,
        headers={
            "Authorization": f"Bearer {service_role_key}",
            "apikey": service_role_key,
            "Content-Type": "application/json",
        },
        json={"expiresIn": int(expires_in)},
        timeout=timeout_s,
    )
    r.raise_for_status()
    data = r.json()
   
    signed_path = data.get("signedURL") or data.get("signedUrl") or data.get("signed_url")
    if not signed_path:
        raise RuntimeError(f"Signed URL missing in response: {data}")
    if signed_path.startswith("http"):
        return signed_path
    return f"{supabase_url.rstrip('/')}{signed_path}"

def download_private_bytes(
    *,
    supabase_url: str,
    service_role_key: str,
    bucket: str,
    path: str,
    expires_in: int = 3600,
) -> bytes:
    signed_url = create_signed_url(
        supabase_url=supabase_url,
        service_role_key=service_role_key,
        bucket=bucket,
        path=path,
        expires_in=expires_in,
    )
    r = requests.get(signed_url, timeout=60)
    r.raise_for_status()
    return r.content
