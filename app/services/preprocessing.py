"""
Preprocessing Service
Handles language detection, text cleaning, and duplicate detection
(Language-agnostic & Unicode-safe)
"""

import re
import hashlib
import logging
import unicodedata
from typing import Dict
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)


class PreprocessingService:
    """Service for text preprocessing operations"""

    def __init__(self):
        # STRICT emoji-only pattern (safe for CJK)
        self.emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "]+",
            flags=re.UNICODE
        )

    # ----------------------------------------------------
    # Language detection
    # ----------------------------------------------------

    def detect_language(self, clean_text: str, raw_text: str = "") -> str:
        try:
            # Prefer cleaned text, fallback to raw text if too short
            candidate = clean_text if len(clean_text.strip()) >= 40 else raw_text

            if not candidate or len(candidate.strip()) < 40:
                return "unknown"

            language = detect(candidate)
            logger.info(f"Detected language: {language}")
            return language

        except LangDetectException:
            logger.warning("Language detection failed: No features in text.")
            return "unknown"
        except Exception as e:
            logger.error(f"Unexpected error in language detection: {e}")
            return "unknown"

    # ----------------------------------------------------
    # Cleaning (Unicode-safe)
    # ----------------------------------------------------

    def clean_text(self, text: str) -> str:
        if not text:
            return ""

        # 1️⃣ Unicode normalization (CRITICAL)
        text = unicodedata.normalize("NFKC", text)

        # 2️⃣ Remove URLs
        text = re.sub(r"http[s]?://\S+", "", text)

        # 3️⃣ Remove emojis only (NOT symbols / CJK)
        text = self.emoji_pattern.sub("", text)

        # 4️⃣ Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # 5️⃣ Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()

        logger.debug(f"Text cleaned: {len(text)} characters")
        return text

    # ----------------------------------------------------
    # Normalization (SAFE)
    # ----------------------------------------------------

    def normalize_text(self, text: str) -> str:
        """
        Normalization ONLY for hashing.
        DO NOT lowercase multilingual text.
        """
        if not text:
            return ""

        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    # ----------------------------------------------------
    # Hashing
    # ----------------------------------------------------

    def compute_hash(self, text: str) -> str:
        if not text:
            return ""

        normalized = self.normalize_text(text)
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()

    # ----------------------------------------------------
    # Pipeline entry
    # ----------------------------------------------------

    def preprocess(self, raw_text: str) -> Dict[str, str]:
        try:
            clean_text = self.clean_text(raw_text)

            # Detect language with fallback to raw text
            language = self.detect_language(clean_text, raw_text)

            text_hash = self.compute_hash(clean_text)

            logger.info(
                f"Preprocessing complete - Language: {language}, Hash: {text_hash[:8]}..."
            )

            return {
                "clean_text": clean_text,
                "language": language,
                "text_hash": text_hash
            }

        except Exception as e:
            logger.error(f"Error in preprocessing pipeline: {e}")
            return {
                "clean_text": raw_text,
                "language": "unknown",
                "text_hash": ""
            }


# Singleton instance
preprocessing_service = PreprocessingService()
