# Article Model
from datetime import datetime
from bson import ObjectId


class Article:
    inferred_category: str = "unknown"
    category_confidence: float = 0.0
    inferred_categories: list = []

    def __init__(
        self,
        title,
        original_url,
        source,
        published_date=None,
        summary="",
        language=None,
        country=None,
        continent=None,
        category=None,
        image_url=None,
        inferred_category="unknown",
        category_confidence=0.0,
        inferred_categories=None,
    ):
        self._id = ObjectId()
        self.title = title
        self.original_url = original_url
        self.source = source
        self.published_date = published_date
        self.summary = summary
        self.image_url = image_url

        self.language = language
        self.country = country
        self.continent = continent
        self.category = category
        self.inferred_category = inferred_category
        self.category_confidence = category_confidence
        self.inferred_categories = inferred_categories or []

        self.created_at = datetime.utcnow()
        self.analyzed = False

    def to_dict(self):
        return {
            "_id": self._id,
            "title": self.title,
            "original_url": self.original_url,
            "source": self.source,
            "published_date": self.published_date,
            "summary": self.summary,
            "language": self.language,
            "country": self.country,
            "continent": self.continent,
            "category": self.category,
            "image_url": self.image_url,
            "inferred_category": self.inferred_category,
            "category_confidence": self.category_confidence,
            "inferred_categories": self.inferred_categories,
            "created_at": self.created_at,
            "analyzed": self.analyzed,
        }
