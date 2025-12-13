"""
Sentiment Analysis Service
Supports BERTweet (social media focused) and fallback to VADER/TextBlob
Handles multilingual sentiment analysis
"""

import logging
import time
from typing import Dict, Optional
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)


class SentimentService:
    """Service for sentiment analysis operations"""
    
    def __init__(self):
        # Initialize VADER
        self.vader_analyzer = SentimentIntensityAnalyzer()
        
        # BERTweet model (lazy loading)
        self.bertweet_model = None
        self.bertweet_tokenizer = None
        self.bertweet_available = False
        
        # Try to load BERTweet
        self._load_bertweet()
    
    def _load_bertweet(self):
        """Load BERTweet model for social media sentiment analysis"""
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            import torch
            
            logger.info("Loading BERTweet model...")
            
            # BERTweet fine-tuned for sentiment analysis
            model_name = "finiteautomata/bertweet-base-sentiment-analysis"
            
            self.bertweet_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.bertweet_model = AutoModelForSequenceClassification.from_pretrained(model_name)
            
            # Set to evaluation mode
            self.bertweet_model.eval()
            
            self.bertweet_available = True
            logger.info("✓ BERTweet model loaded successfully")
            
        except Exception as e:
            logger.warning(f"BERTweet model not available: {e}")
            logger.info("Will use VADER/TextBlob as fallback")
            self.bertweet_available = False
    
    def analyze_with_bertweet(self, text: str) -> Dict:
        """
        Analyze sentiment using BERTweet (transformer-based)
        
        Args:
            text: Input text
            
        Returns:
            Dictionary with sentiment label and confidence
        """
        try:
            import torch
            
            # Tokenize
            inputs = self.bertweet_tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
            
            # Get predictions
            with torch.no_grad():
                outputs = self.bertweet_model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            
            # Get predicted class and confidence
            predicted_class = torch.argmax(predictions, dim=1).item()
            confidence = predictions[0][predicted_class].item()
            
            # Map to sentiment labels
            # Model outputs: 0=negative, 1=neutral, 2=positive
            sentiment_map = {0: 'negative', 1: 'neutral', 2: 'positive'}
            sentiment_label = sentiment_map[predicted_class]
            
            return {
                'sentiment': sentiment_label,
                'confidence': round(confidence, 3),
                'method': 'bertweet',
                'scores': {
                    'negative': round(predictions[0][0].item(), 3),
                    'neutral': round(predictions[0][1].item(), 3),
                    'positive': round(predictions[0][2].item(), 3)
                }
            }
            
        except Exception as e:
            logger.error(f"BERTweet analysis failed: {e}")
            return None
    
    def analyze_with_vader(self, text: str) -> Dict:
        """
        Analyze sentiment using VADER (lexicon-based)
        
        Args:
            text: Input text
            
        Returns:
            Dictionary with sentiment label and confidence
        """
        try:
            scores = self.vader_analyzer.polarity_scores(text)
            compound = scores['compound']
            
            # Determine sentiment label
            if compound >= 0.05:
                sentiment_label = 'positive'
            elif compound <= -0.05:
                sentiment_label = 'negative'
            else:
                sentiment_label = 'neutral'
            
            # Calculate confidence based on compound score strength
            confidence = abs(compound)
            
            return {
                'sentiment': sentiment_label,
                'confidence': round(confidence, 3),
                'method': 'vader',
                'scores': {
                    'negative': round(scores['neg'], 3),
                    'neutral': round(scores['neu'], 3),
                    'positive': round(scores['pos'], 3),
                    'compound': round(compound, 3)
                }
            }
            
        except Exception as e:
            logger.error(f"VADER analysis failed: {e}")
            return None
    
    def analyze_with_textblob(self, text: str) -> Dict:
        """
        Analyze sentiment using TextBlob (simple baseline)
        
        Args:
            text: Input text
            
        Returns:
            Dictionary with sentiment label and confidence
        """
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
            
            # Determine sentiment label
            if polarity > 0.1:
                sentiment_label = 'positive'
            elif polarity < -0.1:
                sentiment_label = 'negative'
            else:
                sentiment_label = 'neutral'
            
            return {
                'sentiment': sentiment_label,
                'confidence': round(abs(polarity), 3),
                'method': 'textblob',
                'scores': {
                    'polarity': round(polarity, 3),
                    'subjectivity': round(subjectivity, 3)
                }
            }
            
        except Exception as e:
            logger.error(f"TextBlob analysis failed: {e}")
            return None
    
    def analyze(self, text: str, method: str = 'auto') -> Dict:
        """
        Analyze sentiment using specified or best available method
        
        Args:
            text: Input text
            method: 'auto', 'bertweet', 'vader', 'textblob'
            
        Returns:
            Dictionary with:
                - sentiment: Positive, negative, or neutral
                - confidence: Confidence score
                - method: Method used
                - scores: Detailed scores
                - analysis_time: Time taken
        """
        start_time = time.time()
        
        try:
            if not text or len(text.strip()) == 0:
                return {
                    'sentiment': 'neutral',
                    'confidence': 0.0,
                    'method': 'none',
                    'scores': {},
                    'analysis_time': 0.0,
                    'error': 'Empty text'
                }
            
            result = None
            
            # Auto mode: try BERTweet first, fall back to VADER
            if method == 'auto':
                if self.bertweet_available:
                    result = self.analyze_with_bertweet(text)
                
                if result is None:
                    result = self.analyze_with_vader(text)
                
                if result is None:
                    result = self.analyze_with_textblob(text)
            
            # Specific method requested
            elif method == 'bertweet' and self.bertweet_available:
                result = self.analyze_with_bertweet(text)
            elif method == 'vader':
                result = self.analyze_with_vader(text)
            elif method == 'textblob':
                result = self.analyze_with_textblob(text)
            
            # If specific method failed, use fallback
            if result is None:
                logger.warning(f"Method {method} failed, using VADER fallback")
                result = self.analyze_with_vader(text)
            
            analysis_time = time.time() - start_time
            result['analysis_time'] = round(analysis_time, 3)
            
            logger.info(f"Sentiment: {result['sentiment']} (confidence: {result['confidence']}, method: {result['method']})")
            
            return result
            
        except Exception as e:
            analysis_time = time.time() - start_time
            logger.error(f"Sentiment analysis failed: {e}")
            
            return {
                'sentiment': 'neutral',
                'confidence': 0.0,
                'method': 'error',
                'scores': {},
                'analysis_time': round(analysis_time, 3),
                'error': str(e)
            }
    
    def compare_methods(self, text: str) -> Dict:
        """
        Compare sentiment across all available methods
        
        Args:
            text: Input text
            
        Returns:
            Dictionary with results from all methods
        """
        results = {}
        
        if self.bertweet_available:
            results['bertweet'] = self.analyze_with_bertweet(text)
        
        results['vader'] = self.analyze_with_vader(text)
        results['textblob'] = self.analyze_with_textblob(text)
        
        # Check consistency
        sentiments = [r['sentiment'] for r in results.values() if r is not None]
        consistent = len(set(sentiments)) == 1
        
        return {
            'results': results,
            'consistent': consistent,
            'majority_sentiment': max(set(sentiments), key=sentiments.count) if sentiments else 'neutral'
        }


# Singleton instance
sentiment_service = SentimentService()
