from enum import StrEnum

categories = [
    "action",
    "adventure",
    "animation",
    "comedy",
    "crime",
    "documentary",
    "drama",
    "education",
    "fantasy",
    "history",
    "horror",
    "kids",
    "lifestyle",
    "music",
    "mystery",
    "news",
    "reality",
    "romance",
    "science_fiction",
    "sport",
    "thriller",
    "war",
    "western",
]

themes = {
    "crime": [
        "police",
        "detective",
        "investigation",
        "forensics",
        "courtroom",
        "legal",
        "prison",
        "mafia",
        "gang",
        "heist",
        "corruption",
        "serial_killer",
        "espionage",
        "surveillance",
        "missing_person",
    ],
    "thriller": [
        "psychological",
        "suspense",
        "conspiracy",
        "manhunt",
        "revenge",
        "survival",
        "stalking",
        "dark_secret",
        "whodunit",
        "hidden_identity",
    ],
    "action": [
        "military",
        "special_forces",
        "chase",
        "combat",
        "explosion",
        "rescue_mission",
    ],
    "adventure": [
        "adventure_quest",
        "treasure_hunt",
        "expedition",
        "road_trip",
        "survival_journey",
    ],
    "science_fiction": [
        "dystopia",
        "utopia",
        "time_travel",
        "space",
        "alien",
        "robots",
        "artificial_intelligence",
        "cyberpunk",
        "virtual_reality",
        "mutation",
        "parallel_world",
    ],
    "fantasy": [
        "magic",
        "myth",
        "dragons",
        "witches",
        "supernatural",
        "heroic_fantasy",
        "dark_fantasy",
    ],
    "drama": [
        "family",
        "friendship",
        "coming_of_age",
        "relationship",
        "breakup",
        "marriage",
        "social_conflict",
        "grief",
        "redemption",
        "betrayal",
    ],
    "romance": [
        "love_triangle",
        "relationship",
        "marriage",
        "breakup",
        "forbidden_love",
        "second_chance",
    ],
    "documentary": [
        "true_crime",
        "biography",
        "nature",
        "wildlife",
        "science",
        "technology",
        "space_science",
        "archaeology",
        "society",
        "politics",
        "economy",
        "health",
        "medicine",
        "psychology",
        "travel",
        "food",
        "art",
        "culture",
        "religion",
    ],
    "history": [
        "ancient_history",
        "medieval",
        "renaissance",
        "world_war_1",
        "world_war_2",
        "cold_war",
        "resistance",
        "revolution",
        "empire",
    ],
    "war": [
        "battlefront",
        "resistance",
        "military_strategy",
        "occupation",
        "veterans",
    ],
    "kids": [
        "preschool",
        "cartoon",
        "teen",
        "educational_kids",
        "animals",
        "fairy_tale",
        "school_life",
    ],
    "animation": [
        "cartoon",
        "anime",
        "family_animation",
        "adult_animation",
        "cgi_animation",
    ],
    "lifestyle": [
        "home",
        "renovation",
        "cooking",
        "fashion",
        "dating",
        "makeover",
        "wellness",
    ],
    "reality": [
        "talent_show",
        "competition",
        "dating",
        "survival_show",
        "makeover",
        "docu_reality",
    ],
    "music": [
        "concert",
        "live_music",
        "music_video",
        "backstage",
        "artist_portrait",
        "pop",
        "rock",
        "rap",
        "jazz",
        "classical",
        "electronic",
        "world_music",
    ],
    "sport": [
        "football",
        "basketball",
        "tennis",
        "combat_sports",
        "motorsport",
        "cycling",
        "athletics",
        "winter_sports",
        "esports",
        "sports_documentary",
    ],
    "news": [
        "current_affairs",
        "debate",
        "interview",
        "breaking_news",
        "geopolitics",
        "local_news",
    ],
    "mystery": [
        "whodunit",
        "hidden_identity",
        "disappearance",
        "cold_case",
        "secret_society",
    ],
    "comedy": [
        "satire",
        "parody",
        "buddy_comedy",
        "romantic_comedy",
        "dark_comedy",
        "workplace_comedy",
    ],
    "horror": [
        "supernatural_horror",
        "slasher",
        "monster",
        "haunted_house",
        "body_horror",
        "occult",
    ],
    "western": [
        "outlaw",
        "frontier",
        "gunslinger",
        "sheriff",
        "revenge",
    ],
    "education": [
        "science",
        "history",
        "geography",
        "language_learning",
        "educational_kids",
        "how_it_works",
    ],
}

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
