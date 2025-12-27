# app/services/fetch/classification.py

# ---------------------------------------------------------
# LEVEL 1 SUB-CATEGORY RULES
# ---------------------------------------------------------

SPORTS_SUBCATEGORY_RULES = {
    "cricket": {
        "phrases": ["cricket", "test match", "one day international", "ipl", "icc"],
        "signals": ["runs", "wickets", "overs", "batsman", "bowler"]
    },
    "football": {
        "phrases": ["football", "soccer", "fifa", "uefa", "premier league"],
        "signals": ["goal", "penalty", "striker"]
    },
    "basketball": {
        "phrases": ["basketball", "nba", "wnba"],
        "signals": ["dunk", "three-pointer", "playoffs"]
    },
    "tennis": {
        "phrases": ["tennis", "wimbledon", "us open", "grand slam"],
        "signals": ["set", "match point", "atp", "wta"]
    }
}

DISASTER_SUBCATEGORY_RULES = {
    "earthquake": {
        "phrases": ["earthquake", "seismic", "richter"],
        "signals": ["aftershock", "epicenter", "tremors"]
    },
    "flood": {
        "phrases": ["flood", "flash flood", "river overflow"],
        "signals": ["submerged", "evacuation", "water level"]
    },
    "fire": {
        "phrases": ["wildfire", "forest fire", "blaze"],
        "signals": ["firefighters", "smoke"]
    },
    "tsunami": {
        "phrases": ["tsunami", "tidal wave"],
        "signals": ["coastal evacuation", "waves hit"]
    }
}

BUSINESS_SUBCATEGORY_RULES = {
    "earnings": {
        "phrases": ["earnings", "profit", "revenue", "q1", "q2", "q3", "q4"],
        "signals": ["results", "growth", "decline"]
    },
    "stock_market": {
        "phrases": ["stocks", "shares", "market"],
        "signals": ["index", "trading", "investors"]
    }
}

TECHNOLOGY_SUBCATEGORY_RULES = {
    "product_launch": {
        "phrases": ["launches", "unveils", "introduces"],
        "signals": ["device", "feature", "upgrade"]
    },
    "artificial_intelligence": {
        "phrases": ["artificial intelligence", "ai model", "machine learning"],
        "signals": ["training", "neural", "llm"]
    }
}

LEVEL1_RULE_MAP = {
    "sports": SPORTS_SUBCATEGORY_RULES,
    "general": DISASTER_SUBCATEGORY_RULES,
    "health": DISASTER_SUBCATEGORY_RULES,
    "business": BUSINESS_SUBCATEGORY_RULES,
    "technology": TECHNOLOGY_SUBCATEGORY_RULES
}

# ---------------------------------------------------------
# ENTITY BOOSTING
# ---------------------------------------------------------

ENTITY_BOOST_MAP = {
    "sports": {
        "eagles": "football",
        "nfl": "football",
        "ipl": "cricket",
        "icc": "cricket",
        "nba": "basketball",
        "wimbledon": "tennis"
    },
    "business": {
        "apple": "earnings",
        "google": "earnings",
        "amazon": "earnings",
        "ipo": "stock_market",
        "nasdaq": "stock_market"
    },
    "technology": {
        "openai": "artificial_intelligence",
        "chatgpt": "artificial_intelligence",
        "iphone": "product_launch",
        "android": "product_launch"
    },
    "health": {
        "covid": "public_health",
        "who": "public_health",
        "cancer": "disease",
        "vaccine": "medicine"
    },
    "science": {
        "nasa": "space",
        "spacex": "space",
        "climate": "climate",
        "research": "research"
    },
    "entertainment": {
        "netflix": "movies",
        "oscars": "movies",
        "spotify": "music",
        "album": "music"
    }
}

def apply_entity_boost(text, category, sub_category, confidence):
    boosts = ENTITY_BOOST_MAP.get(category, {})
    text = text.lower()

    for entity, boosted_sub in boosts.items():
        if entity in text and sub_category.endswith("_general"):
            return boosted_sub, min(confidence + 0.25, 0.85)

    return sub_category, confidence

# ---------------------------------------------------------
# SUB-CATEGORY DETECTION
# ---------------------------------------------------------

def detect_subcategory_with_confidence(text: str, rules: dict):
    if not text or not rules:
        return None, 0.0

    text = text.lower()
    best_label = None
    best_score = 0

    for label, rule in rules.items():
        score = 0
        for phrase in rule.get("phrases", []):
            if phrase in text:
                score += 3
        for signal in rule.get("signals", []):
            if signal in text:
                score += 1
        if score > best_score:
            best_score = score
            best_label = label

    if best_score == 0:
        return None, 0.0

    return best_label, round(min(1.0, best_score / 6), 2)

def apply_domain_fallback(category, sub_category, confidence):
    return (sub_category, confidence) if sub_category else (f"{category}_general", 0.2)

def compute_display_sub_category(category, sub_category, confidence):
    return sub_category if confidence >= 0.4 else f"{category}_general"
