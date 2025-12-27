"""
Translation Service
Handles automatic translation of non-English text to English
Tracks translation metadata and performance
"""

import logging
import time
import os
from typing import Dict, Optional

# Redirect Argos storage & temp to D: drive
D_CACHE_BASE = r"D:\Projects\Backend(SA)_cache"
ARGOS_CACHE = os.path.join(D_CACHE_BASE, "argos_cache")
TEMP_DIR = os.path.join(D_CACHE_BASE, "temp")

os.makedirs(ARGOS_CACHE, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

os.environ["ARGOS_PACKAGES_DIR"] = ARGOS_CACHE
os.environ["TEMP"] = TEMP_DIR
os.environ["TMP"] = TEMP_DIR

from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)


SUPPORTED_TRANSLATION_CODES = {
    "af","sq","am","ar","hy","as","ay","az","bm","eu","be","bn","bho","bs","bg",
    "ca","ceb","ny","zh-CN","zh-TW","co","hr","cs","da","dv","doi","nl","en","eo",
    "et","ee","tl","fi","fr","fy","gl","ka","de","el","gn","gu","ht","ha","haw",
    "iw","hi","hmn","hu","is","ig","ilo","id","ga","it","ja","jw","kn","kk","km",
    "rw","gom","ko","kri","ku","ckb","ky","lo","la","lv","ln","lt","lg","lb","mk",
    "mai","mg","ms","ml","mt","mi","mr","mni-Mtei","lus","mn","my","ne","no","or",
    "om","ps","fa","pl","pt","pa","qu","ro","ru","sm","sa","gd","nso","sr","st",
    "sn","sd","si","sk","sl","so","es","su","sw","sv","tg","ta","tt","te","th",
    "ti","ts","tr","tk","ak","uk","ur","ug","uz","vi","cy","xh","yi","yo","zu"
}

LANGUAGE_CODE_MAP = {
    # Chinese (translator requires explicit variant)
    "zh": "zh-CN",
    "zh-cn": "zh-CN",
    "zh-tw": "zh-TW",

    # Hebrew legacy
    "he": "iw",

    # Indonesian legacy
    "in": "id",

    # Filipino naming mismatch
    "fil": "tl",

    # Norwegian variants
    "nb": "no",
    "nn": "no",

    # Kurdish variants
    "kur": "ku",

    # Serbian variants
    "sr-latn": "sr",

    # Portuguese variants
    "pt-br": "pt",
    "pt-pt": "pt",
}


class TranslationService:
    """Service for text translation operations"""
    
    def __init__(self):
        self.translator = GoogleTranslator()
        self.translation_engine = "google"
        self._argos_initialized = False

    def _init_argos(self):
        """Lazy-initialize Argos Translate (avoids startup delay)."""
        if self._argos_initialized:
            return True
        try:
            import argostranslate.package
            import argostranslate.translate
            self.argos = argostranslate.translate
            self._argos_initialized = True
            logger.info("✓ Argos Translate initialized (Offline Fallback)")
            return True
        except ImportError:
            logger.warning("Argos Translate not installed — offline fallback disabled.")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Argos Translate: {e}")
            return False

    def _translate_with_argos(self, text, src_lang, dest_lang="en"):
        """Performs local translation using Argos."""
        if not self._init_argos():
            return None
        try:
            # Note: Argos normally requires downloading language packages first.
            # This is a basic integration; in production, you'd ensure models are pre-loaded.
            return self.argos.translate(text, src_lang, dest_lang)
        except Exception as e:
            logger.error(f"Argos translation failed: {e}")
            return None
    
    def normalize_for_translation(self, lang: str) -> str:
        """
        Converts stored language codes (zh, mr, es, etc.)
        into translation-engine-compatible codes.
        """
        if not lang or lang == "unknown":
            return "en"

        lang = lang.lower()

        # Step 1: explicit remap if needed
        mapped = LANGUAGE_CODE_MAP.get(lang, lang)

        # Step 2: if translator supports it -> done
        if mapped in SUPPORTED_TRANSLATION_CODES:
            return mapped

        # Step 3: try base language (e.g. zh-hans -> zh)
        base = mapped.split("-")[0]
        if base in SUPPORTED_TRANSLATION_CODES:
            return base

        # Step 4: last-resort safe fallback
        return "en"

    def _chunk_text(self, text: str, max_len: int = 4000) -> list[str]:
        """Splits text into chunks of max_len characters."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + max_len
            chunks.append(text[start:end])
            start = end
        return chunks

    def _translate_with_retry(self, translator, text):
        """Attempts translation with exponential backoff (max 3 retries)."""
        delay = 0.5
        for attempt in range(1, 4):
            try:
                result = translator.translate(text)
                if result:
                    return result
                # If result is empty string/None but no exception, might still be a failure
                if attempt == 3:
                    return None
            except Exception as e:
                if attempt == 3:
                    logger.error(f"Translation failed after {attempt} attempts: {e}")
                    return None
                logger.warning(f"Translation attempt {attempt} failed, retrying in {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, 4.0)
        return None

    def translate_text(self, text: str, target_lang: str, source_lang: str = "en") -> str:
        """
        Generic translation method for any source/target pair.
        Used primarily for additive translation of English analysis to source language.
        """
        if not text or source_lang == target_lang:
            return text

        try:
            # Normalize target language
            target_lang = self.normalize_for_translation(target_lang)
            
            # Primary: Google
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            translated = self._translate_with_retry(translator, text)

            # Secondary: Argos Fallback
            if not translated:
                logger.warning(f"Google failed for {source_lang} -> {target_lang} → Falling back to Argos")
                translated = self._translate_with_argos(text, source_lang, target_lang)

            return translated if translated else text
        except Exception as e:
            logger.error(f"Generic translation failed: {e}")
            return text

    def translate_to_english(self, text: str, source_language: str = 'auto') -> Dict:
        """
        Translate text to English (with automatic chunking and retries)
        """
        start_time = time.time()
        
        # Normalize source language for engine compatibility
        source_language = self.normalize_for_translation(source_language)
        
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
            
            # Chunking logic for long articles (limit: 5000, we use 4000 for safety)
            chunks = self._chunk_text(text, max_len=4000)
            translated_chunks = []
            
            translator = GoogleTranslator(source=source_language, target='en')
            
            for idx, chunk in enumerate(chunks):
                # 1. Primary: Google with Retries
                translated = self._translate_with_retry(translator, chunk)
                
                # 2. Secondary: Argos Offline Fallback
                if not translated:
                    logger.warning(f"Google failed for chunk {idx+1}/{len(chunks)} → Falling back to Argos")
                    translated = self._translate_with_argos(chunk, source_language, "en")

                if translated:
                    translated_chunks.append(translated)
                else:
                    # 3. Final Fallback: Original Text
                    logger.warning(f"All translation methods failed for chunk {idx+1}/{len(chunks)} → preserving original")
                    translated_chunks.append(chunk)

            translated_text = " ".join(translated_chunks)
            translation_time = time.time() - start_time
            
            logger.info(f"Translation complete: {source_language} -> en ({len(chunks)} chunks, {translation_time:.3f}s)")
            
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
