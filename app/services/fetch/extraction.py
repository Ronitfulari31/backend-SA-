# app/services/fetch/extraction.py
import logging
import requests
import trafilatura
from bs4 import BeautifulSoup
from newspaper import Article, Config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# ARTICLE EXTRACTION
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
# ARTICLE IMAGE EXTRACTION
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
