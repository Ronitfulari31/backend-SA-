# Article Model
from datetime import datetime
from bson import ObjectId


class Article:
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
            "created_at": self.created_at,
            "analyzed": self.analyzed,
        }
