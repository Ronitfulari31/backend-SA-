# -------------------------------------------------------
# LEVEL 1 AUTHORITATIVE EVENT CLASSIFIER
# Uses headline + snippet only (no scraping, no NLP models)
# -------------------------------------------------------

def normalize(text: str) -> str:
    return (text or "").lower()


# -------------------------
# EVENT RULE DEFINITIONS
# -------------------------

EVENT_RULES = [
    # -------- SPORTS --------
    {
        "event_type": "sports_tournament",
        "phrases": ["championship", "tournament", "cup", "bracket", "playoffs"],
        "sports": [
            "cricket", "football", "soccer", "volleyball",
            "basketball", "tennis", "hockey"
        ]
    },
    {
        "event_type": "sports_match",
        "phrases": ["match", "vs", "defeats", "beats"],
        "sports": [
            "cricket", "football", "soccer", "basketball",
            "hockey", "tennis"
        ]
    },
    {
        "event_type": "sports_schedule",
        "phrases": ["schedule", "fixtures", "draw announced"],
        "sports": []
    },

    # -------- DISASTERS --------
    {
        "event_type": "natural_disaster",
        "phrases": ["earthquake", "aftershock", "richter"],
        "sub_category": "earthquake"
    },
    {
        "event_type": "natural_disaster",
        "phrases": ["flood", "flash flood", "inundated"],
        "sub_category": "flood"
    },
    {
        "event_type": "natural_disaster",
        "phrases": ["wildfire", "forest fire", "blaze"],
        "sub_category": "fire"
    },
    {
        "event_type": "natural_disaster",
        "phrases": ["tsunami", "tidal wave"],
        "sub_category": "tsunami"
    },

    # -------- BUSINESS --------
    {
        "event_type": "business_earnings",
        "phrases": ["earnings", "revenue", "profit", "q1", "q2", "q3", "q4"],
        "sub_category": "earnings"
    },
    {
        "event_type": "business_market",
        "phrases": ["stocks", "shares", "market falls", "market rises"],
        "sub_category": "stock_market"
    },

    # -------- TECHNOLOGY --------
    {
        "event_type": "tech_product",
        "phrases": ["launches", "unveils", "introduces"],
        "sub_category": "product_launch"
    },
    {
        "event_type": "tech_ai",
        "phrases": ["artificial intelligence", "ai model", "machine learning"],
        "sub_category": "ai"
    }
]


KNOWN_SPORT_NAMES = {
    "cricket", "football", "soccer", "volleyball",
    "basketball", "tennis", "hockey", "golf",
    "rugby", "badminton", "athletics", "baseball"
}


# -------------------------------------------------------
# MAIN LEVEL-1 CLASSIFIER
# -------------------------------------------------------

def level1_event_classify(title: str, description: str) -> dict:
    """
    Returns:
    {
        event_type: str,
        sub_category: str,
        confidence: float
    }
    """
    text = normalize(f"{title} {description}")

    for rule in EVENT_RULES:
        if any(p in text for p in rule["phrases"]):

            if "sports" in rule:
                for sport in rule["sports"]:
                    if sport in text:
                        return {
                            "event_type": rule["event_type"],
                            "sub_category": sport,
                            "confidence": 0.75
                        }

                return {
                    "event_type": rule["event_type"],
                    "sub_category": "sports_general",
                    "confidence": 0.55
                }

            return {
                "event_type": rule["event_type"],
                "sub_category": rule.get("sub_category", "general"),
                "confidence": 0.65
            }

    for sport in KNOWN_SPORT_NAMES:
        if sport in text:
            return {
                "event_type": "sports_event",
                "sub_category": sport,
                "confidence": 0.6
            }

    return {
        "event_type": "general_event",
        "sub_category": "general",
        "confidence": 0.3
    }


# -------------------------------------------------------
# DOMAIN-SAFE FALLBACK (NEW)
# -------------------------------------------------------

def apply_domain_fallback(category, sub_category, confidence):
    """
    Ensures sub_category is never None.
    Used by fetcher, not by classifier logic.
    """
    if sub_category:
        return sub_category, confidence

    return f"{category}_general", 0.2
