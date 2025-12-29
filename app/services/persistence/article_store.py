# Article Store - Persistence Layer
from datetime import datetime, timedelta
from app.database import get_db
from app.models.article import Article


class ArticleStore:
    def __init__(self):
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            from app.database import get_db
            db = get_db()
            if db is None:
                raise RuntimeError("Database not initialized. Call init_db(app) first.")
            self._collection = db.articles
            
            # Ensure unique index on URL
            self._collection.create_index(
                "original_url",
                unique=True,
                background=True
            )

            # TTL index (optional, 24h cache)
            self._collection.create_index(
                "created_at",
                expireAfterSeconds=86400
            )
        return self._collection

    def save_if_new(self, article: Article):
        """
        Insert article if URL not already present.
        Returns stored document or None if duplicate.
        """
        try:
            result = self.collection.insert_one(article.to_dict())
            return self.collection.find_one({"_id": result.inserted_id})
        except Exception:
            # Duplicate URL
            return None

    def fetch_recent(self, context, limit=50):
        """
        Fetch recent articles matching context.
        """
        query = {
            "language": {"$in": context["language"]},
            "continent": context["continent"]
        }

        if context["country"] != "unknown":
            query["country"] = context["country"]

        return list(
            self.collection
            .find(query)
            .sort("created_at", -1)
            .limit(limit)
        )

    def fetch_recent_by_context(self, context, minutes=30, limit=50):
        """
        Cache-first fetch:
        Return recent articles matching context if within freshness window.
        """
        since = datetime.utcnow() - timedelta(minutes=minutes)

        query = {
            "created_at": {"$gte": since},
            "language": {"$in": context["language"]},
            "continent": context["continent"]
        }

        if context["country"] != "unknown":
            query["country"] = context["country"]

        if context["category"] != "unknown":
            query["category"] = context["category"]

        return list(
            self.collection
            .find(query)
            .sort("created_at", -1)
            .limit(limit)
        )
