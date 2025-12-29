"""
News Fetcher
------------
Fetches news metadata from the pre-populated 'articles' collection.
Ingestion is handled by the background RSSScheduler.
"""

from app.services.persistence.article_store import ArticleStore
from app.services.fetch.extraction import extract_article_package
from app.services.pipeline import process_document_pipeline
from app.services.pagination.cursor_pagination import CursorPagination
from app.services.ranking.article_ranker import ArticleRanker
from datetime import datetime, timedelta
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

# Initialize services
article_store = ArticleStore()
paginator = CursorPagination(
    sort_fields=[("created_at", -1), ("_id", -1)],
    max_limit=50
)
ranker = ArticleRanker()


def build_discovery_tiers(context: dict, query_language=None):
    """
    Build ordered MongoDB query tiers based on resolved context.
    Highest priority tier comes first.
    
    Args:
        context: Resolved context dict
        query_language: Language list to use for filtering (only if user-provided)
    """
    # Debug logging
    logger.info(f"[build_discovery_tiers] query_language={query_language}")

    tiers = []

    city = context.get("city", "unknown")
    state = context.get("state", "unknown")
    country = context.get("country", "unknown")
    continent = context.get("continent", "unknown")
    category = context.get("category", "unknown")
    source = context.get("source", "unknown")
    analyzed = context.get("analyzed", "false")

    def base():
        q = {}
        # Only filter by language if explicitly provided by user
        if query_language:
            q["language"] = {"$in": query_language}
            logger.info(f"[build_discovery_tiers] Adding language filter: {query_language}")
        else:
            logger.info(f"[build_discovery_tiers] No language filter (query_language is None)")
        
        # Add source filter if provided
        if source != "unknown":
            q["source"] = source
            logger.info(f"[build_discovery_tiers] Adding source filter: {source}")
        
        # Add analyzed filter if requested
        # Handle both string "true" and boolean True
        if analyzed in ["true", True, "True", "1"]:
            q["analyzed"] = True
            logger.info(f"[build_discovery_tiers] Adding analyzed filter: True (input was: {analyzed})")
        else:
            logger.info(f"[build_discovery_tiers] NOT adding analyzed filter (input was: {analyzed})")
        
        # Add category filter
        if category != "unknown":
            q["$or"] = [
                {"category": category},              # source category
                {"inferred_category": category}      # ML inferred category
            ]
        return q

    # 1. City Tier
    if city != "unknown":
        tiers.append({**base(), "city": city})

    # 2. State Tier
    if state != "unknown":
        tiers.append({**base(), "state": state})

    # 3. Country Tier
    if country != "unknown":
        tiers.append({**base(), "country": country})

    # 4. Continent Tier
    if continent != "unknown":
        tiers.append({**base(), "continent": continent})

    # 5. Global Tier (Always fallback to global to ensure we don't hide any articles)
    tiers.append(base())

    return tiers


def _format_article(doc):
    """
    Standardize article output for UI.
    Serves AI summary if analyzed, otherwise the original RSS snippet.
    """
    analyzed = doc.get("analyzed", False)
    return {
        "_id": str(doc["_id"]),
        "title": doc.get("title"),
        "summary": doc.get("summary") if analyzed else doc.get("rss_summary"),
        "original_url": doc.get("original_url"),
        "image_url": doc.get("image_url"),
        "source": doc.get("source"),
        "category": doc.get("category"),
        "published_date": doc.get("published_date"),
        "analyzed": analyzed
    }


