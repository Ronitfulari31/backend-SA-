"""
Summarization Service
Generates extractive summaries for documents
"""

import logging
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer

logger = logging.getLogger(__name__)


class SummarizationService:
    def summarize(self, text: str, method: str = "lsa", sentences_count: int = 3) -> str:
        """
        Generate a summary from input text
        """
        try:
            if not text or len(text.split()) < 40:
                logger.info("Text too short for summarization, returning original text")
                return text

            parser = PlaintextParser.from_string(text, Tokenizer("english"))
            summarizer = LsaSummarizer()

            summary_sentences = summarizer(parser.document, sentences_count)
            summary = " ".join(str(sentence) for sentence in summary_sentences)

            return summary.strip()

        except Exception as e:
            logger.exception("Summarization failed")
            return text


# Singleton instance
summarization_service = SummarizationService()
