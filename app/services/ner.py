"""
Named Entity Recognition Service
Extracts entities like PERSON, ORG, GPE, DATE, etc.
"""

import logging
import spacy

logger = logging.getLogger(__name__)


class NERService:
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("✓ spaCy NER model loaded successfully")
        except Exception as e:
            logger.exception("Failed to load spaCy model")
            self.nlp = None

    def extract_entities(self, text: str):
        """
        Extract named entities from text
        """
        if not self.nlp or not text:
            return []

        try:
            doc = self.nlp(text)

            entities = []
            for ent in doc.ents:
                entities.append({
                    "text": ent.text,
                    "label": ent.label_
                })

            return entities

        except Exception as e:
            logger.exception("NER extraction failed")
            return []


# Singleton instance
ner_service = NERService()
