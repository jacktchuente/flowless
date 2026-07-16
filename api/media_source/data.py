from enum import StrEnum

languages = [
    "ar",
    "de",
    "en",
    "es",
    "fr",
    "hi",
    "it",
    "ja",
    "ko",
    "nl",
    "pl",
    "pt",
    "ru",
    "sv",
    "tr",
    "uk",
    "zh",
]


class NormalizationFieldType(StrEnum):
    LANGUAGE = "language"
    COUNTRY = "country"


# Valeurs spéciales / non exploitables
IGNORED_LANGUAGE_VALUES = {
    "und",  # undefined
    "unknown",
    "mul",  # multiple languages
    "mis",  # uncoded languages
    "",
}

IGNORED_COUNTRY_VALUES = {
    "",
    "unknown",
    "und",
}

# -------------------------------------------------------------------
# Languages
# Canonical target = ISO 639-1 when possible
# -------------------------------------------------------------------
LANGUAGE_NORMALIZATION_MAP = {
    # French
    "fre": "fr",
    "fra": "fr",
    "fr": "fr",
    "french": "fr",
    "francais": "fr",
    "français": "fr",
    "vf": "fr",

    # English
    "eng": "en",
    "en": "en",
    "english": "en",
    "anglais": "en",

    # Japanese
    "jpn": "ja",
    "ja": "ja",
    "japanese": "ja",
    "japonais": "ja",

    # German
    "ger": "de",
    "deu": "de",
    "de": "de",
    "german": "de",
    "allemand": "de",

    # Italian
    "ita": "it",
    "it": "it",
    "italian": "it",
    "italien": "it",

    # Spanish
    "spa": "es",
    "es": "es",
    "spanish": "es",
    "espagnol": "es",

    # Portuguese
    "por": "pt",
    "pt": "pt",
    "portuguese": "pt",
    "portugais": "pt",

    # Chinese
    "chi": "zh",
    "zho": "zh",
    "zh": "zh",
    "chinese": "zh",
    "chinois": "zh",

    # Korean
    "kor": "ko",
    "ko": "ko",
    "korean": "ko",
    "coreen": "ko",
    "coréen": "ko",

    # Arabic
    "ara": "ar",
    "ar": "ar",
    "arabic": "ar",
    "arabe": "ar",

    # Russian
    "rus": "ru",
    "ru": "ru",
    "russian": "ru",
    "russe": "ru",

    # Dutch
    "dut": "nl",
    "nld": "nl",
    "nl": "nl",
    "dutch": "nl",
    "neerlandais": "nl",
    "néerlandais": "nl",

    # Czech
    "cze": "cs",
    "ces": "cs",
    "cs": "cs",
    "czech": "cs",
    "tcheque": "cs",
    "tchèque": "cs",

    # Romanian
    "rum": "ro",
    "ron": "ro",
    "ro": "ro",
    "romanian": "ro",
    "roumain": "ro",

    # Persian / Farsi
    "per": "fa",
    "fas": "fa",
    "fa": "fa",
    "persian": "fa",
    "farsi": "fa",

    # Danish
    "dan": "da",
    "da": "da",

    # Swedish
    "swe": "sv",
    "sv": "sv",

    # Vietnamese
    "vie": "vi",
    "vi": "vi",

    # Indonesian
    "ind": "id",
    "id": "id",

    # Thai
    "tha": "th",
    "th": "th",

    # Croatian
    "hrv": "hr",
    "hr": "hr",

    # Finnish
    "fin": "fi",
    "fi": "fi",

    # Greek
    "gre": "el",
    "ell": "el",
    "el": "el",

    # Hebrew
    "heb": "he",
    "he": "he",

    # Hungarian
    "hun": "hu",
    "hu": "hu",

    # Malay
    "may": "ms",
    "msa": "ms",
    "ms": "ms",

    # Norwegian Bokmål
    "nob": "no",
    "no": "no",

    # Polish
    "pol": "pl",
    "pl": "pl",

    # Turkish
    "tur": "tr",
    "tr": "tr",

    # Some noisy values seen in media libs
    "new": None,
}

# -------------------------------------------------------------------
# Countries
# Canonical target = ISO 3166-1 alpha-2
# -------------------------------------------------------------------
COUNTRY_NORMALIZATION_MAP = {
    "united states of america": "US",
    "united states": "US",
    "usa": "US",
    "us": "US",

    "france": "FR",
    "fr": "FR",

    "japan": "JP",
    "jp": "JP",

    "united kingdom": "GB",
    "uk": "GB",
    "great britain": "GB",
    "gb": "GB",

    "germany": "DE",
    "de": "DE",

    "belgium": "BE",
    "be": "BE",

    "china": "CN",
    "cn": "CN",

    "canada": "CA",
    "ca": "CA",

    "hong kong": "HK",
    "hk": "HK",

    "russia": "RU",
    "ru": "RU",

    "australia": "AU",
    "au": "AU",

    "czech republic": "CZ",
    "czechia": "CZ",
    "cz": "CZ",

    "hungary": "HU",
    "hu": "HU",

    "chile": "CL",
    "cl": "CL",

    "mexico": "MX",
    "mx": "MX",

    "sweden": "SE",
    "se": "SE",

    "india": "IN",
    "in": "IN",

    "south africa": "ZA",
    "za": "ZA",

    "cuba": "CU",
    "cu": "CU",

    "malta": "MT",
    "mt": "MT",

    "new zealand": "NZ",
    "nz": "NZ",

    "taiwan": "TW",
    "tw": "TW",
}
