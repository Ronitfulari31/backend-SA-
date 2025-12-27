from app.services.metadata.country_language_service import CountryLanguageService
from app.services.metadata.geo_language_service import GeoLanguageService
from app.services.fetch.resolver_metrics import log_resolver_metrics
import logging

logger = logging.getLogger(__name__)


def resolve_context(params: dict, db=None) -> dict:
    if db is not None:
        log_resolver_metrics(db, "resolver_calls_total")
        geo_lang_service = GeoLanguageService(db)
        country_lang_service = CountryLanguageService(db)
    else:
        geo_lang_service = GeoLanguageService(None)
        country_lang_service = CountryLanguageService(None)

    city = params.get("city", "unknown")
    state = params.get("state", "unknown")
    country = params.get("country", "unknown")
    continent = params.get("continent", "unknown")

    # ---------------- SCOPE ----------------
    if city != "unknown":
        scope = "city"
    elif state != "unknown":
        scope = "state"
    elif country != "unknown":
        scope = "country"
    elif continent != "unknown":
        scope = "continent"
    else:
        scope = "global"

    # ---------------- LANGUAGE RESOLUTION ----------------
    if params.get("language"):
        languages = [params["language"]]
    else:
        languages = []

        if city != "unknown":
            languages += geo_lang_service.get_city_languages(city, state)
            languages += geo_lang_service.get_state_languages(state)
            languages += country_lang_service.get_country_languages(country)

        elif state != "unknown":
            languages += geo_lang_service.get_state_languages(state)
            languages += country_lang_service.get_country_languages(country)

        elif country != "unknown":
            languages += country_lang_service.get_country_languages(country)

        elif continent != "unknown":
            languages += geo_lang_service.get_continent_languages(continent)

        if not languages:
            languages = ["en"]

        languages = list(dict.fromkeys(languages))

    category = params.get("category") or "unknown"

    # ---------------- LOGGING ----------------
    if db is not None and languages == ["en"]:
        log_resolver_metrics(db, "resolver_fallback_used")

    logger.info(
        "[resolver] scope=%s | city=%s | state=%s | country=%s | languages=%s |category=%s",
        scope, city, state, country, languages, category
    )

    return {
        "scope": scope,
        "continent": continent,
        "country": country,
        "state": state,
        "city": city,
        "language": languages,
        "category": category
    }
