import requests
from functools import lru_cache
from datetime import datetime

REST_COUNTRIES_API = "https://restcountries.com/v3.1/name/{}"


class CountryLanguageService:
    def __init__(self, db):
        self.db = db

        # ISO-639-3 → ISO-639-1 (NewsAPI compatible)
        self.iso_map = {
            "eng": "en",
            "hin": "hi",
            "por": "pt",
            "fra": "fr",
            "deu": "de",
            "spa": "es",
            "ara": "ar",
            "rus": "ru",
            "jpn": "ja",
            "zho": "zh"
        }

    # -------------------------------
    # IN-MEMORY CACHE (FAST PATH)
    # -------------------------------
    @lru_cache(maxsize=256)
    def _memory_cache(self, country: str) -> list[str]:
        return self._fetch_country_languages(country)

    # -------------------------------
    # MAIN ENTRY
    # -------------------------------
    def get_country_languages(self, country: str) -> list[str]:
        if not country or country == "unknown":
            return []

        # 1️⃣ MongoDB cache (persistent)
        if self.db is not None:
            cached = self.db.country_languages.find_one(
                {"country": country},
                {"_id": 0, "languages": 1}
            )
            if cached:
                return cached["languages"]

        # 2️⃣ In-memory + API fallback
        languages = self._memory_cache(country)

        if languages and self.db is not None:
            self.db.country_languages.insert_one({
                "country": country,
                "languages": languages,
                "source": "restcountries",
                "cached_at": datetime.utcnow()
            })

        return languages

    # -------------------------------
    # EXTERNAL API CALL (ONE-TIME)
    # -------------------------------
    def _fetch_country_languages(self, country: str) -> list[str]:
        try:
            resp = requests.get(
                REST_COUNTRIES_API.format(country),
                timeout=5
            )
            if resp.status_code != 200:
                return []

            data = resp.json()[0]
            langs = data.get("languages", {})

            resolved = []
            for iso3 in langs.keys():
                resolved.append(self.iso_map.get(iso3, "en"))

            # Remove duplicates, preserve order
            return list(dict.fromkeys(resolved))

        except Exception:
            return []
