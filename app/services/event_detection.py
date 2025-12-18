"""
Event Detection Service
Keyword-based hybrid classifier for disaster event classification
Events: flood, fire, earthquake, landslide, terror_attack, other
"""

import logging
import time
from typing import Dict, List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import re

logger = logging.getLogger(__name__)


class EventDetectionService:
    """Service for disaster event classification"""
    
    def __init__(self):
        # Disaster event keywords mapping
        self.event_keywords = {
            'flood': [
                'flood', 'flooding', 'flooded', 'water', 'rain', 'rainfall', 'heavy rain',
                'monsoon', 'overflow', 'river', 'dam', 'inundation', 'waterlogging',
                'submerged', 'drowned', 'drowning', 'rescue', 'evacuation', 'shelter',
                'बाढ़', 'पानी', 'बारिश'
            ],
            'fire': [
                'fire', 'burning', 'burnt', 'flame', 'smoke', 'blaze', 'wildfire',
                'forest fire', 'arson', 'explosion', 'burn', 'inferno', 'firefighter',
                'extinguish', 'ignite', 'combustion'
            ],
            'earthquake': [
                'earthquake', 'quake', 'tremor', 'seismic', 'magnitude', 'richter',
                'epicenter', 'aftershock', 'tsunami', 'shaking', 'ground', 'collapse',
                'building collapse', 'rubble', 'भूकंप'  
            ],
            'landslide': [
                'landslide', 'mudslide', 'avalanche', 'debris', 'slope', 'hill',
                'mountain', 'rock fall', 'soil', 'erosion', 'collapse', 'buried',
                'भूस्खलन'  #
            ],
            'terror_attack': [
                'attack', 'terror', 'terrorist', 'bombing', 'blast', 'shooting',
                'shooter', 'gunfire', 'explosion', 'violence', 'victim', 'casualties',
                'injured', 'killed', 'death', 'assault', 'hostage', 'militant'
            ]
        }
        
        # Pre-trained simple classifier (will be replaced with real data if available)
        self.vectorizer = None
        self.classifier = None
        self._initialize_baseline_classifier()
    
    def _initialize_baseline_classifier(self):
        """Initialize a baseline classifier using keyword examples"""
        try:
            # Create training examples from keywords
            training_texts = []
            training_labels = []
            
            for event_type, keywords in self.event_keywords.items():
                for keyword in keywords[:5]:  # Use first 5 keywords as examples
                    training_texts.append(keyword)
                    training_labels.append(event_type)
            
            # Train a simple Naive Bayes classifier
            self.vectorizer = TfidfVectorizer(max_features=100)
            X = self.vectorizer.fit_transform(training_texts)
            
            self.classifier = MultinomialNB()
            self.classifier.fit(X, training_labels)
            
            logger.info("Baseline event classifier initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize baseline classifier: {e}")
    
    def classify_by_keywords(self, text: str) -> Dict:
        """
        Classify event using keyword matching
        
        Args:
            text: Input text
            
        Returns:
            Dictionary with event_type and confidence
        """
        text_lower = text.lower()
        
        # Count keyword matches for each event type
        event_scores = {}
        
        for event_type, keywords in self.event_keywords.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                # Use word boundaries for better matching
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                matches = len(re.findall(pattern, text_lower))
                
                if matches > 0:
                    score += matches
                    matched_keywords.append(keyword)
            
            if score > 0:
                event_scores[event_type] = {
                    'score': score,
                    'matched_keywords': matched_keywords
                }
        
        # Determine most likely event
        if not event_scores:
            return {
                'event_type': 'other',
                'confidence': 0.0,
                'method': 'keyword',
                'matched_keywords': []
            }
        
        # Get event with highest score
        best_event = max(event_scores.items(), key=lambda x: x[1]['score'])
        event_type = best_event[0]
        score = best_event[1]['score']
        matched_keywords = best_event[1]['matched_keywords']
        
        # Calculate confidence (normalize by text length)
        word_count = len(text.split())
        confidence = min(score / max(word_count, 1), 1.0)
        
        return {
            'event_type': event_type,
            'confidence': round(confidence, 3),
            'method': 'keyword',
            'matched_keywords': matched_keywords[:5]  # Limit to top 5
        }
    
    def classify_by_ml(self, text: str) -> Dict:
        """
        Classify event using ML classifier
        
        Args:
            text: Input text
            
        Returns:
            Dictionary with event_type and confidence
        """
        try:
            if self.vectorizer is None or self.classifier is None:
                return None
            
            # Vectorize text
            X = self.vectorizer.transform([text])
            
            # Predict
            predicted_event = self.classifier.predict(X)[0]
            
            # Get probability scores
            probabilities = self.classifier.predict_proba(X)[0]
            max_prob = max(probabilities)
            
            return {
                'event_type': predicted_event,
                'confidence': round(max_prob, 3),
                'method': 'ml'
            }
            
        except Exception as e:
            logger.error(f"ML classification failed: {e}")
            return None
    
    def classify(self, text: str, method: str = 'hybrid') -> Dict:
        """
        Classify disaster event using specified method
        
        Args:
            text: Input text
            method: 'keyword', 'ml', or 'hybrid'
            
        Returns:
            Dictionary with:
                - event_type: Classified event type
                - confidence: Confidence score
                - method: Method used
                - classification_time: Time taken
        """
        start_time = time.time()
        
        try:
            if not text or len(text.strip()) == 0:
                return {
                    'event_type': 'other',
                    'confidence': 0.0,
                    'method': method,
                    'classification_time': 0.0,
                    'error': 'Empty text'
                }
            
            result = None
            
            if method == 'hybrid':
                # Try keyword first (more reliable for disasters)
                keyword_result = self.classify_by_keywords(text)
                
                # If keyword confidence is high, use it
                if keyword_result['confidence'] > 0.3:
                    result = keyword_result
                else:
                    # Otherwise, try ML
                    ml_result = self.classify_by_ml(text)
                    
                    if ml_result:
                        # Combine results: if both agree, increase confidence
                        if ml_result['event_type'] == keyword_result['event_type']:
                            result = keyword_result
                            result['confidence'] = min(keyword_result['confidence'] + 0.2, 1.0)
                            result['method'] = 'hybrid'
                        else:
                            # Use keyword result with lower confidence
                            result = keyword_result
                    else:
                        result = keyword_result
            
            elif method == 'keyword':
                result = self.classify_by_keywords(text)
            
            elif method == 'ml':
                result = self.classify_by_ml(text)
                if result is None:
                    result = self.classify_by_keywords(text)
            
            classification_time = time.time() - start_time
            result['classification_time'] = round(classification_time, 3)
            
            logger.info(f"Event classified: {result['event_type']} (confidence: {result['confidence']})")
            
            return result
            
        except Exception as e:
            classification_time = time.time() - start_time
            logger.error(f"Event classification failed: {e}")
            
            return {
                'event_type': 'other',
                'confidence': 0.0,
                'method': method,
                'classification_time': round(classification_time, 3),
                'error': str(e)
            }
    
    def get_event_types(self) -> List[str]:
        """Get list of supported event types"""
        return ['flood', 'fire', 'earthquake', 'landslide', 'terror_attack', 'other']


# Singleton instance
event_detection_service = EventDetectionService()
