import logging
from functools import lru_cache
from transformers import pipeline

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# ZERO-SHOT CLASSIFIER (LOAD ONCE)
# ---------------------------------------------------------

_zero_shot_classifier = pipeline(
    task="zero-shot-classification",
    model="facebook/bart-large-mnli",
    device=-1  # CPU; change to 0 if GPU available
)

# ---------------------------------------------------------
# ALLOWED SUB-CATEGORIES PER NEWSAPI CATEGORY
# ---------------------------------------------------------

CATEGORY_SUBCATEGORIES = {
    "sports": [
        "football",
        "cricket",
        "basketball",
        "tennis",
        "other sports"
    ],
    "business": [
        "company earnings",
        "stock market",
        "mergers and acquisitions",
        "startup news",
        "business general"
    ],
    "technology": [
        "artificial intelligence",
        "product launch",
        "cybersecurity",
        "software updates",
        "technology general"
    ],
    "health": [
        "disease outbreak",
        "public health",
        "medical research",
        "medicine",
        "health general"
    ],
    "science": [
        "space exploration",
        "climate science",
        "scientific research",
        "physics",
        "science general"
    ],
    "entertainment": [
        "movies",
        "music",
        "celebrity news",
        "television",
        "entertainment general"
    ]
}

# ---------------------------------------------------------
# LABEL NORMALIZATION MAP
# ---------------------------------------------------------

LABEL_NORMALIZATION = {
    # Sports
    "football": "football",
    "cricket": "cricket",
    "basketball": "basketball",
    "tennis": "tennis",
    "other sports": "sports_general",

    # Business
    "company earnings": "earnings",
    "stock market": "stock_market",
    "mergers and acquisitions": "mergers",
    "startup news": "startup",
    "business general": "business_general",

    # Technology
    "artificial intelligence": "artificial_intelligence",
    "product launch": "product_launch",
    "cybersecurity": "cybersecurity",
    "software updates": "software_update",
    "technology general": "technology_general",

    # Health
    "disease outbreak": "disease",
    "public health": "public_health",
    "medical research": "research",
    "medicine": "medicine",
    "health general": "health_general",

    # Science
    "space exploration": "space",
    "climate science": "climate",
    "scientific research": "research",
    "physics": "physics",
    "science general": "science_general",

    # Entertainment
    "movies": "movies",
    "music": "music",
    "celebrity news": "celebrity",
    "television": "television",
    "entertainment general": "entertainment_general"
}

# ---------------------------------------------------------
# ML SUB-CATEGORY PREDICTION (CACHED)
# ---------------------------------------------------------

@lru_cache(maxsize=1024)
def ml_predict_subcategory(text: str, category: str):
    """
    Zero-shot ML fallback for sub-category detection.

    Runs ONLY when rule-based + entity-based confidence is weak.

    Returns:
        (normalized_sub_category: str | None, confidence: float)
    """

    if not text or category not in CATEGORY_SUBCATEGORIES:
        return None, 0.0

    try:
        labels = CATEGORY_SUBCATEGORIES[category]

        result = _zero_shot_classifier(
            text[:512],  # safety truncation
            candidate_labels=labels,
            multi_label=False
        )

        top_label = result["labels"][0]
        top_score = float(result["scores"][0])

        normalized = LABEL_NORMALIZATION.get(top_label)

        if not normalized:
            return None, 0.0

        # Confidence gating (IMPORTANT)
        if top_score < 0.55:
            return None, 0.0

        logger.info(
            f"[ML] Zero-shot classified '{category}' → {normalized} (conf={top_score:.2f})"
        )

        # Cap confidence to avoid overpowering rules
        return normalized, round(min(top_score, 0.85), 2)

    except Exception as e:
        logger.exception("ML sub-category classification failed")
        return None, 0.0
