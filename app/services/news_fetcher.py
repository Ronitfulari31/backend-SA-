import logging
import requests
import trafilatura
from datetime import datetime, timezone
from newspaper import Article, Config
from flask import current_app
from bs4 import BeautifulSoup

from bson import ObjectId

from app.models.document import Document
from app.services.pipeline import process_document_pipeline
from app.services.sentiment import get_sentiment_service
from app.services.ml_subcategory import ml_predict_subcategory

logger = logging.getLogger(__name__)

NEWS_API_TOP_HEADLINES = "https://newsapi.org/v2/top-headlines"

# ---------------------------------------------------------
# HELPER
# ---------------------------------------------------------

def is_missing(value):
    if value is None:
        return True

    if isinstance(value, str):
        stripped = value.strip().lower()
        if stripped in ("", "null", "none"):
            return True
        # Validation helper (not NLP-related)
        return False

    if isinstance(value, dict):
        if len(value) == 0:
            return True
        # 🟢 Added: Check if core sentiment fields are uninitialized
        if "label" in value and value["label"] in (None, "null", "pending"):
            return True
        return False

    if isinstance(value, list):
        return len(value) == 0

    return False

# ---------------------------------------------------------
# LEVEL 1 SUB-CATEGORY RULES (UNCHANGED)
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
# ENTITY BOOSTING (UNCHANGED)
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
# SUB-CATEGORY DETECTION (UNCHANGED)
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

# ---------------------------------------------------------
# SOFT RANKING (UNCHANGED)
# ---------------------------------------------------------

CATEGORY_RANKING_BIAS = {
    "sports": 0.10,
    "business": 0.08,
    "technology": 0.08,
    "health": 0.06,
    "science": 0.06,
    "entertainment": 0.05,
    "general": 0.0
}

def compute_ranking_score(confidence, status, published_date, category):
    confidence_part = confidence * 0.5
    analysis_part = 0.25 if status == "completed" else 0.0
    recency_part = 0.0

    if published_date:
        try:
            published = datetime.fromisoformat(published_date.replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - published).total_seconds() / 3600
            recency_part = max(0.0, 1.0 - min(age_hours / 48, 1.0)) * 0.15
        except Exception:
            pass

    category_bias = CATEGORY_RANKING_BIAS.get(category, 0.0)
    return round(confidence_part + analysis_part + recency_part + category_bias, 3)

# ---------------------------------------------------------
# ARTICLE EXTRACTION (UNCHANGED)
# ---------------------------------------------------------

def extract_article_package(url: str):
    if not url:
        return {"success": False}, None

    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            content = trafilatura.extract(downloaded)
            if content:
                return {"success": True, "content": content}, url
    except Exception:
        logger.warning("Trafilatura extraction failed")

    try:
        config = Config()
        config.browser_user_agent = "Mozilla/5.0"
        article = Article(url, config=config)
        article.download()
        article.parse()
        if article.text:
            return {"success": True, "content": article.text}, article.canonical_link or url
    except Exception:
        logger.warning("Newspaper extraction failed")

    return {"success": False}, url

# ---------------------------------------------------------
# ARTICLE IMAGE EXTRACTION (UNCHANGED)
# ---------------------------------------------------------

def extract_article_image(url: str):
    if not url:
        return None

    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            return og["content"]

        tw = soup.find("meta", attrs={"name": "twitter:image"})
        if tw and tw.get("content"):
            return tw["content"]

    except Exception:
        logger.warning("Article image extraction failed", exc_info=True)

    return None

# ---------------------------------------------------------
# MAIN SERVICE (LEVEL-1 + CLICK-DRIVEN LEVEL-2)
# ---------------------------------------------------------

