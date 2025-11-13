from flask import Blueprint, request, jsonify
from bson import ObjectId
from app.database import db
from deep_translator import GoogleTranslator
import logging

# Initialize Blueprint
translation_bp = Blueprint('translation', __name__, url_prefix='/api/documents')

# Setup logging
logger = logging.getLogger(__name__)

# Supported languages
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'ja': 'Japanese',
    'ko': 'Korean',
    'zh-CN': 'Chinese (Simplified)',
    'zh-TW': 'Chinese (Traditional)',
    'ar': 'Arabic',
    'nl': 'Dutch',
    'pl': 'Polish',
    'tr': 'Turkish',
    'th': 'Thai',
    'vi': 'Vietnamese',
    'id': 'Indonesian',
    'fa': 'Persian',
    "hi": "Hindi",
    "bn": "Bengali",
    "te": "Telugu",
    "mr": "Marathi",
    "ta": "Tamil",
    "ur": "Urdu",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "or": "Odia",
    "pa": "Punjabi",
    "as": "Assamese",
    "ma": "Manipuri",
    "ne": "Nepali",
    "sd": "Sindhi",
    "ks": "Kashmiri",
    "kok": "Konkani",
    "mni": "Meitei",
    "sat": "Santali",
    "doi": "Dogri",
    "bho": "Bhojpuri",
    "brx": "Bodo",
    "hif": "Fiji Hindi"
}


@translation_bp.route('/<document_id>/nlp/translate', methods=['POST'])
def translate_document(document_id):
    """
    Translate document content to target language
    
    POST /api/documents/<document_id>/translate
    Request Body:
    {
        "target_language": "es",  # Language code (e.g., es, fr, de, etc.)
        "source_language": "en"   # Optional, auto-detect if not provided
    }
    
    Returns:
        - original_text: Original document content
        - translated_text: Translated content
        - source_language: Detected or provided source language
        - target_language: Target language code
        - target_language_name: Full language name
    """
    try:
        # Validate document ID
        if not ObjectId.is_valid(document_id):
            return jsonify({
                'status': 'error',
                'message': 'Invalid document ID format'
            }), 400
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body is required'
            }), 400
        
        target_language = data.get('target_language', '').lower()
        source_language = data.get('source_language', 'auto').lower()
        
        # Validate target language
        if not target_language:
            return jsonify({
                'status': 'error',
                'message': 'target_language is required'
            }), 400
        
        if target_language not in SUPPORTED_LANGUAGES:
            return jsonify({
                'status': 'error',
                'message': f'Target language "{target_language}" is not supported',
                'supported_languages': SUPPORTED_LANGUAGES
            }), 400
        
        # Fetch document from database
        document = db.documents.find_one({'_id': ObjectId(document_id)})
        
        if not document:
            return jsonify({
                'status': 'error',
                'message': 'Document not found'
            }), 404
        
        content = document.get('content', '')
        
        if not content or len(content.strip()) == 0:
            return jsonify({
                'status': 'error',
                'message': 'Document content is empty'
            }), 400
        
        # Translate text
        try:
            translator = GoogleTranslator(source_language=source_language, target_language=target_language)
            translated_text = translator.translate(content)
        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Translation failed. Please try again with different language settings',
                'error': str(e)
            }), 500
        
        # Store translation history in database (optional)
        try:
            if not hasattr(db.documents.find_one({'_id': ObjectId(document_id)}), 'translations'):
                db.documents.update_one(
                    {'_id': ObjectId(document_id)},
                    {'$set': {'translations': []}}
                )
            
            db.documents.update_one(
                {'_id': ObjectId(document_id)},
                {'$push': {
                    'translations': {
                        'target_language': target_language,
                        'translated_text': translated_text,
                        'timestamp': db.database.datetime.datetime.utcnow()
                    }
                }}
            )
        except Exception as e:
            logger.warning(f"Could not save translation history: {str(e)}")
        
        return jsonify({
            'status': 'success',
            'message': 'Translation completed successfully',
            'data': {
                'document_id': str(document_id),
                'title': document.get('title', 'Untitled'),
                'source_language': source_language if source_language != 'auto' else 'auto-detected',
                'target_language': target_language,
                'target_language_name': SUPPORTED_LANGUAGES.get(target_language),
                'original_text': content[:500] + '...' if len(content) > 500 else content,
                'translated_text': translated_text,
                'character_count': len(content),
                'translated_character_count': len(translated_text)
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error translating document {document_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'An error occurred during translation',
            'error': str(e)
        }), 500


@translation_bp.route('/nlp/languages', methods=['GET'])
def get_supported_languages():
    """
    Get list of supported languages
    
    GET /api/languages
    """
    try:
        return jsonify({
            'status': 'success',
            'message': 'Supported languages retrieved',
            'data': {
                'total_languages': len(SUPPORTED_LANGUAGES),
                'languages': SUPPORTED_LANGUAGES
            }
        }), 200
    except Exception as e:
        logger.error(f"Error fetching supported languages: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'An error occurred',
            'error': str(e)
        }), 500


@translation_bp.route('/<document_id>/nlp/translate-batch', methods=['POST'])
def translate_batch(document_id):
    """
    Translate document to multiple languages at once
    
    POST /api/documents/<document_id>/translate-batch
    Request Body:
    {
        "target_languages": ["es", "fr", "de"],
        "source_language": "en"  # Optional
    }
    """
    try:
        if not ObjectId.is_valid(document_id):
            return jsonify({
                'status': 'error',
                'message': 'Invalid document ID format'
            }), 400
        
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body is required'
            }), 400
        
        target_languages = data.get('target_languages', [])
        source_language = data.get('source_language', 'auto').lower()
        
        if not target_languages or not isinstance(target_languages, list):
            return jsonify({
                'status': 'error',
                'message': 'target_languages must be a list'
            }), 400
        
        # Validate languages
        for lang in target_languages:
            if lang.lower() not in SUPPORTED_LANGUAGES:
                return jsonify({
                    'status': 'error',
                    'message': f'Language "{lang}" is not supported'
                }), 400
        
        # Fetch document
        document = db.documents.find_one({'_id': ObjectId(document_id)})
        
        if not document:
            return jsonify({
                'status': 'error',
                'message': 'Document not found'
            }), 404
        
        content = document.get('content', '')
        
        if not content or len(content.strip()) == 0:
            return jsonify({
                'status': 'error',
                'message': 'Document content is empty'
            }), 400
        
        # Translate to all target languages
        translations = {}
        for target_lang in target_languages:
            try:
                translator = GoogleTranslator(source_language=source_language, target_language=target_lang.lower())
                translations[target_lang.lower()] = translator.translate(content)
            except Exception as e:
                logger.error(f"Error translating to {target_lang}: {str(e)}")
                translations[target_lang.lower()] = None
        
        return jsonify({
            'status': 'success',
            'message': 'Batch translation completed',
            'data': {
                'document_id': str(document_id),
                'title': document.get('title', 'Untitled'),
                'source_language': source_language,
                'translations': translations
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error in batch translation: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'An error occurred during batch translation',
            'error': str(e)
        }), 500