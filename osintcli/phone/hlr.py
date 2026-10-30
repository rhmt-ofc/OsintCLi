"""HLR and Telco Carrier Intelligence for OsintCLI.
Deterministic identification of mobile carrier, network type, and regional origin.
"""
import re

# Comprehensive Indonesian Prefix Database
ID_PREFIXES = {
    # Telkomsel (kartuHALO, simPATI, Kartu As, Loop, by.U)
    "0811": ("Telkomsel", "kartuHALO / Pascabayar", "GSM/LTE/5G"),
    "0812": ("Telkomsel", "simPATI / kartuHALO", "GSM/LTE/5G"),
    "0813": ("Telkomsel", "simPATI / kartuHALO", "GSM/LTE/5G"),
    "0821": ("Telkomsel", "simPATI", "GSM/LTE/5G"),
    "0822": ("Telkomsel", "simPATI / Loop", "GSM/LTE/5G"),
    "0823": ("Telkomsel", "Kartu As", "GSM/LTE/5G"),
    "0851": ("Telkomsel", "by.U / AS Flexi", "GSM/LTE/5G"),
    "0852": ("Telkomsel", "Kartu As", "GSM/LTE/5G"),
    "0853": ("Telkomsel", "Kartu As", "GSM/LTE/5G"),

    # Indosat Ooredoo Hutchison (IM3, Mentari, Matrix)
    "0814": ("Indosat Ooredoo", "Indosat M2 / Broadband", "GSM/LTE"),
    "0815": ("Indosat Ooredoo", "Matrix / Mentari", "GSM/LTE/5G"),
    "0816": ("Indosat Ooredoo", "Matrix / Mentari", "GSM/LTE/5G"),
    "0855": ("Indosat Ooredoo", "Matrix Auto", "GSM/LTE/5G"),
    "0856": ("Indosat Ooredoo", "IM3", "GSM/LTE/5G"),
    "0857": ("Indosat Ooredoo", "IM3", "GSM/LTE/5G"),
    "0858": ("Indosat Ooredoo", "Mentari / IM3", "GSM/LTE/5G"),

    # XL Axiata
    "0817": ("XL Axiata", "XL Pascabayar / Prabayar", "GSM/LTE/5G"),
    "0818": ("XL Axiata", "XL Prabayar", "GSM/LTE/5G"),
    "0819": ("XL Axiata", "XL Prabayar", "GSM/LTE/5G"),
    "0859": ("XL Axiata", "XL Prabayar", "GSM/LTE/5G"),
    "0877": ("XL Axiata", "XL Prabayar", "GSM/LTE/5G"),
    "0878": ("XL Axiata", "XL Prabayar", "GSM/LTE/5G"),

    # AXIS (XL Axiata)
    "0831": ("AXIS (XL Axiata)", "AXIS Prabayar", "GSM/LTE/5G"),
    "0832": ("AXIS (XL Axiata)", "AXIS Prabayar", "GSM/LTE/5G"),
    "0833": ("AXIS (XL Axiata)", "AXIS Prabayar", "GSM/LTE/5G"),
    "0838": ("AXIS (XL Axiata)", "AXIS Prabayar", "GSM/LTE/5G"),

    # Tri (Indosat Ooredoo Hutchison)
    "0895": ("Tri (3 IOH)", "Tri Prabayar", "GSM/LTE/5G"),
    "0896": ("Tri (3 IOH)", "Tri Prabayar", "GSM/LTE/5G"),
    "0897": ("Tri (3 IOH)", "Tri Prabayar", "GSM/LTE/5G"),
    "0898": ("Tri (3 IOH)", "Tri Prabayar", "GSM/LTE/5G"),
    "0899": ("Tri (3 IOH)", "Tri Prabayar", "GSM/LTE/5G"),

    # Smartfren
    "0881": ("Smartfren", "Smartfren Prabayar", "CDMA/LTE"),
    "0882": ("Smartfren", "Smartfren Prabayar", "LTE/5G"),
    "0883": ("Smartfren", "Smartfren Prabayar", "LTE/5G"),
    "0884": ("Smartfren", "Smartfren Prabayar", "LTE/5G"),
    "0885": ("Smartfren", "Smartfren Prabayar", "LTE/5G"),
    "0886": ("Smartfren", "Smartfren Prabayar", "LTE/5G"),
    "0887": ("Smartfren", "Smartfren Prabayar", "LTE/5G"),
    "0888": ("Smartfren", "Smartfren Prabayar", "LTE/5G"),
    "0889": ("Smartfren", "Smartfren Prabayar", "LTE/5G"),

    # Net1 / Sampoerna Telekom
    "0827": ("Net1 Indonesia", "Net1 4G", "LTE 450MHz"),
    "0828": ("Sampoerna Telekom", "Ceria", "CDMA/LTE"),
}

