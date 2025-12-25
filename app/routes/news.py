"""
News Routes
Endpoints for real-time data ingestion
"""

import logging
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId

from app.services.news_fetcher import news_fetcher_service

logger = logging.getLogger(__name__)
news_bp = Blueprint('news', __name__)


# ---------------------------------------------------------
# HELPER: GENERIC MISSING CHECK (UNCHANGED)
# ---------------------------------------------------------

def is_missing(value):
    if value is None:
        return True

    if isinstance(value, str):
        stripped = value.strip().lower()
        if stripped in ("", "null", "none"):
            return True
        # 🔴 critical: too short for NLP (REMOVED: Now allowing headlines)
        # if len(stripped) < 40:
        #     return True
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
# HELPER: DETECT MISSING PIPELINE STAGES (MERGED, ADDITIVE)
# ---------------------------------------------------------

def get_missing_analysis_stages(doc):
    missing = []

    cleaned_text = doc.get("cleaned_text")
    language = doc.get("language")

    # Preprocessing
    if is_missing(cleaned_text):
        missing.append("preprocessing")

    # Translation (ONLY if non-English)
    if language and language not in ("en", "unknown"):
        if is_missing(doc.get("translated_text")):
            missing.append("translation")

    # Sentiment
    if is_missing(doc.get("sentiment")):
        missing.append("sentiment")

    # Event
    if (
        is_missing(doc.get("event_type")) or
        is_missing(doc.get("event_confidence"))
    ):
        missing.append("event")

    # Location
    if is_missing(doc.get("location")):
        missing.append("location")

    # Summary
    summary = doc.get("summary", {})
    if is_missing(summary) or is_missing(summary.get("text")):
        missing.append("summary")

    # Keywords
    if is_missing(doc.get("keywords")):
        missing.append("keywords")

    # Entities
    if is_missing(doc.get("entities")):
        missing.append("entities")

    # -------------------------------------------------
    # ✅ DEPENDENCY ENFORCEMENT (ADDED – NO REMOVALS)
    # -------------------------------------------------
    # If text changes, semantic stages must re-run
    if "preprocessing" in missing or "translation" in missing:
        for stage in ("sentiment", "event", "summary", "keywords", "entities"):
            if stage not in missing:
                missing.append(stage)

    return missing


# ---------------------------------------------------------
# LIST STORED NEWS (LEVEL-1 FEED) — UNCHANGED
# ---------------------------------------------------------

