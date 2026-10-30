"""Phone Intelligence Aggregator for OsintCLI.
Orchestrates HLR telco resolution, caller ID directories (Truecaller & Getcontact),
messaging status probes (WhatsApp & Telegram), and cross-pivot handle extraction.
"""
from ..adapters import item
from .hlr import lookup_hlr
from .truecaller import query_truecaller
from .getcontact import query_getcontact
from .messaging import probe_whatsapp, probe_telegram


def relationship(parent, child, source, depth, kind="PUBLIC_LINK"):
    return item(
        "relationship",
        f"{parent} → {child}",
        source,
        title=kind,
        status="CANDIDATE",
        raw={"from": parent, "to": child, "relation": kind, "depth": depth},
        reason="Korelasi identitas atau keterkaitan platform publik dari data observasi telepon."
    )


def collect_phone_intel(ctx):
    """Run full phone intelligence pipeline for OsintCLI."""
    raw_number = ctx.value

    # 1. Base format item
    yield item(
        "phone_format",
        {"international": raw_number, "digits": raw_number.lstrip("+")},
        "local:phone",
        title="Format E.164 Internasional",
        status="VERIFIED",
        reason="Normalisasi format penomoran internasional standar E.164."
    )

    # 2. HLR & Carrier Identification
    hlr = lookup_hlr(raw_number)
    status_hlr = "VERIFIED" if hlr.get("valid") else "UNVERIFIED"

    yield item(
        "phone_hlr",
        f"{hlr.get('carrier')} ({hlr.get('product')})",
        "local:hlr_database",
        title=f"Operator: {hlr.get('carrier')}",
        status=status_hlr,
        raw=hlr,
        reason=f"Identifikasi prefix {hlr.get('prefix')} alokasi regulasi telekomunikasi {hlr.get('regulator')}."
    )

    yield item(
        "phone_region",
        f"{hlr.get('country')} — {hlr.get('region')}",
        "local:hlr_database",
        title="Cakupan Wilayah / Negara",
        status=status_hlr,
        raw=hlr,
        reason="Alokasi teritorial HLR/Area kode operator."
    )

    if hlr.get("carrier") and "Tidak diketahui" not in hlr.get("carrier"):
        yield relationship(raw_number, hlr["carrier"], "local:hlr_database", 1, "OPERATED_BY")

    # 3. Messaging Presence (WhatsApp & Telegram)
    wa = probe_whatsapp(raw_number)
    yield item(
        "messaging_wa",
        wa["direct_link"],
        "whatsapp:direct",
        title="WhatsApp Direct Channel",
        status="VERIFIED",
        raw=wa,
        reason="Format nomor valid dan kompatibel dengan gateway pesan WhatsApp Web & Direct API."
    )
    yield relationship(raw_number, wa["direct_link"], "whatsapp:direct", 1, "REGISTERED_ON")

    tg = probe_telegram(raw_number)
    yield item(
        "messaging_tg",
        tg["direct_link"],
        "telegram:direct",
        title="Telegram Direct Channel",
        status="CANDIDATE",
        raw=tg,
        reason="Tautan direct contact pencarian pengguna Telegram."
    )
    yield relationship(raw_number, tg["direct_link"], "telegram:direct", 1, "REGISTERED_ON")

    # 4. Caller ID: Truecaller
    tc = query_truecaller(ctx.client, raw_number)
    if tc.get("found"):
        yield item(
            "caller_id",
            tc["name"],
            "truecaller:api",
            title=f"Truecaller ID: {tc['name']}",
            status="VERIFIED",
            raw=tc,
            reason=f"Nama terverifikasi pada direktori Truecaller. Spam score: {tc.get('spam_score')}%."
        )
        yield relationship(raw_number, tc["name"], "truecaller:api", 1, "IDENTIFIED_AS")

        if tc.get("email"):
            yield item(
                "email",
                tc["email"],
                "truecaller:api",
                title=f"Email Terkait: {tc['email']}",
                status="CANDIDATE",
                raw=tc,
                reason="Alamat email yang terasosiasi pada profil Truecaller publik."
            )
            yield relationship(raw_number, tc["email"], "truecaller:api", 1, "HAS_EMAIL")
    else:
        yield item(
            "truecaller_status",
            tc.get("message") or tc.get("error", "Tidak ada hasil"),
            "truecaller:api",
            title="Status Truecaller",
            status="UNVERIFIED",
            raw=tc,
            reason="Pemeriksaan direktori Truecaller selesai."
        )

    # 5. Caller ID & Tags: Getcontact
    gc = query_getcontact(ctx.client, raw_number)
    if gc.get("found"):
        if gc.get("name"):
            yield item(
                "caller_id",
                gc["name"],
                "getcontact:api",
                title=f"Getcontact Name: {gc['name']}",
                status="VERIFIED",
                raw=gc,
                reason="Nama primer terdaftar pada database Getcontact."
            )
            yield relationship(raw_number, gc["name"], "getcontact:api", 1, "IDENTIFIED_AS")

        tags = gc.get("tags", [])
        if tags:
            tag_summary = ", ".join(tags[:15])
            yield item(
                "phone_tags",
                tag_summary,
                "getcontact:tags",
                title=f"Tag Kontak ({len(tags)})",
                status="CANDIDATE",
                raw={"tags": tags},
                reason="Daftar tag crowdsourced dari buku kontak orang lain."
            )
            for t in tags[:10]:
                yield relationship(raw_number, t, "getcontact:tags", 1, "TAGGED_AS")

        # Auto-Pivot Candidate Handles to Social
        handles = gc.get("candidate_handles", [])
        for handle in handles:
            yield item(
                "candidate_username",
                f"@{handle}",
                "getcontact:pivot",
                title=f"Kandidat Username: @{handle}",
                status="CANDIDATE",
                raw={"handle": handle},
                reason="Handle media sosial terdeteksi dari tag kontak; dapat diinvestigasi lanjut lewat Fusion."
            )
            yield relationship(raw_number, f"@{handle}", "getcontact:pivot", 2, "POTENTIAL_ALIAS")
    else:
        yield item(
            "getcontact_status",
            gc.get("message") or gc.get("error", "Tidak ada hasil"),
            "getcontact:api",
            title="Status Getcontact",
            status="UNVERIFIED",
            raw=gc,
            reason="Pemeriksaan tag Getcontact selesai."
        )
