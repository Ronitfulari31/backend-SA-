"""
Preprocessing Service
Handles language detection, text cleaning, and duplicate detection
"""

import re
import hashlib
import logging
from typing import Dict, Tuple
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)


class PreprocessingService:
    """Service for text preprocessing operations"""
    
    def __init__(self):
        # Emoji pattern
        self.emoji_pattern = re.compile(
            "["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of the text
        
        Args:
            text: Input text
            
        Returns:
            ISO language code (e.g., 'en', 'hi', 'es')
        """
        try:
            if not text or len(text.strip()) == 0:
                return 'unknown'
            
            # langdetect works better with longer text
            language = detect(text)
            logger.info(f"Detected language: {language}")
            return language
            
        except LangDetectException as e:
            logger.warning(f"Language detection failed: {e}")
            return 'unknown'
        except Exception as e:
            logger.error(f"Unexpected error in language detection: {e}")
            return 'unknown'
    
    def clean_text(self, text: str) -> str:
        """
        Clean text by removing URLs, emojis, and special characters
        
        Args:
            text: Raw input text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove emojis
        text = self.emoji_pattern.sub(r'', text)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        logger.debug(f"Text cleaned: {len(text)} characters")
        return text
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text (lowercase, remove extra spaces)
        
        Args:
            text: Input text
            
        Returns:
            Normalized text
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def compute_hash(self, text: str) -> str:
        """
        Compute hash for duplicate detection
        
        Args:
            text: Input text
            
        Returns:
            MD5 hash of the text
        """
        if not text:
            return ""
        
        # Normalize before hashing for better duplicate detection
        normalized = self.normalize_text(text)
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def preprocess(self, raw_text: str) -> Dict[str, str]:
        """
        Full preprocessing pipeline
        
        Args:
            raw_text: Raw input text
            
        Returns:
            Dictionary with:
                - clean_text: Cleaned text
                - language: Detected language code
                - text_hash: Hash for duplicate detection
        """
        try:
            # Clean the text
            clean_text = self.clean_text(raw_text)
            
            # Detect language on cleaned text
            language = self.detect_language(clean_text)
            
            # Compute hash for duplicate detection
            text_hash = self.compute_hash(clean_text)
            
            logger.info(f"Preprocessing complete - Language: {language}, Hash: {text_hash[:8]}...")
            
            return {
                'clean_text': clean_text,
                'language': language,
                'text_hash': text_hash
            }
            
        except Exception as e:
            logger.error(f"Error in preprocessing pipeline: {e}")
            return {
                'clean_text': raw_text,
                'language': 'unknown',
                'text_hash': ''
            }


# Singleton instance
preprocessing_service = PreprocessingService()
