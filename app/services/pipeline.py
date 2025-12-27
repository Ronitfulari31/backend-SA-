"""
Pipeline Service
Orchestrates the document through all NLP stages (Language-Agnostic)
"""

import time
import logging
import unicodedata
from bson import ObjectId
from datetime import datetime
from app.models.document import Document
from app.services.preprocessing import preprocessing_service
from app.services.translation import translation_service
from app.services.sentiment import get_sentiment_service
from app.services.event_detection import get_event_detection_service
from app.services.location_extraction import location_extraction_service
from app.services.summarization import summarization_service
from app.services.keyword_extraction import keyword_extraction_service
from app.services.ner import ner_service

logger = logging.getLogger(__name__)

PIPELINE_ORDER = [
    "preprocessing",
    "translation",
    "event",
    "location",
    "summary",
    "sentiment",
    "keywords",
    "entities"
]

# ---------------------------------------------------------
# DOMAIN GUARDRAILS
# ---------------------------------------------------------

def apply_domain_guardrails(category, event_type, confidence):
    if confidence < 0.6:
        logger.info(f"[GUARD] Low confidence ({confidence}) → forcing event_type=other")
        return "other", 0.0

    if category == "sports" and event_type in {
        "terror_attack", "crime", "war", "natural_disaster"
    }:
        logger.warning(
            f"[GUARD] Blocked cross-domain event '{event_type}' for sports article"
        )
        return "other", 0.0

    return event_type, confidence


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def normalize_text(text: str) -> str:
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text).strip()


def resolve_language(document, detected_language):
    stored_lang = document.get("language")
    if stored_lang and stored_lang != "unknown":
        return stored_lang
    return detected_language or "unknown"




def safe_translate(db, doc_id, text, language, collection="documents"):
    source_lang = translation_service.normalize_for_translation(language)

    if source_lang == "en":
        return text

    result = translation_service.translate_to_english(text, source_lang)

    if not result.get("success"):
        logger.error(f"[{doc_id}] Translation failed → continuing with original text")
        return text

    Document.update_translation(
        db,
        doc_id,
        result["translated_text"],
        result["translation_engine"],
        result["translation_time"],
        collection=collection
    )

    return result["translated_text"]


def safe_location_value(value):
    if not value or not isinstance(value, str):
        return "Unknown"
    return value.strip()


# ---------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------

def process_document_pipeline(db, doc_id, raw_text, stages=None, collection="documents"):
    try:
        start_time = time.time()
        logger.info(f"[{doc_id}] ▶ Pipeline started (collection: {collection})")

        stages = set(stages) if stages else None
        should_run = lambda s: stages is None or s in stages

        # State containers for atomic update
        summary = ""
        sentiment = {}
        keywords = []
        entities = []
        event = {}
        locations = {}

        # ---------------- Stage 1: Preprocessing ----------------
        if should_run("preprocessing"):
            preprocess_result = preprocessing_service.preprocess(raw_text)
            clean_text = normalize_text(preprocess_result.get("clean_text") or raw_text)
            
            # Note: clean_text and language are still root fields
            db[collection].update_one(
                {"_id": ObjectId(doc_id)},
                {"$set": {
                    "cleaned_text": clean_text,
                    "language": preprocess_result.get("language"),
                    "text_hash": preprocess_result.get("text_hash")
                }}
            )
        else:
            doc = db[collection].find_one({"_id": ObjectId(doc_id)})
            clean_text = doc.get("cleaned_text", "")
            preprocess_result = {"language": doc.get("language")}

        doc = db[collection].find_one({"_id": ObjectId(doc_id)})
        language = resolve_language(doc, preprocess_result.get("language"))

        # ---------------- Stage 2: Translation ----------------
        analysis_text = safe_translate(db, doc_id, clean_text or raw_text, language, collection=collection)

        if not analysis_text.strip():
            raise ValueError("Analysis text empty")

        # ---------------- Stage 3: Event Detection ----------------
        if should_run("event"):
            event_service = get_event_detection_service()
            event_result = event_service.classify(analysis_text, method="hybrid")
            
            category = doc.get("metadata", {}).get("category")
            safe_type, safe_conf = apply_domain_guardrails(
                category, event_result["event_type"], event_result["confidence"]
            )
            event = {
                "type": safe_type,
                "confidence": safe_conf,
                "classification_time": event_result["classification_time"]
            }

        # ---------------- Stage 4: Locations ----------------
        if should_run("location") or should_run("locations"):
            location_result = location_extraction_service.extract_locations(analysis_text) or {}
            raw_loc = location_result.get("enriched_location") or location_result.get("normalized") or {}
            
            locations = {
                "city": safe_location_value(raw_loc.get("city")),
                "state": safe_location_value(raw_loc.get("state")),
                "country": safe_location_value(raw_loc.get("country")),
                "confidence": raw_loc.get("confidence", 0.0)
            }

        # ---------------- Stage 5: Summary ----------------
        if should_run("summary"):
            summary = summarization_service.summarize(analysis_text, method="lsa", sentences_count=3)

        # ---------------- Stage 6: Sentiment ----------------
        if should_run("sentiment"):
            sentiment_service = get_sentiment_service()
            sent_result = sentiment_service.analyze(
                cleaned_text=analysis_text,
                summary_text=summary,
                raw_text=analysis_text,
                method="auto"
            )
            sentiment = {
                "label": sent_result["sentiment"],
                "confidence": sent_result["confidence"],
                "method": sent_result["method"],
                "scores": sent_result.get("scores", {}),
                "analysis_time": sent_result.get("analysis_time", 0.0)
            }

        # ---------------- Stage 7: Keywords ----------------
        if should_run("keywords"):
            keywords = keyword_extraction_service.extract(analysis_text, method="rake", top_n=10)

        # ---------------- Stage 8: Entities ----------------
        if should_run("entities"):
            entities = ner_service.extract_entities(analysis_text)

        # ---------------- Type Assertions (PATCH 3) ----------------
        assert isinstance(summary, str), "Summary must be string"
        assert isinstance(sentiment, dict), "Sentiment must be dict"
        assert isinstance(keywords, list), "Keywords must be list"
        assert isinstance(entities, list), "Entities must be list"
        assert isinstance(event, dict), "Event must be dict"
        assert isinstance(locations, dict), "Locations must be dict"

        # ---------------- Atomic Update (PATCH 4) ----------------
        update_payload = {
            "summary": summary,
            "sentiment": sentiment,
            "keywords": keywords,
            "entities": entities,
            "event": event,
            "locations": locations,
            "analyzed": True,
            "metadata.status": "completed",
            "metadata.analysis_stage": "level_2_complete",
            "analyzed_at": datetime.utcnow()
        }

        # Final write
        db[collection].update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": update_payload}
        )

        total_time = time.time() - start_time
        Document.mark_processed(db, doc_id, total_time, collection=collection)

        logger.info(f"[{doc_id}] ✅ Pipeline completed successfully")
        return {"success": True, "processing_time": total_time}

    except Exception as e:
        logger.exception(f"[{doc_id}] ❌ Pipeline failed")
        return {"success": False, "error": str(e)}

    except Exception as e:
        logger.exception(f"[{doc_id}] ❌ Pipeline failed")
        return {"success": False, "error": str(e)}