# Regional mapping based on 5-6 digit HLR prefix
ID_REGIONS = {
    # Jabodetabek / Banten / Jabar
    "08111": "Jabodetabek / Banten",
    "08112": "Jawa Barat (Bandung & Sekitarnya)",
    "08113": "Jawa Timur (Surabaya & Sekitarnya)",
    "08114": "Sulawesi & Maluku",
    "08115": "Kalimantan",
    "08116": "Sumatera Bagian Utara / Riau",
    "08117": "Sumatera Bagian Selatan",
    "08118": "DKI Jakarta",
    "08119": "DKI Jakarta",
    "08121": "Jabodetabek / Banten",
    "08122": "Jawa Barat (Bandung, Sukabumi, Cirebon)",
    "08123": "Jawa Timur (Surabaya, Malang, Jember)",
    "08124": "Sulawesi / Maluku / Papua",
    "08125": "Kalimantan Barat / Selatan / Timur",
    "08126": "Sumatera Utara / Aceh",
    "08127": "Sumatera Barat / Riau / Kepri",
    "08128": "Jabodetabek",
    "08129": "Jabodetabek / Depok / Tangerang / Bekasi",
    "08131": "Jabodetabek",
    "08132": "Jawa Tengah / DI Yogyakarta",
    "08133": "Bali / Nusa Tenggara / Jatim",
    "08136": "Sumatera Utara / Pekanbaru",
    "08137": "Sumatera Selatan / Lampung / Jambi",
    "08138": "Jabodetabek",
    "08139": "Jawa Tengah / Solo / Semarang",
    "08211": "Jabodetabek",
    "08212": "Jabodetabek / Jawa Barat",
    "08213": "Jawa Tengah / DIY",
    "08214": "Jawa Timur / Bali",
    "08522": "Jawa Barat",
    "08523": "Jawa Timur / Madura",
    "08524": "Kalimantan / Sulawesi",
    "08525": "Kalimantan Timur / Selatan",
    "08526": "Sumatera",
    "08527": "Sumatera Tengah / Selatan",
    "08528": "Jabodetabek",
    "08529": "Jawa Tengah / DIY",
    "08531": "Jabodetabek",
    "08532": "Jawa Barat",
    "08533": "Jawa Timur",
    "08571": "Jabodetabek / Banten",
    "08572": "Jawa Barat / Jawa Tengah",
    "08573": "Jawa Timur / Bali",
    "08574": "Jawa Tengah / DIY",
    "08781": "Jabodetabek / Banten",
    "08782": "Jawa Barat",
    "08783": "Jawa Tengah / DIY",
    "08784": "Jawa Timur / Bali",
    "08961": "Jabodetabek",
    "08962": "Jawa Barat",
    "08963": "Jawa Tengah",
    "08964": "Jawa Timur",
}

# International Country Code Table (ITU E.164)
COUNTRY_CODES = {
    "1": ("Amerika Serikat / Kanada", "US/CA", "NANP"),
    "44": ("Britania Raya (UK)", "GB", "Ofcom"),
    "60": ("Malaysia", "MY", "MCMC"),
    "62": ("Indonesia", "ID", "Kominfo"),
    "65": ("Singapura", "SG", "IMDA"),
    "61": ("Australia", "AU", "ACMA"),
    "81": ("Jepang", "JP", "MIC"),
    "82": ("Korea Selatan", "KR", "MSIT"),
    "86": ("Tiongkok", "CN", "MIIT"),
    "91": ("India", "IN", "DoT"),
    "49": ("Jerman", "DE", "BNetzA"),
    "33": ("Prancis", "FR", "ARCEP"),
    "7": ("Rusia / Kazakhstan", "RU/KZ", "RKN"),
    "966": ("Arab Saudi", "SA", "CST"),
    "971": ("Uni Emirat Arab", "AE", "TDRA"),
    "63": ("Filipina", "PH", "NTC"),
    "66": ("Thailand", "TH", "NBTC"),
    "84": ("Vietnam", "VN", "MIC"),
    "31": ("Belanda", "NL", "ACM"),
    "39": ("Italia", "IT", "AGCOM"),
    "34": ("Spanyol", "ES", "CNMC"),
    "55": ("Brasil", "BR", "Anatel"),
    "90": ("Turki", "TR", "BTK"),
}


def lookup_hlr(phone_str):
    """Analyze phone string for country, carrier, and regional origin."""
    digits = re.sub(r"\D", "", phone_str)
    if not digits:
        return {"valid": False, "error": "Nomor kosong"}

    country_info = None
    country_code = None
    national_number = digits

    # Identify Country Code (sort by length descending to match 966 before 9, etc.)
    for cc in sorted(COUNTRY_CODES.keys(), key=lambda x: -len(x)):
        if digits.startswith(cc):
            country_info = COUNTRY_CODES[cc]
            country_code = cc
            national_number = digits[len(cc):]
            break

    if not country_info:
        # Default fallback
        country_info = ("Internasional", "GLOBAL", "ITU-T")
        country_code = digits[:2]
        national_number = digits[2:]

    result = {
        "valid": True,
        "raw_digits": digits,
        "international": f"+{digits}",
        "country": country_info[0],
        "country_iso": country_info[1],
        "regulator": country_info[2],
        "country_code": country_code,
        "carrier": "Tidak diketahui / Operator Internasional",
        "product": "N/A",
        "network": "Cellular / PSTN",
        "region": "Nasional / Regional tidak teridentifikasi",
        "prefix": "",
    }

    # If Indonesia (+62), resolve Telco & Region
    if country_code == "62":
        # Indonesian domestic numbers start with '08' when nationalized
        domestic_prefix = "0" + national_number[:3]
        hlr_5 = "0" + national_number[:4]

        result["prefix"] = domestic_prefix
        if domestic_prefix in ID_PREFIXES:
            carrier, product, network = ID_PREFIXES[domestic_prefix]
            result["carrier"] = carrier
            result["product"] = product
            result["network"] = network

        if hlr_5 in ID_REGIONS:
            result["region"] = ID_REGIONS[hlr_5]
        elif domestic_prefix in ID_PREFIXES:
            result["region"] = "Indonesia (Cakupan Nasional)"

    return result