def fetch_news(context: dict, query_language=None):
    """
    Main fetch entry point used by /api/news/fetch
    Implements Tiered Discovery + Cursor Pagination.
    """
    # 1. Read pagination params
    limit = paginator.clamp_limit(context.get("limit"))
    cursor = context.get("cursor")
    cursor_filter = paginator.build_cursor_filter(cursor)
    
    results = []
    seen_ids = set()
    tiers = build_discovery_tiers(context, query_language=query_language)
    
    # Generate tier level names dynamically to match actual tiers
    tier_levels = []
    city = context.get("city", "unknown")
    state = context.get("state", "unknown")
    country = context.get("country", "unknown")
    continent = context.get("continent", "unknown")
    
    if city != "unknown":
        tier_levels.append("city")
    if state != "unknown":
        tier_levels.append("state")
    if country != "unknown":
        tier_levels.append("country")
    if continent != "unknown":
        tier_levels.append("continent")
    
    # Global tier is already added in build_discovery_tiers in the new logic
    # but we need to ensure the tier_levels matches the tiers list.
    # Actually, build_discovery_tiers now always adds 'global' at the end.
    # Let's ensure tier_levels length matches tiers length.
    while len(tier_levels) < len(tiers):
        tier_levels.append("global")
    
    # We collect more than limit to allow for cross-tier filling, 
    # but we'll trim to 'limit' at the end.
    MAX_COLLECTION = 200 

    for tier_level, tier_query in zip(tier_levels, tiers):
        if len(results) >= MAX_COLLECTION:
            break

        # Apply Cursor Filter
        match_stage = tier_query.copy()
        if cursor_filter:
            match_stage = {
                "$and": [match_stage, cursor_filter]
            }

        # Simplified Pipeline: Just match, sort, and limit. 
        # (Grouping by source was too restrictive for a complete feed)
        pipeline = [
            { "$match": match_stage },
            { "$sort": { "created_at": -1, "_id": -1 } },
            { "$limit": MAX_COLLECTION }
        ]

        # Execute aggregation
        batch = list(article_store.collection.aggregate(pipeline))

        for article in batch:
            aid = str(article["_id"])
            if aid not in seen_ids:
                # Rank scoring
                article["_rank_score"] = ranker.score(
                    article=article,
                    context=context,
                    tier_level=tier_level
                )
                results.append(article)
                seen_ids.add(aid)

            if len(results) >= MAX_COLLECTION:
                break

    # 2. Final Sorting (Rank first, then recency)
    results.sort(
        key=lambda a: (
            a.get("_rank_score", 0), 
            a.get("created_at").timestamp() if a.get("created_at") and hasattr(a.get("created_at"), "timestamp") else 0,
            str(a.get("_id"))
        ),
        reverse=True
    )

    # 3. Trim results + build next cursor
    has_more = len(results) > limit
    results = results[:limit]
    
    next_cursor = None
    if results and has_more:
        next_cursor = paginator.encode_cursor(results[-1])

    # 4. Final response
    if not results:
        # Get base query for total even if no results
        memo_tiers = build_discovery_tiers(context, query_language=query_language)
        base_query = memo_tiers[-1] if memo_tiers else {}
        total_matching = article_store.collection.count_documents(base_query)

        return {
            "status": "success",
            "count": 0,
            "total": total_matching,
            "articles": [],
            "message": "No articles found matching your filters.",
            "context": context,
            "empty": True
        }

    formatted_articles = [_format_article(a) for a in results]

    # Calculate accurate total matching documents (using the base global query)
    memo_tiers = build_discovery_tiers(context, query_language=query_language)
    base_query = memo_tiers[-1] if memo_tiers else {}
    total_matching = article_store.collection.count_documents(base_query)

    return {
        "status": "success",
        "count": len(results),
        "total": total_matching,
        "articles": formatted_articles,
        "next_cursor": next_cursor,
        "has_more": has_more,
        "context": context,
        "cache_hit": True
    }


def scrape_and_analyze_article(db, article_id, stages=None):
    """
    Flow 3: User clicks "Analyze"
    Fetches full content on-demand and runs the NLP pipeline.
    """
    article_data = db.articles.find_one({"_id": ObjectId(article_id)})
    if not article_data:
        logger.error(f"Article {article_id} not found for analysis")
        return None

    # 1. Fetch full content
    url = article_data.get("original_url")
    extraction, resolved_url = extract_article_package(url)
    
    if not extraction.get("success") or not extraction.get("content") or len(extraction["content"].strip()) < 200:
        raise ValueError(f"Article extraction failed or too short for doc_id={article_id}")

    content = extraction["content"]

    # 2. Run NLP Pipeline
    # We update raw_text first
    db.articles.update_one(
        {"_id": ObjectId(article_id)},
        {"$set": {"raw_text": content}}
    )

    # Re-using the collection-agnostic pipeline
    process_document_pipeline(
        db=db,
        doc_id=article_id,
        raw_text=content,
        stages=stages,
        collection="articles"
    )

    # 3. Mark as analyzed
    db.articles.update_one(
        {"_id": ObjectId(article_id)},
        {"$set": {
            "analyzed": True,
            "metadata.status": "completed",
            "metadata.analysis_stage": "level_2_complete",
            "metadata.analyzed_at": datetime.utcnow()
        }}
    )
    
    return db.articles.find_one({"_id": ObjectId(article_id)})


# For backward compatibility with routes/news.py
class NewsFetcherService:
    def fetch_news_with_context(self, db, user_id, context, query_language=None):
        return fetch_news(context, query_language=query_language)
    
    def scrape_and_analyze_article(self, db, doc_id, stages=None):
        return scrape_and_analyze_article(db, doc_id, stages)

news_fetcher_service = NewsFetcherService()
