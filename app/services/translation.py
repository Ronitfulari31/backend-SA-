"""
Translation Service
Handles automatic translation of non-English text to English
Tracks translation metadata and performance
"""

import logging
import time
from typing import Dict, Optional
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)


class TranslationService:
    """Service for text translation operations"""
    
    def __init__(self):
        self.translator = GoogleTranslator()
        self.translation_engine = "google"
    
    def translate_to_english(self, text: str, source_language: str = 'auto') -> Dict:
        """
        Translate text to English
        
        Args:
            text: Text to translate
            source_language: Source language code (default: 'auto' for auto-detection)
            
        Returns:
            Dictionary with:
                - translated_text: Translated text
                - original_language: Detected/specified source language
                - translation_engine: Engine used
                - translation_time: Time taken in seconds
                - success: Whether translation succeeded
        """
        start_time = time.time()
        
        try:
            # If text is already in English or very short, skip translation
            if not text or len(text.strip()) == 0:
                return {
                    'translated_text': text,
                    'original_language': source_language,
                    'translation_engine': self.translation_engine,
                    'translation_time': 0.0,
                    'success': True,
                    'skipped': True
                }
            
            # If source is already English, skip
            if source_language == 'en':
                logger.info("Text already in English, skipping translation")
                return {
                    'translated_text': text,
                    'original_language': 'en',
                    'translation_engine': self.translation_engine,
                    'translation_time': 0.0,
                    'success': True,
                    'skipped': True
                }
            
            # Perform translation
            translator = GoogleTranslator(source=source_language, target='en')
            translated_text = translator.translate(text)
            
            translation_time = time.time() - start_time
            
            logger.info(f"Translation complete: {source_language} -> en ({translation_time:.3f}s)")
            
            return {
                'translated_text': translated_text,
                'original_language': source_language,
                'translation_engine': self.translation_engine,
                'translation_time': round(translation_time, 3),
                'success': True,
                'skipped': False
            }
            
        except Exception as e:
            translation_time = time.time() - start_time
            logger.error(f"Translation failed: {e}")
            
            # Return original text if translation fails
            return {
                'translated_text': text,
                'original_language': source_language,
                'translation_engine': self.translation_engine,
                'translation_time': round(translation_time, 3),
                'success': False,
                'error': str(e),
                'skipped': False
            }
    
    def translate_multiple(self, texts: list, source_language: str = 'auto') -> list:
        """
        Translate multiple texts
        
        Args:
            texts: List of texts to translate
            source_language: Source language code
            
        Returns:
            List of translation result dictionaries
        """
        results = []
        
        for text in texts:
            result = self.translate_to_english(text, source_language)
            results.append(result)
        
        return results
    
    def get_supported_languages(self) -> Dict[str, str]:
        """
        Get list of supported languages
        
        Returns:
            Dictionary of language codes and names
        """
        # Common languages for disaster response
        return {
            'en': 'English',
            'hi': 'Hindi',
            'es': 'Spanish',
            'fr': 'French',
            'ar': 'Arabic',
            'zh-CN': 'Chinese (Simplified)',
            'ja': 'Japanese',
            'ko': 'Korean',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'de': 'German',
            'it': 'Italian',
            'tr': 'Turkish',
            'vi': 'Vietnamese',
            'id': 'Indonesian',
            'th': 'Thai',
            'pl': 'Polish',
            'nl': 'Dutch',
            'bn': 'Bengali',
            'ur': 'Urdu',
            'ta': 'Tamil',
            'te': 'Telugu',
            'mr': 'Marathi'
        }


# Singleton instance
translation_service = TranslationService()
