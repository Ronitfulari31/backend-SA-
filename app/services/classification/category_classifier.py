"""
Category Classifier
-------------------
Lightweight, ingestion-safe category classifier.

Purpose:
- Classify news articles into high-level categories
- Used during RSS ingestion (scheduler)
- Must be fast, deterministic, and non-blocking

Supported Categories:
- sports
- entertainment
- business
- politics
- disaster
- terror_attack
"""

import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# -------------------------
# Category Keyword Map
# -------------------------
CATEGORY_KEYWORDS = {
    "sports": [
        "match", "tournament", "league", "goal", "score", "cricket", "football",
        "soccer", "tennis", "badminton", "olympics", "world cup", "player", "coach"
    ],
    "entertainment": [
        "film", "movie", "cinema", "actor", "actress", "bollywood", "hollywood",
        "music", "song", "album", "trailer", "web series", "netflix", "ott"
    ],
    "business": [
        "market", "stock", "shares", "investment", "revenue", "profit", "loss",
        "startup", "funding", "ipo", "company", "corporate", "economy", "trade"
    ],
    "politics": [
        "government", "election", "minister", "parliament", "policy", "law",
        "president", "prime minister", "bjp", "congress", "senate", "vote"
    ],
    "disaster": [
        "earthquake", "flood", "cyclone", "hurricane", "wildfire", "landslide",
        "tsunami", "drought", "storm", "emergency", "rescue", "evacuation"
    ],
    "terror_attack": [
        "terror", "terrorist", "attack", "bomb", "blast", "explosion",
        "suicide bombing", "militant", "gunmen", "hostage", "isis", "al-qaeda"
    ]
}

# -------------------------
# Classifier Function
# -------------------------
def classify_category(text: str, min_confidence: float = 0.15) -> Dict:
    """
    Classify text into multiple high-level news categories.

    Args:
        text (str): Combined title + summary
        min_confidence (float): Minimum confidence threshold to include a label

    Returns:
        dict: {
            "primary": str,
            "confidence": float,
            "labels": List[Dict]
        }
    """
    try:
        if not text or not isinstance(text, str):
            return {
                "primary": "unknown",
                "confidence": 0.0,
                "labels": []
            }

        text = text.lower()
        scores = {}

        for category, keywords in CATEGORY_KEYWORDS.items():
            count = 0
            for kw in keywords:
                # Word-boundary aware matching
                if re.search(rf"\b{re.escape(kw)}\b", text):
                    count += 1
            if count > 0:
                scores[category] = count

        if not scores:
            return {
                "primary": "unknown",
                "confidence": 0.0,
                "labels": []
            }

        total_hits = sum(scores.values())
        
        labels = []
        for cat, hits in scores.items():
            conf = round(hits / total_hits, 2)
            if conf >= min_confidence:
                labels.append({
                    "label": cat,
                    "confidence": conf
                })

        # Sort labels by confidence
        labels.sort(key=lambda x: x["confidence"], reverse=True)

        if not labels:
            # Fallback to top score even if below threshold if requested? 
            # Following user logic strictly:
            return {
                "primary": "unknown",
                "confidence": 0.0,
                "labels": []
            }

        primary = labels[0]["label"]
        primary_conf = labels[0]["confidence"]

        return {
            "primary": primary,
            "confidence": primary_conf,
            "labels": labels
        }

    except Exception as e:
        logger.error(f"[category_classifier] Multi-label classification failed: {e}")
        return {
            "primary": "unknown",
            "confidence": 0.0,
            "labels": []
        }
