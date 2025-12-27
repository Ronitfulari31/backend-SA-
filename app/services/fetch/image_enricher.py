import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (NewsSentimentBot/1.0)"
}

def fetch_image_url(article_url, timeout=6):
    """
    Lightweight resolution of og:image tag from article URL.
    Does NOT perform full parsing or NLP.
    """
    try:
        response = requests.get(
            article_url,
            headers=HEADERS,
            timeout=timeout
        )

        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        tag = soup.find("meta", property="og:image")

        if tag and tag.get("content"):
            return tag["content"].strip()

    except Exception as e:
        logger.debug(f"Image enrichment failed for {article_url}: {e}")
        return None

    return None