@news_bp.route('/list-new-news', methods=['GET'])
@jwt_required()
def list_news():
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        skip = (page - 1) * limit

        db = current_app.db
        query = {'source': 'news'}

        category = request.args.get('category')
        sub_category = request.args.get('sub_category')

        if category:
            query['metadata.category'] = category

        if sub_category:
            query['metadata.sub_category'] = sub_category

        total = db.documents.count_documents(query)

        cursor = (
            db.documents
            .find(query)
            .sort([('metadata.published_date', -1), ('_id', -1)])
            .skip(skip)
            .limit(limit)
        )

        articles = []
        for doc in cursor:
            meta = doc.get('metadata', {})
            articles.append({
                'id': str(doc['_id']),
                'title': meta.get('title'),
                'source': meta.get('publisher'),
                'original_url': meta.get('original_url'),
                'resolved_url': meta.get('resolved_url'),
                'thumbnail_image_url': meta.get('thumbnail_image_url'),
                'category': meta.get('category'),
                'sub_category': meta.get('sub_category'),
                'analysis_stage': meta.get('analysis_stage', 'level_1_only'),
                'status': meta.get('status', 'ingested')
            })

        return jsonify({
            'status': 'success',
            'data': {
                'articles': articles,
                'pagination': {
                    'total': total,
                    'page': page,
                    'limit': limit,
                    'pages': (total + limit - 1) // limit
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"News list error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ---------------------------------------------------------
# CATEGORY-BASED FETCH (LEVEL-1) 
# ---------------------------------------------------------

@news_bp.route('/fetch-category', methods=['GET'])
@jwt_required()
def fetch_category_news():
    try:
        category = request.args.get('category')
        if not category:
            return jsonify({
                'status': 'error',
                'message': 'category query parameter is required'
            }), 400

        user_id = get_jwt_identity()
        db = current_app.db

        result = news_fetcher_service.fetch_category_news(
            db=db,
            user_id=user_id,
            category=category.lower()
        )

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Category fetch error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch category news: {str(e)}'
        }), 500


# ---------------------------------------------------------
# ANALYZE (LEVEL-2, REPAIRABLE) — UNCHANGED FLOW
# ---------------------------------------------------------

@news_bp.route('/analyze/<doc_id>', methods=['GET'])
@jwt_required()
def analyze_news_item(doc_id):
    try:
        db = current_app.db

        doc = db.documents.find_one({"_id": ObjectId(doc_id)})
        if not doc:
            return jsonify({"status": "error", "message": "Document not found"}), 404

        missing_stages = get_missing_analysis_stages(doc)

        if missing_stages:
            logger.info(f"[{doc_id}] Missing stages → {missing_stages}")
            news_fetcher_service.scrape_and_analyze_article(
                db=db,
                doc_id=doc_id,
                stages=missing_stages
            )
            doc = db.documents.find_one({"_id": ObjectId(doc_id)})
        else:
            logger.info(f"[{doc_id}] Analysis already present → returning cached data")

        meta = doc.get("metadata", {})

        published_date = meta.get("published_date")
        published_at = (
            published_date.isoformat()
            if hasattr(published_date, "isoformat")
            else published_date
        )

        return jsonify({
            "status": "success",
            "document_id": str(doc["_id"]),
            "article": {
                "title": meta.get("title", "Untitled"),
                "original_url": meta.get("original_url", ""),
                "source": meta.get("publisher", ""),
                "published_at": published_at,
                "language": doc.get("language", "unknown")
            },
            "content": {
                "raw": doc.get("raw_text", ""),
                "cleaned": doc.get("cleaned_text", "")
            },
            "summary": {
                "text": doc.get("summary", {}).get("text", ""),
                "method": doc.get("summary", {}).get("method", ""),
                "sentences": doc.get("summary", {}).get("sentences", 0)
            },
            "analysis": {
                "sentiment": doc.get("sentiment") or {
                    "label": "neutral",
                    "confidence": 0.0,
                    "method": "fallback"
                },
                "event": {
                    "type": doc.get("event_type", "other"),
                    "confidence": doc.get("event_confidence", 0.0),
                    "guarded": doc.get("event_guarded", False)
                },
                "location": doc.get("location"),
                "keywords": doc.get("keywords", []),
                "entities": doc.get("entities", [])
            }
        }), 200

    except Exception as e:
        logger.exception("Level-2 analysis failed")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------
# FULL VIEW (LEVEL-2) — UNCHANGED
# ---------------------------------------------------------

@news_bp.route('/<doc_id>/full-view', methods=['GET'])
@jwt_required()
def get_news_full_view(doc_id):
    try:
        db = current_app.db

        doc = db.documents.find_one({'_id': ObjectId(doc_id)})
        if not doc:
            return jsonify({'status': 'error', 'message': 'Not found'}), 404

        meta = doc.get('metadata', {})

        return jsonify({
            'status': 'success',
            'data': {
                'article': {
                    'id': str(doc['_id']),
                    'title': meta.get('title'),
                    'content': doc.get('raw_text'),
                    'source': meta.get('publisher'),
                    'resolved_url': meta.get('resolved_url'),
                    'thumbnail_image_url': meta.get('thumbnail_image_url'),
                    'article_image_url': meta.get('article_image_url')
                },
                'analysis': {
                    'sentiment': doc.get('sentiment') or {
                        'label': 'neutral',
                        'confidence': 0.0,
                        'method': 'fallback'
                    },
                    'location': doc.get('location'),
                    'event_type': doc.get('event_type')
                },
                'reactions': []
            }
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
