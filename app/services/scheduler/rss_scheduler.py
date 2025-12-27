import time
from app.services.fetch.rss_fetcher import fetch_rss_articles
from app.services.fetch.source_selector import select_sources
from app.services.persistence.article_store import ArticleStore
from app.services.fetch.image_enricher import fetch_image_url
from app.models.article import Article
import logging

logger = logging.getLogger(__name__)

MAX_ARTICLES_PER_SOURCE = 10


class RSSScheduler:
    def __init__(self, interval_minutes=5):
        self.interval = interval_minutes * 60
        self.article_store = ArticleStore()

    def run_once(self):
        """
        One polling cycle across all sources.
        Enforces image-ready policy and per-source limits.
        """
        from app.services.fetch.rss_sources import RSS_SOURCES

        for source in RSS_SOURCES:
            try:
                rss_items = fetch_rss_articles(source["feed_url"], source["name"])
                if not rss_items:
                    continue

                stored = 0
                for item in rss_items:
                    if stored >= MAX_ARTICLES_PER_SOURCE:
                        break

                    # 🔹 Image Enrichment (One fast HTTP call)
                    image_url = fetch_image_url(item["original_url"])

                    if not image_url:
                        continue  # ❌ Skip image-less news

                    article = Article(
                        title=item.get("title"),
                        original_url=item.get("original_url"),
                        source=source["name"],
                        published_date=item.get("published_date"),
                        summary=item.get("summary"),
                        language=source["language"][0],
                        country=source["country"],
                        continent=source["continent"],
                        category=source["category"][0],
                        image_url=image_url,
                    )

                    if self.article_store.save_if_new(article):
                        stored += 1
                
                if stored > 0:
                    logger.info(f"💾 Saved {stored} image-ready articles from {source['name']}")
                    
            except Exception as e:
                logger.error(
                    f"❌ Scheduler error for source {source['name']}: {e}"
                )
                continue

    def start(self):
        """
        Blocking loop (run in background thread/process).
        """
        while True:
            self.run_once()
            time.sleep(self.interval)
