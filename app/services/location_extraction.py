"""
Location Extraction Service
Level-1: Extract location mentions using spaCy
Level-2: Enrich and normalize into city/state/country using geocoder
(English-normalized, language-agnostic)
"""

import logging
import time
from typing import Dict, List
from functools import lru_cache

import spacy
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class LocationExtractionService:
    """Service for hierarchical location extraction"""

    def __init__(self):
        self.nlp = None
        self._load_spacy_model()

        # ✅ FIX: Nominatim does NOT accept `language` in constructor
        self.geolocator = Nominatim(
            user_agent="news_location_enrichment"
        )

        self.geocode = RateLimiter(
            self.geolocator.geocode,
            min_delay_seconds=1,
            swallow_exceptions=True
        )

    # -------------------------------------------------
    # spaCy
    # -------------------------------------------------

    def _load_spacy_model(self):
        try:
            logger.info("Loading spaCy model...")
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("✓ spaCy model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            logger.info("Run: python -m spacy download en_core_web_sm")

    def extract_entities(self, text: str) -> List[Dict]:
        if self.nlp is None:
            logger.error("spaCy model not loaded")
            return []

        try:
            doc = self.nlp(text)
            return [
                {
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char
                }
                for ent in doc.ents
            ]
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []

    # -------------------------------------------------
    # LEVEL-1 → LEVEL-2 PIPELINE
    # -------------------------------------------------

    def extract_locations(self, text: str) -> Dict:
        start_time = time.time()

        try:
            if not text or not text.strip() or self.nlp is None:
                return {"location": None, "extraction_time": 0.0}

            doc = self.nlp(text)

            # -------- LEVEL-1: RAW DETECTION --------
            raw_locations = []
            seen = set()

            for ent in doc.ents:
                if ent.label_ not in {"GPE", "LOC"}:
                    continue

                value = ent.text.strip()
                key = value.lower()

                if key in seen:
                    continue

                seen.add(key)
                raw_locations.append({
                    "entity_text": value,
                    "location_type": self._classify_location_type(value)
                })

            # -------- LEVEL-2: ENRICHMENT --------
            enriched = self._enrich_locations(raw_locations)

            extraction_time = round(time.time() - start_time, 3)

            logger.info(
                f"Location extraction completed | "
                f"Level-1={len(raw_locations)} | "
                f"Enriched={'yes' if enriched else 'no'} | "
                f"time={extraction_time}s"
            )

            return {
                "location": enriched,
                "extraction_time": extraction_time
            }

        except Exception as e:
            logger.error(f"Location extraction failed: {e}")
            return {
                "location": None,
                "extraction_time": round(time.time() - start_time, 3),
                "error": str(e)
            }

    # -------------------------------------------------
    # HELPERS
    # -------------------------------------------------

    def _classify_location_type(self, location_text: str) -> str:
        value = location_text.lower()

        countries = {
            "india", "usa", "united states", "china", "japan", "uk",
            "united kingdom", "france", "germany", "spain", "italy",
            "russia", "brazil", "mexico", "australia", "canada"
        }

        indian_states = {
            "maharashtra", "karnataka", "tamil nadu", "kerala",
            "gujarat", "rajasthan", "punjab", "haryana",
            "uttar pradesh", "bihar", "west bengal", "odisha"
        }

        if value in countries:
            return "country"
        if value in indian_states:
            return "state"
        return "city"

    @lru_cache(maxsize=512)
    def _cached_geocode(self, place: str):
        # ✅ FIX: Force English at REQUEST LEVEL (supported by geopy)
        return self.geocode(
            place,
            addressdetails=True,
            language="en",
            timeout=5
        )

    # -------------------------------------------------
    # LEVEL-2 ENRICHMENT
    # -------------------------------------------------

    def _enrich_locations(self, locations: List[Dict]) -> Dict | None:
        """
        Resolve detected locations into a primary city/state/country
        (Always English, never null)
        """

        # Prefer city-level first
        sorted_locations = sorted(
            locations,
            key=lambda x: 0 if x["location_type"] == "city" else 1
        )

        for loc in sorted_locations:
            try:
                geo = self._cached_geocode(loc["entity_text"])
                if not geo or not geo.raw:
                    continue

                address = geo.raw.get("address", {})

                city = (
                    address.get("city")
                    or address.get("town")
                    or address.get("village")
                )

                state = address.get("state")
                country = address.get("country")

                if not country:
                    continue

                return {
                    "city": city or "Unknown",
                    "state": state or "Unknown",
                    "country": country or "Unknown",
                    "confidence": 0.9
                }

            except Exception as e:
                logger.warning(
                    f"Geocoding failed for {loc['entity_text']}: {e}"
                )

        return None

    # -------------------------------------------------
    # SUMMARY
    # -------------------------------------------------

    def get_location_summary(self, locations: List[Dict]) -> Dict:
        summary = {
            "total_locations": len(locations),
            "cities": [],
            "states": [],
            "countries": []
        }

        for loc in locations:
            if loc.get("city"):
                summary["cities"].append(loc["city"])
            if loc.get("state"):
                summary["states"].append(loc["state"])
            if loc.get("country"):
                summary["countries"].append(loc["country"])

        summary["cities"] = list(set(summary["cities"]))
        summary["states"] = list(set(summary["states"]))
        summary["countries"] = list(set(summary["countries"]))

        return summary


# Singleton instance
location_extraction_service = LocationExtractionService()