class NewsFetcherService:



    def fetch_category_news(self, db, user_id, category):
        api_key = current_app.config.get("NEWSAPI_KEY")
        if not api_key:
            raise RuntimeError("NEWSAPI_KEY missing")

        response = requests.get(
            NEWS_API_TOP_HEADLINES,
            params={
                "category": category,
                "language": "en",
                "pageSize": 20,
                "apiKey": api_key
            },
            timeout=30
        )

        if response.status_code != 200:
            return {"status": "error", "message": "NewsAPI error"}

        rules = LEVEL1_RULE_MAP.get(category)
        results = []

        for article in response.json().get("articles", []):
            url = article.get("url")
            if not url:
                continue

            text = f"{article.get('title','')} {article.get('description','')}"

            sub_category, confidence = detect_subcategory_with_confidence(text, rules)
            sub_category, confidence = apply_domain_fallback(category, sub_category, confidence)
            sub_category, confidence = apply_entity_boost(text, category, sub_category, confidence)

            if confidence < 0.4 or sub_category.endswith("_general"):
                ml_sub, ml_conf = ml_predict_subcategory(text, category)
                if ml_sub and ml_conf > confidence:
                    sub_category = ml_sub
                    confidence = ml_conf

            display_sub_category = compute_display_sub_category(
                category, sub_category, confidence
            )

            ranking_score = compute_ranking_score(
                confidence,
                "ingested",
                article.get("publishedAt"),
                category
            )

            # -----------------------------------------------------
            # LEVEL-1 SENTIMENT (MITIGATE NULLS)
            # -----------------------------------------------------
            sentiment_svc = get_sentiment_service()
            l1_sentiment = sentiment_svc.analyze(text, method="vader")

            doc_id = Document.create(
                db=db,
                user_id=user_id,
                raw_text=article.get("description") or article.get("title"),
                source="news",
                metadata={
                    "title": article.get("title"),
                    "original_url": url,
                    "publisher": article.get("source", {}).get("name"),
                    "published_date": article.get("publishedAt"),
                    "category": category,
                    "sub_category": sub_category,
                    "sub_category_confidence": confidence,
                    "display_sub_category": display_sub_category,
                    "ranking_score": ranking_score,
                    "thumbnail_image_url": article.get("urlToImage"),
                    "thumbnail_image_source": "newsapi",
                    "status": "ingested",
                    "analysis_stage": "level_1_only",
                    "event_scope": "level_1"
                }
            )

            # PROACTIVE UPDATE: Save Level-1 sentiment immediately
            Document.update_sentiment(
                db, doc_id,
                label=l1_sentiment["sentiment"],
                confidence=l1_sentiment["confidence"],
                method=f"preliminary_{l1_sentiment['method']}",
                scores=l1_sentiment.get("scores", {}),
                time_taken=l1_sentiment["analysis_time"]
            )

            results.append({
                "id": str(doc_id),
                "title": article.get("title"),
                "category": category,
                "display_sub_category": display_sub_category,
                "confidence": confidence,
                "ranking_score": ranking_score,
                "thumbnail_image_url": article.get("urlToImage"),
                "original_url": article.get("url"),
                "source": article.get("source", {}).get("name"),
                "sentiment": {
                    "label": l1_sentiment["sentiment"],
                    "confidence": l1_sentiment["confidence"]
                }
            })

        results.sort(key=lambda x: x["ranking_score"], reverse=True)

        return {
            "status": "success",
            "category": category,
            "count": len(results),
            "articles": results
        }

    # -----------------------------------------------------
    # UPDATED: FULL + PARTIAL ANALYSIS SUPPORT
    # -----------------------------------------------------

    def scrape_and_analyze_article(self, db, doc_id, stages=None):

        doc = db.documents.find_one({"_id": ObjectId(doc_id)})
        if not doc:
            return

        meta = doc.get("metadata", {})

        if not stages and meta.get("analysis_stage") == "level_2_complete":
            logger.info(f"[{doc_id}] Analysis already complete → skipping")
            return

        db.documents.update_one(
            {"_id": doc["_id"]},
            {"$set": {
                "metadata.status": "analyzing",
                "metadata.analysis_stage": "level_2_in_progress"
            }}
        )

        extraction, resolved_url = extract_article_package(meta.get("original_url"))
        if not extraction["success"]:
            return

        content = extraction["content"]
        article_image = extract_article_image(resolved_url)

        # ---------------- FULL / PARTIAL PIPELINE ----------------
        process_document_pipeline(
            db=db,
            doc_id=str(doc["_id"]),
            raw_text=content,
            stages=stages
        )

        # ---------------- FINAL METADATA (UNCHANGED)
        new_ranking = compute_ranking_score(
            meta.get("sub_category_confidence", 0),
            "completed",
            meta.get("published_date"),
            meta.get("category")
        )

        db.documents.update_one(
            {"_id": doc["_id"]},
            {"$set": {
                "raw_text": content,
                "metadata.article_image_url": article_image,
                "metadata.article_image_source": "opengraph",
                "metadata.status": "completed",
                "metadata.analysis_stage": "level_2_complete",
                "metadata.event_scope": "level_2",
                "metadata.analyzed_at": datetime.utcnow(),
                "metadata.ranking_score": new_ranking,
                "processed": True
            }}
        )


news_fetcher_service = NewsFetcherService()
