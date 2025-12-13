"""
Migration Script - Update Existing Documents to New Schema
Migrates old documents to support multilingual pipeline
"""

import logging
from datetime import datetime
from app.database import db

logger = logging.getLogger(__name__)


def migrate_documents():
    """
    Migrate existing documents to new schema
    
    Adds default values for new fields:
    - language, clean_text, text_hash
    - translated_text, translation metadata
    - sentiment, event_type, locations
    - pipeline_metrics
    """
    try:
        logger.info("Starting document migration...")
        
        # Find all documents that don't have the new schema
        old_documents = db.documents.find({
            '$or': [
                {'language': {'$exists': False}},
                {'clean_text': {'$exists': False}},
                {'sentiment.label': {'$exists': False}}
            ]
        })
        
        count = 0
        for doc in old_documents:
            doc_id = doc['_id']
            
            # Prepare update fields
            update_fields = {}
            
            # Map old 'content' field to 'raw_text' if exists
            if 'content' in doc and 'raw_text' not in doc:
                update_fields['raw_text'] = doc['content']
            
            # Set defaults for new fields if they don't exist
            if 'clean_text' not in doc:
                update_fields['clean_text'] = doc.get('content', doc.get('raw_text', ''))
            
            if 'language' not in doc:
                update_fields['language'] = 'unknown'  # Will be re-detected
            
            if 'text_hash' not in doc:
                update_fields['text_hash'] = None
            
            if 'translated_text' not in doc:
                update_fields['translated_text'] = None
            
            if 'translation_engine' not in doc:
                update_fields['translation_engine'] = None
            
            if 'translation_time' not in doc:
                update_fields['translation_time'] = None
            
            if 'source' not in doc:
                update_fields['source'] = 'file'
            
            if 'timestamp' not in doc:
                # Use uploaded_at if exists, otherwise created_at
                update_fields['timestamp'] = doc.get('uploaded_at', doc.get('created_at', datetime.utcnow()))
            
            if 'location_hint' not in doc:
                update_fields['location_hint'] = None
            
            if 'event_type_hint' not in doc:
                update_fields['event_type_hint'] = None
            
            # Sentiment structure
            if 'sentiment' not in doc:
                update_fields['sentiment'] = {
                    'label': None,
                    'confidence': None,
                    'method': None,
                    'scores': {}
                }
            
            if 'event_type' not in doc:
                update_fields['event_type'] = None
            
            if 'event_confidence' not in doc:
                update_fields['event_confidence'] = None
            
            if 'locations' not in doc:
                update_fields['locations'] = []
            
            if 'processing_time' not in doc:
                update_fields['processing_time'] = None
            
            if 'pipeline_metrics' not in doc:
                update_fields['pipeline_metrics'] = {
                    'preprocessing_time': None,
                    'translation_time': None,
                    'sentiment_time': None,
                    'event_detection_time': None,
                    'ner_time': None
                }
            
            if 'created_at' not in doc:
                update_fields['created_at'] = doc.get('uploaded_at', datetime.utcnow())
            
            if 'updated_at' not in doc:
                update_fields['updated_at'] = datetime.utcnow()
            
            # Mark as unprocessed so it can be re-processed through new pipeline
            update_fields['processed'] = False
            
            # Perform update
            db.documents.update_one(
                {'_id': doc_id},
                {'$set': update_fields}
            )
            
            count += 1
            
            if count % 10 == 0:
                logger.info(f"Migrated {count} documents...")
        
        logger.info(f"✓ Migration complete! Migrated {count} documents")
        return count
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


def reprocess_migrated_documents():
    """
    Re-process migrated documents through the new pipeline
    This will populate language, sentiment, event, locations, etc.
    """
    logger.info("Re-processing migrated documents...")
    
    # Import services
    from app.services.preprocessing import preprocessing_service
    from app.services.translation import translation_service
    from app.services.sentiment import sentiment_service
    from app.services.event_detection import event_detection_service
    from app.services.location_extraction import location_extraction_service
    from app.models.document import Document
    
    # Find unprocessed documents
    unprocessed_docs = db.documents.find({'processed': False}).limit(50)  # Process in batches
    
    count = 0
    for doc in unprocessed_docs:
        try:
            doc_id = str(doc['_id'])
            raw_text = doc.get('raw_text', doc.get('content', ''))
            
            if not raw_text:
                continue
            
            # 1. Preprocessing
            preprocess_result = preprocessing_service.preprocess(raw_text)
            Document.update_preprocessing(
                db,
                doc_id,
                preprocess_result['clean_text'],
                preprocess_result['language'],
                preprocess_result['text_hash'],
                0.0  # Time not tracked for migration
            )
            
            # 2. Translation (if not English)
            if preprocess_result['language'] != 'en':
                translation_result = translation_service.translate_to_english(
                    preprocess_result['clean_text'],
                    preprocess_result['language']
                )
                
                Document.update_translation(
                    db,
                    doc_id,
                    translation_result['translated_text'],
                    translation_result['translation_engine'],
                    translation_result['translation_time']
                )
                
                # Analyze sentiment on translated text
                text_to_analyze = translation_result['translated_text']
            else:
                text_to_analyze = preprocess_result['clean_text']
            
            # 3. Sentiment Analysis
            sentiment_result = sentiment_service.analyze(text_to_analyze)
            Document.update_sentiment(
                db,
                doc_id,
                sentiment_result['sentiment'],
                sentiment_result['confidence'],
                sentiment_result['method'],
                sentiment_result['scores'],
                sentiment_result['analysis_time']
            )
            
            # 4. Event Detection
            event_result = event_detection_service.classify(text_to_analyze)
            Document.update_event(
                db,
                doc_id,
                event_result['event_type'],
                event_result['confidence'],
                event_result['classification_time']
            )
            
            # 5. Location Extraction
            location_result = location_extraction_service.extract_locations(text_to_analyze)
            Document.update_locations(
                db,
                doc_id,
                location_result['locations'],
                location_result['extraction_time']
            )
            
            # Mark as processed
            Document.mark_processed(db, doc_id, 0.0)
            
            count += 1
            logger.info(f"Re-processed document {count}: {doc.get('filename', doc_id)}")
            
        except Exception as e:
            logger.error(f"Failed to reprocess document {doc.get('_id')}: {e}")
            continue
    
    logger.info(f"✓ Re-processed {count} documents")
    return count


if __name__ == '__main__':
    # Run migration
    print("=" * 60)
    print("Document Migration Script")
    print("=" * 60)
    
    migrated = migrate_documents()
    print(f"\n✓ Migrated {migrated} documents to new schema")
    
    print("\nTo re-process documents through the new pipeline, run:")
    print("from app.utils.migration_script import reprocess_migrated_documents")
    print("reprocess_migrated_documents()")
