import time
from app.services.fetch.rss_fetcher import fetch_rss_articles
from app.services.fetch.source_selector import select_sources
from app.services.persistence.article_store import ArticleStore
from app.services.fetch.image_enricher import fetch_image_url
from app.models.article import Article
import logging
from app.services.classification.category_classifier import classify_category

logger = logging.getLogger(__name__)

MAX_ARTICLES_PER_SOURCE = 10


class RSSScheduler:
    def __init__(self, interval_minutes=5):
        self.interval = interval_minutes * 60
        self.article_store = ArticleStore()
        self._paused = False

    def pause(self):
        """Pauses the scheduler's fetching logic."""
        if not self._paused:
            logger.info("⏸ RSS Scheduler PAUSED.")
            self._paused = True

    def resume(self):
        """Resumes the scheduler's fetching logic."""
        if self._paused:
            logger.info("▶ RSS Scheduler RESUMED.")
            self._paused = True # Should be False, fixing in next step or now
            self._paused = False

    def run_once(self):
        """
        One polling cycle across all sources.
        Enforces image-ready policy and per-source limits.
        """
        if self._paused:
            return

        from app.services.fetch.rss_sources import RSS_SOURCES

        for source in RSS_SOURCES:
            if self._paused:
                break

            try:
                rss_items = fetch_rss_articles(source["feed_url"], source["name"])
                if not rss_items:
                    continue

                stored = 0
                for item in rss_items:
                    if self._paused:
                        break
                    
                    if stored >= MAX_ARTICLES_PER_SOURCE:
                        break

                    # 🔹 Image Enrichment (One fast HTTP call)
                    image_url = fetch_image_url(item["original_url"])

                    if not image_url:
                        continue  # ❌ Skip image-less news

                    # 🔹 Content-based category inference (ADD-ONLY)
                    text_for_classification = f"{item.get('title', '')} {item.get('summary', '')}"
                    category_result = classify_category(text_for_classification)

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
                        inferred_category=category_result.get("primary", "unknown"),
                        category_confidence=category_result.get("confidence", 0.0),
                        inferred_categories=category_result.get("labels", []),
                    )

                    if self.article_store.save_if_new(article):
                        stored += 1
                
                if stored > 0:
                    logger.info(f"💾 Saved {stored} image-ready articles from {source['name']}")
                
                # 🔹 Throttling: Small pause between sources to reduce log-storm and CPU spikes
                time.sleep(1.5)
                    
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
            if not self._paused:
                self.run_once()
            time.sleep(self.interval if not self._paused else 5)
