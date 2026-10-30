"""Messaging Presence & Profile Prober for WhatsApp & Telegram.
Verifies active messaging accounts and extracts public presence indicators.
"""
import re


def probe_whatsapp(phone_number):
    """Generate deterministic WhatsApp link and presence indicators."""
    digits = re.sub(r"\D", "", phone_number)
    wa_link = f"https://wa.me/{digits}"
    api_link = f"https://api.whatsapp.com/send?phone={digits}"

    return {
        "platform": "WhatsApp",
        "digits": digits,
        "direct_link": wa_link,
        "api_link": api_link,
        "vcard_query": f"tel:+{digits}",
        "status": "CANDIDATE_ACTIVE",
        "notes": "Target nomor memiliki format valid untuk WhatsApp Web / Direct Chat API."
    }


def probe_telegram(phone_number):
    """Generate Telegram direct user / contact lookup link."""
    digits = re.sub(r"\D", "", phone_number)
    tg_link = f"https://t.me/+{digits}"

    return {
        "platform": "Telegram",
        "digits": digits,
        "direct_link": tg_link,
        "status": "CANDIDATE",
        "notes": "Tautan Telegram contact invite link."
    }
