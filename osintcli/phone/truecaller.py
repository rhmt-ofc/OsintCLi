"""Truecaller Reverse-Engineered Client for OsintCLI.
Based on decompiled Android client networking (Retrofit / OkHttp) v13.40.
"""
import json
import os
import re

TRUECALLER_SEARCH_ENDPOINT = "https://search5-noneu.truecaller.com/v2/search"
DEFAULT_USER_AGENT = "Truecaller/13.40.6 (Android; 13; Scale/3.00)"


def parse_truecaller_response(data):
    """Parse JSON structure returned from Truecaller search endpoint."""
    if not isinstance(data, dict):
        return None

    data_list = data.get("data", [])
    if not data_list or not isinstance(data_list, list):
        return None

    entry = data_list[0]
    if not isinstance(entry, dict):
        return None

    name = entry.get("name") or ""
    phones = [p.get("e164Format") for p in entry.get("phones", []) if isinstance(p, dict) and p.get("e164Format")]
    carrier = ""
    for p in entry.get("phones", []):
        if isinstance(p, dict) and p.get("carrier"):
            carrier = p["carrier"]
            break

    spam_score = entry.get("spamScore", 0)
    badges = entry.get("badges", [])
    if isinstance(badges, list):
        badges = [str(b) for b in badges]
    else:
        badges = []

    addresses = entry.get("addresses", [])
    city = ""
    country = ""
    if addresses and isinstance(addresses, list) and isinstance(addresses[0], dict):
        city = addresses[0].get("city", "")
        country = addresses[0].get("countryCode", "")

    internet_addresses = entry.get("internetAddresses", [])
    email = ""
    if internet_addresses and isinstance(internet_addresses, list) and isinstance(internet_addresses[0], dict):
        email = internet_addresses[0].get("id", "")

    return {
        "found": bool(name or phones),
        "name": name,
        "phones": phones,
        "carrier": carrier,
        "spam_score": spam_score,
        "badges": badges,
        "email": email,
        "city": city,
        "country": country,
        "raw": entry,
    }


def query_truecaller(client, phone_number, auth_token=None):
    """Perform Truecaller search using Client with token or env fallback."""
    digits = re.sub(r"\D", "", phone_number)
    token = auth_token or os.environ.get("TRUECALLER_TOKEN") or ""

    if not token:
        # Without token, Truecaller requires active session installation token
        return {
            "found": False,
            "error": "TRUECALLER_AUTH_REQUIRED",
            "message": "Truecaller memerlukan instalasi token (SET TRUECALLER_TOKEN di secrets.toml atau environment).",
            "offline_note": "Gunakan hasil REA untuk pasang bearer token dari sesi akun."
        }

    url = f"{TRUECALLER_SEARCH_ENDPOINT}?q={digits}&type=4&placement=SEARCHRESULTS,HISTORY,DETAILS&encoding=json"
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/json",
        "client-secret": "lvc22mp3l1sfv6ujg83xx17",
    }

    try:
        resp = client.request(url, headers=headers, timeout=10)
        data = resp.json()
        parsed = parse_truecaller_response(data)
        if parsed:
            return parsed
        return {"found": False, "message": "Nomor tidak terdaftar di database Truecaller."}
    except Exception as e:
        return {"found": False, "error": str(e)}
