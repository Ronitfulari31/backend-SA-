# app/models/document.py
"""
Document Model - Updated for Multimodal Multilingual Sentiment Analysis
Supports: language detection, translation, sentiment, event detection, locations
"""

from datetime import datetime
from bson import ObjectId
from typing import Optional, Dict, List


class Document:
    """Document model with multilingual pipeline support"""
    
    @staticmethod
    def create(
        db,
        user_id: str,
        raw_text: str,
        filename: Optional[str] = None,
        file_path: Optional[str] = None,
        file_type: Optional[str] = None,
        source: str = 'file',
        location_hint: Optional[str] = None,
        event_type_hint: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Create a new document record with multilingual support
        
        Args:
            db: Database connection
            user_id: User ID who owns this document
            raw_text: Original unprocessed text
            filename: Original filename (optional)
            file_path: File storage path (optional)
            file_type: File extension (optional)
            source: Data source (file, twitter, news, etc.)
            location_hint: Optional location hint from user
            event_type_hint: Optional event type hint
            metadata: Additional metadata
            
        Returns:
            Document ID (string)
        """
        doc = {
            # Original data
            'raw_text': raw_text,
            'clean_text': None,  # Will be populated by preprocessing
            
            # Language
            'language': None,  # Will be detected
            'text_hash': None,  # For duplicate detection
            
            # Translation
            'translated_text': None,
            'translation_engine': None,
            'translation_time': None,
            
            # Metadata
            'source': source,
            'timestamp': datetime.utcnow(),
            'location_hint': location_hint,
            'event_type_hint': event_type_hint,
            
            # File info (optional)
            'filename': filename,
            'file_path': file_path,
            'file_type': file_type,
            
            # Analysis results
            'sentiment': {
                'label': None,  # positive, negative, neutral
                'confidence': None,
                'method': None,  # bertweet, vader, textblob
                'scores': {}
            },
            
            'event_type': None,
            'event_confidence': None,
            
            'locations': [],  # Array of location dictionaries
            
            # Performance tracking
            'processing_time': None,
            'pipeline_metrics': {
                'preprocessing_time': None,
                'translation_time': None,
                'sentiment_time': None,
                'event_detection_time': None,
                'ner_time': None
            },
            
            # User and system metadata
            'user_id': user_id,
            'metadata': metadata or {},
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'processed': False
        }
        
        result = db.documents.insert_one(doc)
        return str(result.inserted_id)
    
    @staticmethod
    def update_preprocessing(
        db,
        doc_id: str,
        clean_text: str,
        language: str,
        text_hash: str,
        preprocessing_time: float
    ):
        """Update document with preprocessing results"""
        db.documents.update_one(
            {'_id': ObjectId(doc_id)},
            {
                '$set': {
                    'clean_text': clean_text,
                    'language': language,
                    'text_hash': text_hash,
                    'pipeline_metrics.preprocessing_time': preprocessing_time,
                    'updated_at': datetime.utcnow()
                }
            }
        )
    
    @staticmethod
    def update_translation(
        db,
        doc_id: str,
        translated_text: str,
        translation_engine: str,
        translation_time: float
    ):
        """Update document with translation results"""
        db.documents.update_one(
            {'_id': ObjectId(doc_id)},
            {
                '$set': {
                    'translated_text': translated_text,
                    'translation_engine': translation_engine,
                    'translation_time': translation_time,
                    'pipeline_metrics.translation_time': translation_time,
                    'updated_at': datetime.utcnow()
                }
            }
        )
    
    @staticmethod
    def update_sentiment(
        db,
        doc_id: str,
        sentiment_label: str,
        confidence: float,
        method: str,
        scores: Dict,
        sentiment_time: float
    ):
        """Update document with sentiment analysis results"""
        db.documents.update_one(
            {'_id': ObjectId(doc_id)},
            {
                '$set': {
                    'sentiment.label': sentiment_label,
                    'sentiment.confidence': confidence,
                    'sentiment.method': method,
                    'sentiment.scores': scores,
                    'pipeline_metrics.sentiment_time': sentiment_time,
                    'updated_at': datetime.utcnow()
                }
            }
        )
    
    @staticmethod
    def update_event(
        db,
        doc_id: str,
        event_type: str,
        event_confidence: float,
        event_detection_time: float
    ):
        """Update document with event classification results"""
        db.documents.update_one(
            {'_id': ObjectId(doc_id)},
            {
                '$set': {
                    'event_type': event_type,
                    'event_confidence': event_confidence,
                    'pipeline_metrics.event_detection_time': event_detection_time,
                    'updated_at': datetime.utcnow()
                }
            }
        )
    
    @staticmethod
    def update_locations(
        db,
        doc_id: str,
        locations: List[Dict],
        ner_time: float
    ):
        """Update document with location extraction results"""
        db.documents.update_one(
            {'_id': ObjectId(doc_id)},
            {
                '$set': {
                    'locations': locations,
                    'pipeline_metrics.ner_time': ner_time,
                    'updated_at': datetime.utcnow()
                }
            }
        )
    
    @staticmethod
    def mark_processed(db, doc_id: str, processing_time: float):
        """Mark document as fully processed"""
        db.documents.update_one(
            {'_id': ObjectId(doc_id)},
            {
                '$set': {
                    'processed': True,
                    'processing_time': processing_time,
                    'updated_at': datetime.utcnow()
                }
            }
        )
    
    @staticmethod
    def get_by_id(db, doc_id: str):
        """Get document by ID"""
        return db.documents.find_one({'_id': ObjectId(doc_id)})
    
    @staticmethod
    def get_by_user(db, user_id: str, limit: int = 100):
        """Get all documents for a user"""
        return list(db.documents.find({'user_id': user_id}).limit(limit))
    
    @staticmethod
    def find_duplicate(db, text_hash: str):
        """Check if document with same hash exists"""
        return db.documents.find_one({'text_hash': text_hash})
    
    @staticmethod
    def get_by_filters(
        db,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        sentiment: Optional[str] = None,
        language: Optional[str] = None,
        source: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ):
        """Get documents with various filters for dashboard queries"""
        query = {}
        
        if user_id:
            query['user_id'] = user_id
        if event_type:
            query['event_type'] = event_type
        if sentiment:
            query['sentiment.label'] = sentiment
        if language:
            query['language'] = language
        if source:
            query['source'] = source
        if start_date or end_date:
            query['timestamp'] = {}
            if start_date:
                query['timestamp']['$gte'] = start_date
            if end_date:
                query['timestamp']['$lte'] = end_date
        
        return list(db.documents.find(query).limit(limit).sort('timestamp', -1))

