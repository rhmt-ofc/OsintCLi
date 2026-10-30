"""Getcontact Reverse-Engineered Protocol Client for OsintCLI.
Implements the decompiled Getcontact APK v2.8 / v5 REST API, signature hashing,
and crowd-sourced contact tag extraction.
"""
import hashlib
import hmac
import json
import os
import re
import time

GETCONTACT_BASE = "https://pb.getcontact.com"
APP_HMAC_KEY = b"2da8b746d8495a12efbc347890cd12ef"  # Decompiled Getcontact HMAC key


def sign_payload(timestamp_str, payload_bytes, key=APP_HMAC_KEY):
    """Generate HMAC-SHA256 signature for Getcontact X-Signature header."""
    message = timestamp_str.encode("utf-8") + b":" + payload_bytes
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def extract_candidate_handles(tags):
    """Analyze crowd-sourced tags and extract potential social media handles/usernames."""
    candidates = set()
    for t in tags:
        t = t.strip()
        # Direct @handle
        m = re.search(r"@([A-Za-z0-9_.]{3,30})", t)
        if m:
            candidates.add(m.group(1).lower())
            continue

        # Prefix like "ig: mamat" or "github: mamat"
        m = re.search(r"(?:ig|instagram|gh|github|fb|twitter|x)[:\s\-]+([A-Za-z0-9_.]{3,30})", t, re.IGNORECASE)
        if m:
            candidates.add(m.group(1).lower())
            continue

        # Single word without spaces that looks like a username
        if re.fullmatch(r"[a-z0-9_]{4,20}", t.lower()) and not t.isdigit():
            # Filter out common indonesian generic words
            if t.lower() not in {"teman", "teman_kantor", "bapak", "ibu", "kakak", "abang", "mas", "mbak", "kantor"}:
                candidates.add(t.lower())

    return sorted(candidates)


def parse_getcontact_response(data):
    """Parse Getcontact response JSON into normalized profile and tags."""
    if not isinstance(data, dict):
        return None

    response_data = data.get("responseData", {})
    if not isinstance(response_data, dict):
        return None

    profile = response_data.get("profile", {})
    name = f"{profile.get('name', '')} {profile.get('surname', '')}".strip()

    tags_data = response_data.get("tags", [])
    tags = []
    if isinstance(tags_data, list):
        for item in tags_data:
            if isinstance(item, dict) and item.get("tag"):
                tags.append(item["tag"])
            elif isinstance(item, str):
                tags.append(item)

    spam_info = response_data.get("spamInfo", {})
    spam_count = spam_info.get("degree", 0) if isinstance(spam_info, dict) else 0

    return {
        "found": bool(name or tags),
        "name": name,
        "tags": tags,
        "tags_count": len(tags),
        "spam_score": spam_count,
        "candidate_handles": extract_candidate_handles(tags),
        "raw": response_data,
    }


def query_getcontact(client, phone_number, auth_token=None):
    """Execute signed Getcontact API request."""
    digits = re.sub(r"\D", "", phone_number)
    token = auth_token or os.environ.get("GETCONTACT_TOKEN") or ""

    if not token:
        return {
            "found": False,
            "error": "GETCONTACT_AUTH_REQUIRED",
            "message": "Getcontact memerlukan token sesi (SET GETCONTACT_TOKEN di secrets.toml atau environment).",
            "offline_note": "Gunakan hasil REA untuk pasang X-Token dari akun Getcontact.",
            "candidate_handles": [],
            "tags": [],
        }

    url = f"{GETCONTACT_BASE}/v2.8/number-detail"
    ts = str(int(time.time()))
    payload = json.dumps({"phoneNumber": f"+{digits}"}).encode("utf-8")
    sig = sign_payload(ts, payload)

    headers = {
        "X-Token": token,
        "X-Req-Timestamp": ts,
        "X-Signature": sig,
        "User-Agent": "GetContact/5.8.0 (Android; 13)",
        "Content-Type": "application/json; charset=utf-8",
    }

    try:
        resp = client.request(url, method="POST", body=payload, headers=headers, timeout=12)
        data = resp.json()
        parsed = parse_getcontact_response(data)
        if parsed:
            return parsed
        return {"found": False, "message": "Nomor tidak terdaftar atau rate-limit tercapai."}
    except Exception as e:
        return {"found": False, "error": str(e), "candidate_handles": [], "tags": []}
