"""
Translation Service
Handles automatic translation of non-English text to English
Tracks translation metadata and performance
"""

import logging
import time
import os
from typing import Dict, Optional

# Environment variables are now set in app/__init__.py for consistency.
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
        self._unsupported_argos_paths = set()
        
        # Persistent Circuit Breakers (per session)
        self._google_circuit_broken = False
        self._last_google_failure = 0
        self._circuit_breaker_cooldown = 300  # 5 minutes

    def _init_argos(self):
        """Lazy-initialize Argos Translate (avoids startup delay)."""
        if self._argos_initialized:
            return True
        try:
            # Re-verify environment (Double-safety for Flask/multithreading)
            D_CACHE_BASE = r"D:\Projects\Backend(SA)_cache"
            argos_cache = os.path.join(D_CACHE_BASE, "argos_cache", "packages")
            if os.environ.get("ARGOS_PACKAGES_DIR") != argos_cache:
                os.environ["ARGOS_PACKAGES_DIR"] = argos_cache
                logger.info(f"[ARGOS] Redundant env fix | setting cache path: {argos_cache}")

            argos_path = os.getenv("ARGOS_PACKAGES_DIR")
            logger.info(f"[ARGOS] Initializing with cache path: {argos_path}")
            
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

    def init_argos(self):
        """
        Force-refreshes Argos Translate package index and lists available languages.
        Ensures a bulletproof initialization at app startup.
        """
        if not self._init_argos():
            return
        try:
            import argostranslate.package
            logger.info("🔄 Refreshing Argos package index...")
            argostranslate.package.update_package_index()
            
            langs = self.argos.get_installed_languages()
            logger.info("[ARGOS] Available languages at startup:")
            for l in langs:
                logger.info(f" - {l.code} ({l.name})")
        except Exception as e:
            logger.error(f"Failed to fully initialize Argos: {e}")

    def log_argos_languages(self):
        """Logs all installed Argos languages for debugging."""
        # Now uses the more robust init_argos logic
        self.init_argos()

    def _resolve_argos_language(self, code: str):
        """
        Robust Argos language resolver.
        Handles cases like:
        hi  -> hi_IN
        zh  -> zh_CN / zh_TW
        id  -> id_ID
        ar  -> ar_SA
        """
        if not code or not self._init_argos():
            return None

        code = code.lower()
        langs = self.argos.get_installed_languages()

        # 1. Exact match (best case)
        for lang in langs:
            if lang.code.lower() == code:
                return lang

        # 2. Prefix match (hi → hi_IN, zh → zh_CN)
        for lang in langs:
            if lang.code.lower().startswith(code):
                return lang

        # 3. Known aliases (extra safety)
        aliases = {
            "hi": ["hi_in", "hin"],
            "zh": ["zh_cn", "zh_tw"],
            "zh-cn": ["zh"],
            "id": ["id_id"],
            "ar": ["ar_sa"],
            "fr": ["fr_fr"],
            "es": ["es_es"],
            "nl": ["nl_nl"],
        }

        for alias in aliases.get(code, []):
            for lang in langs:
                if lang.code.lower() == alias:
                    return lang

        # 4. Aggressive fallback: Language Name match (User requested)
        for lang in langs:
            name_lower = lang.name.lower()
            if code == "hi" and "hindi" in name_lower:
                return lang
            if code == "id" and "indonesian" in name_lower:
                return lang
            if code == "zh" and "chinese" in name_lower:
                return lang
            if code == "ar" and "arabic" in name_lower:
                return lang
            if code == "fr" and "french" in name_lower:
                return lang
            if code == "es" and "spanish" in name_lower:
                return lang

        all_codes = [f"{l.code} ({l.name})" for l in langs]
        logger.error(f"[ARGOS] Unable to resolve language code: {code} | Installed: {all_codes}")
        return None

    def _translate_with_argos(self, text: str, source_lang: str, target_lang: str, silent: bool = False):
        """Performs local translation using Argos with robust resolution."""
        if not self._init_argos():
            return None
            
        path_key = f"{source_lang}->{target_lang}"
        if path_key in self._unsupported_argos_paths:
            return None

        try:
            if not silent:
                logger.info(
                    f"[ARGOS] Attempting translation | source={source_lang} target={target_lang}"
                )

            from_lang = self._resolve_argos_language(source_lang)
            to_lang = self._resolve_argos_language(target_lang)

            if not from_lang or not to_lang:
                if path_key not in self._unsupported_argos_paths:
                    logger.error(
                        f"[ARGOS] Language resolution failed | from={source_lang} to={target_lang}"
                    )
                    self._unsupported_argos_paths.add(path_key)
                return None

            translation = from_lang.get_translation(to_lang)

            if not translation:
                if path_key not in self._unsupported_argos_paths:
                    logger.error(
                        f"[ARGOS] No translation path | from={from_lang.code} to={to_lang.code}"
                    )
                    self._unsupported_argos_paths.add(path_key)
                return None

            return translation.translate(text)

        except Exception as e:
            if not silent:
                logger.exception(f"[ARGOS] Translation exception: {e}")
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
        """Attempts translation ONCE. No retries to ensure zero latency on failure."""
        try:
            result = translator.translate(text)
            if result:
                return result
            return None
        except Exception as e:
            logger.debug(f"Quick Google check failed: {e}")
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
            source_lang = self.normalize_for_translation(source_lang)
            
            # Primary: Google
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            translated = self._translate_with_retry(translator, text)

            # Secondary: Argos Fallback
            if not translated:
                translated = self._translate_with_argos(text, source_lang, target_lang)

            return translated if translated else "[Translation Failed]"
        except Exception as e:
            logger.error(f"Generic translation failed: {e}")
            return "[Translation Failed]"

    def translate_batch(self, texts: list[str], target_lang: str, source_lang: str = "en") -> list[str]:
        """
        Translates a list of strings efficiently.
        Features: Deduplication to minimize API calls and a persistent circuit breaker.
        """
        if not texts:
            return []

        clean_target = self.normalize_for_translation(target_lang)
        source_lang = self.normalize_for_translation(source_lang)
        if source_lang == clean_target:
            return texts

        # 1. Deduplicate strings to minimize network calls
        unique_texts = list(set([t for t in texts if t and isinstance(t, str)]))
        translation_map = {} # Original -> Translated

        # 2. Check global circuit breaker
        current_time = time.time()
        if self._google_circuit_broken and (current_time - self._last_google_failure < self._circuit_breaker_cooldown):
            google_active = False
        else:
            if self._google_circuit_broken:
                logger.info("[GOOGLE] Circuit breaker cooldown ended. Retrying Google...")
                self._google_circuit_broken = False
            google_active = True

        # 3. Process unique strings
        for text in unique_texts:
            translated = None

            # Try Google first
            if google_active:
                try:
                    translator = GoogleTranslator(source=source_lang, target=clean_target)
                    translated = self._translate_with_retry(translator, text)
                    if not translated:
                        logger.warning(f"[GOOGLE] Failure detected for '{text}'. Engaging session circuit breaker.")
                        self._google_circuit_broken = True
                        self._last_google_failure = time.time()
                        google_active = False # Switch to Argos for rest of batch
                except Exception as ge:
                    logger.warning(f"[GOOGLE] Error: {ge}. Engaging session circuit breaker.")
                    self._google_circuit_broken = True
                    self._last_google_failure = time.time()
                    google_active = False

            # Try Argos fallback
            if not translated:
                translated = self._translate_with_argos(text, source_lang, clean_target, silent=True)

            translation_map[text] = translated if translated else "[Translation Failed]"

        # 4. Map back to original order
        return [translation_map.get(t, "[Translation Failed]") for t in texts]

    def translate_to_english(self, text: str, source_language: str = 'auto') -> Dict:
        """
        Translate text to English (with automatic chunking and retries)
        """
        start_time = time.time()
        
        # Don't normalize 'auto' - let Google Translate handle auto-detection
        if source_language != 'auto':
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
            
            # If source is already English (but not auto), skip
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
            
            # Detect actual language if source is 'auto'
            detected_language = source_language
            if source_language == 'auto':
                try:
                    from langdetect import detect
                    detected_language = detect(text[:500])  # Detect from first 500 chars
                    logger.info(f"Auto-detected language: {detected_language}")
                except Exception as e:
                    logger.warning(f"Language detection failed: {e}, using 'auto'")
                    detected_language = 'auto'
            
            translator = GoogleTranslator(source=source_language, target='en')
            
            for idx, chunk in enumerate(chunks):
                # 1. Primary: Google with Retries
                translated = self._translate_with_retry(translator, chunk)
                
                # 2. Secondary: Argos Offline Fallback
                if not translated:
                    self._google_circuit_broken = True
                    self._last_google_failure = time.time()
                    translated = self._translate_with_argos(chunk, detected_language if detected_language != 'auto' else source_language, "en")

                if translated:
                    translated_chunks.append(translated)
                else:
                    # 3. Final Fallback: Mark as failed
                    translated_chunks.append("[Translation Failed]")

            translated_text = " ".join(translated_chunks)
            translation_time = time.time() - start_time
            
            logger.info(f"Translation complete: {detected_language} -> en ({len(chunks)} chunks, {translation_time:.3f}s)")
            
            return {
                'translated_text': translated_text,
                'original_language': detected_language,
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
