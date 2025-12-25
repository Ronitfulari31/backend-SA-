"""
Sentiment Analysis Service
Supports BERTweet (social media focused) with lazy loading
Falls back to VADER and TextBlob
Handles multilingual sentiment analysis safely
"""

import logging
import time
from typing import Dict
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)


class SentimentService:
    """Service for sentiment analysis operations"""

    def __init__(self):
        self.vader_analyzer = SentimentIntensityAnalyzer()

        # BERTweet (lazy-loaded)
        self.bertweet_model = None
        self.bertweet_tokenizer = None
        self.bertweet_available = False
        self._bertweet_attempted = False

    # ---------------------------------------------------------
    # Lazy BERTweet Loader
    # ---------------------------------------------------------
    def _load_bertweet(self):
        if self._bertweet_attempted:
            return

        self._bertweet_attempted = True

        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            logger.info("🔄 Loading BERTweet model...")

            model_name = "finiteautomata/bertweet-base-sentiment-analysis"

            self.bertweet_tokenizer = AutoTokenizer.from_pretrained(
                model_name, use_fast=False
            )
            self.bertweet_model = AutoModelForSequenceClassification.from_pretrained(
                model_name
            )
            self.bertweet_model.eval()
            self.bertweet_available = True

            logger.info("✅ BERTweet model loaded successfully")

        except Exception as e:
            logger.warning(f"⚠️ BERTweet unavailable, falling back: {e}")
            self.bertweet_available = False

    # ---------------------------------------------------------
    # Sentiment Engines
    # ---------------------------------------------------------
    def analyze_with_bertweet(self, text: str) -> Dict | None:
        try:
            import torch

            self._load_bertweet()
            if not self.bertweet_available:
                return None

            inputs = self.bertweet_tokenizer(
                text, return_tensors="pt", truncation=True, max_length=128
            )

            with torch.no_grad():
                outputs = self.bertweet_model(**inputs)
                probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

            idx = torch.argmax(probs, dim=1).item()
            confidence = probs[0][idx].item()

            sentiment_map = {0: "negative", 1: "neutral", 2: "positive"}

            return {
                "sentiment": sentiment_map[idx],
                "confidence": round(confidence, 3),
                "method": "bertweet",
                "scores": {
                    "negative": round(probs[0][0].item(), 3),
                    "neutral": round(probs[0][1].item(), 3),
                    "positive": round(probs[0][2].item(), 3),
                },
            }

        except Exception as e:
            logger.error(f"BERTweet failed: {e}")
            return None

    def analyze_with_vader(self, text: str) -> Dict | None:
        try:
            scores = self.vader_analyzer.polarity_scores(text)
            compound = scores["compound"]

            if compound >= 0.05:
                sentiment = "positive"
            elif compound <= -0.05:
                sentiment = "negative"
            else:
                sentiment = "neutral"

            return {
                "sentiment": sentiment,
                "confidence": round(abs(compound), 3),
                "method": "vader",
                "scores": scores,
            }

        except Exception as e:
            logger.error(f"VADER failed: {e}")
            return None

    def analyze_with_textblob(self, text: str) -> Dict | None:
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity

            if polarity > 0.1:
                sentiment = "positive"
            elif polarity < -0.1:
                sentiment = "negative"
            else:
                sentiment = "neutral"

            return {
                "sentiment": sentiment,
                "confidence": round(abs(polarity), 3),
                "method": "textblob",
                "scores": {
                    "polarity": round(polarity, 3),
                    "subjectivity": round(blob.sentiment.subjectivity, 3),
                },
            }

        except Exception as e:
            logger.error(f"TextBlob failed: {e}")
            return None

    # ---------------------------------------------------------
    # Unified API (cleaned → summary → raw)
    # ---------------------------------------------------------
    def analyze(
        self,
        cleaned_text: str | None = None,
        summary_text: str | None = None,
        raw_text: str | None = None,
        method: str = "auto",
    ) -> Dict:

        start_time = time.time()

        text = None
        source = None

        if cleaned_text and cleaned_text.strip():
            text = cleaned_text
            source = "cleaned"
        elif summary_text and summary_text.strip():
            text = summary_text
            source = "summary"
        elif raw_text and raw_text.strip():
            text = raw_text
            source = "raw"

        logger.info(f"Sentiment input source={source}, length={len(text) if text else 0}")

        if not text:
            return {
                "sentiment": "neutral",
                "confidence": 0.0,
                "method": "skipped_no_text",
                "scores": {},
                "analysis_time": 0.0,
            }

        result = None

        if method == "auto":
            result = self.analyze_with_bertweet(text)
            if result is None:
                result = self.analyze_with_vader(text)
            if result is None:
                result = self.analyze_with_textblob(text)
        elif method == "bertweet":
            result = self.analyze_with_bertweet(text)
        elif method == "vader":
            result = self.analyze_with_vader(text)
        elif method == "textblob":
            result = self.analyze_with_textblob(text)

        if result is None:
            result = {
                "sentiment": "neutral",
                "confidence": 0.0,
                "method": "fallback",
                "scores": {},
            }

        result["method"] = f"{result['method']}_{source}"
        result["analysis_time"] = round(time.time() - start_time, 3)

        logger.info(
            f"Sentiment={result['sentiment']} "
            f"(confidence={result['confidence']}, method={result['method']})"
        )

        return result

    # ---------------------------------------------------------
    # Compare Methods (OPTION B – FIXED)
    # ---------------------------------------------------------
    def compare_methods(
        self,
        cleaned_text: str | None = None,
        summary_text: str | None = None,
        raw_text: str | None = None,
    ) -> Dict:
        """
        Compare sentiment engines using the same
        cleaned → summary → raw selection logic
        """

        text = None
        source = None

        if cleaned_text and cleaned_text.strip():
            text = cleaned_text
            source = "cleaned"
        elif summary_text and summary_text.strip():
            text = summary_text
            source = "summary"
        elif raw_text and raw_text.strip():
            text = raw_text
            source = "raw"

        if not text:
            return {
                "results": {},
                "consistent": True,
                "majority_sentiment": "neutral",
                "source": "none",
            }

        results = {}

        bt = self.analyze_with_bertweet(text)
        if bt:
            results["bertweet"] = bt

        vd = self.analyze_with_vader(text)
        if vd:
            results["vader"] = vd

        tb = self.analyze_with_textblob(text)
        if tb:
            results["textblob"] = tb

        sentiments = [r["sentiment"] for r in results.values()]

        return {
            "results": results,
            "consistent": len(set(sentiments)) == 1 if sentiments else True,
            "majority_sentiment": max(set(sentiments), key=sentiments.count)
            if sentiments
            else "neutral",
            "source": source,
        }


# ------------------------------------------------------------------
# Singleton accessor
# ------------------------------------------------------------------
_sentiment_service_instance = None


def get_sentiment_service() -> SentimentService:
    global _sentiment_service_instance

    if _sentiment_service_instance is None:
        logger.info("🧠 Creating SentimentService singleton")
        _sentiment_service_instance = SentimentService()

    return _sentiment_service_instance
