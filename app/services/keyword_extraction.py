"""
Keyword Extraction Service
Extracts keywords using RAKE
"""

import logging
from rake_nltk import Rake

logger = logging.getLogger(__name__)


class KeywordExtractionService:
    def extract(self, text: str, method: str = "rake", top_n: int = 10):
        """
        Extract keywords from text
        """
        try:
            if not text:
                return []

            rake = Rake()
            rake.extract_keywords_from_text(text)

            ranked_phrases = rake.get_ranked_phrases()
            return ranked_phrases[:top_n]

        except Exception as e:
            logger.exception("Keyword extraction failed")
            return []


# Singleton instance
keyword_extraction_service = KeywordExtractionService()
