"""
News Routes
Endpoints for real-time data ingestion
"""

import logging
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId

from app.services.news_fetcher import news_fetcher_service
from app.services.fetch.resolver import resolve_context
from app.services.translation import translation_service
from app.utils.language import decide_second_language, translate_analysis_additive, get_or_create_translated_analysis

logger = logging.getLogger(__name__)
news_bp = Blueprint('news', __name__)


# ---------------------------------------------------------
# HELPER: GENERIC MISSING CHECK (UNCHANGED)
# ---------------------------------------------------------

def is_missing(value):
    return value is None or value == "" or value == []


def get_missing_analysis_stages(doc):
    missing = []

    if is_missing(doc.get("raw_text")):
        missing.append("raw_text")

    if is_missing(doc.get("summary")):
        missing.append("summary")

    if is_missing(doc.get("sentiment")):
        missing.append("sentiment")

    if is_missing(doc.get("keywords")):
        missing.append("keywords")

    if is_missing(doc.get("entities")):
        missing.append("entities")

    if is_missing(doc.get("event")):
        missing.append("event")

    if is_missing(doc.get("locations")):
        missing.append("locations")

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
        query = {}  # Querying articles collection directly

        category = request.args.get('category')
        sub_category = request.args.get('sub_category')

        if category:
            query['category'] = category

        if sub_category:
            query['sub_category'] = sub_category

        total = db.articles.count_documents(query)

        cursor = (
            db.articles
            .find(query)
            .sort([('published_date', -1), ('_id', -1)])
            .skip(skip)
            .limit(limit)
        )

        articles = []
        for doc in cursor:
            articles.append({
                'id': str(doc['_id']),
                'title': doc.get('title'),
                'source': doc.get('source'),
                'original_url': doc.get('original_url'),
                'published_date': doc.get('published_date'),
                'summary': doc.get('summary'),
                'category': doc.get('category'),
                'analyzed': doc.get('analyzed', False)
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

        # Map old API to new fetch_news
        context = {
            "category": category.lower(),
            "language": ["en"],
            "country": "unknown",
            "continent": "unknown",
            "scope": "global"
        }

        result = news_fetcher_service.fetch_news_with_context(
            db=db,
            user_id=user_id,
            context=context
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

        doc = db.articles.find_one({"_id": ObjectId(doc_id)})
        if not doc:
            return jsonify({"status": "error", "message": "Article not found"}), 404

        missing_stages = get_missing_analysis_stages(doc)

        if missing_stages or not doc.get("analyzed"):
            logger.info(f"[{doc_id}] Analyzing article...")
            news_fetcher_service.scrape_and_analyze_article(
                db=db,
                doc_id=doc_id,
                stages=missing_stages
            )
            doc = db.articles.find_one({"_id": ObjectId(doc_id)})
        else:
            logger.info(f"[{doc_id}] Analysis already present → returning cached data")

        meta = doc.get("metadata", {})

        published_date = meta.get("published_date")
        published_at = (
            published_date.isoformat()
            if hasattr(published_date, "isoformat")
            else published_date
        )
        response_data = {
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
                "text": doc.get("summary", ""),
                "method": "lsa",
                "sentences": 3
            },
            "analysis": {
                "sentiment": doc.get("sentiment") or {
                    "label": "neutral",
                    "confidence": 0.0,
                    "method": "fallback"
                },
                "event": doc.get("event") or {
                    "type": "other",
                    "confidence": 0.0,
                    "method": "fallback"
                },
                "location": doc.get("locations") if doc.get("locations") and any(doc["locations"].values()) else {
                    "status": "not_detected",
                },
                "keywords": doc.get("keywords", []),
                "entities": doc.get("entities", [])
            }
        }

        # 🔹 Multi-Language Response Architecture (Additive)
        article_lang = doc.get("language")
        second_lang = decide_second_language(article_lang)

        if second_lang:
            try:
                # Use current analysis as source
                analysis_en = response_data["analysis"]
                
                # Use read-through cache
                translated_data = get_or_create_translated_analysis(
                    doc=doc,
                    analysis_en={
                        "summary": response_data["summary"]["text"],
                        **analysis_en
                    },
                    target_lang=second_lang,
                    translator_service=translation_service,
                    collection=db.articles,
                    logger=logger
                )
                
                response_data["analysis_translated"] = {
                    second_lang: translated_data
                }
            except Exception as te:
                logger.error(f"Additive translation failed for {second_lang}: {te}")

        return jsonify(response_data), 200

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


@news_bp.route('/fetch', methods=['GET'])
@jwt_required()
def fetch_news_with_params():
    """
    NEW unified fetching API.
    Uses resolver + param-based fetching.
    Does NOT affect existing APIs.
    """
    try:
        params = request.args.to_dict()
        user_id = get_jwt_identity()
        db = current_app.db

        # 🔹 Resolve context (already correct)
        context = resolve_context(params, db=db)

        # 🔹 Fetch news using new logic (metadata already enriched in fetcher)
        result = news_fetcher_service.fetch_news_with_context(
            db=db,
            user_id=user_id,
            context=context
        )

        return jsonify({
            "status": "success",
            "context": context,
            **result
        }), 200

    except Exception as e:
        logger.exception("Param-based fetch failed")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
