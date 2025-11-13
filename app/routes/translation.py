from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from app.database import db
from deep_translator import GoogleTranslator
from datetime import datetime
import logging

# Initialize Blueprint
translation_bp = Blueprint('translation',__name__, url_prefix='/api/documents')

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
    'hi': 'Hindi',
    'ar': 'Arabic',
    'nl': 'Dutch',
    'pl': 'Polish',
    'tr': 'Turkish',
    'th': 'Thai',
    'vi': 'Vietnamese',
    'id': 'Indonesian',
    'fa': 'Persian'
}


@translation_bp.route('/<document_id>/nlp/translate', methods=['POST'])
@jwt_required()
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
        
        # Get user ID from JWT
        user_id = get_jwt_identity()
        
        # Fetch document from database and verify ownership
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500
        
        document = current_app.db.documents.find_one({
            '_id': ObjectId(document_id),
            'user_id': user_id
        })
        
        if not document:
            return jsonify({
                'status': 'error',
                'message': 'Document not found or you do not have access'
            }), 404
        
        content = document.get('content', '')
        
        if not content or len(content.strip()) == 0:
            return jsonify({
                'status': 'error',
                'message': 'Document content is empty'
            }), 400
        
        # Translate text
        try:
            # Handle auto-detection - GoogleTranslator uses 'auto' for auto-detection
            if source_language == 'auto':
                translator = GoogleTranslator(source='auto', target=target_language)
            else:
                translator = GoogleTranslator(source=source_language, target=target_language)
            
            # Google Translate has a character limit (around 5000 chars per request)
            # Split long content into chunks if necessary
            max_chunk_size = 4500  # Leave some buffer
            if len(content) > max_chunk_size:
                # Split content into sentences or chunks
                chunks = []
                current_chunk = ""
                
                # Try to split by sentences first
                sentences = content.split('. ')
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 2 <= max_chunk_size:
                        current_chunk += sentence + '. '
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence + '. '
                
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # Translate each chunk
                translated_chunks = []
                for chunk in chunks:
                    try:
                        translated_chunk = translator.translate(chunk)
                        translated_chunks.append(translated_chunk)
                    except Exception as e:
                        logger.error(f"Error translating chunk: {str(e)}")
                        # If chunk translation fails, try the whole content as fallback
                        translated_text = translator.translate(content)
                        break
                else:
                    # All chunks translated successfully
                    translated_text = ' '.join(translated_chunks)
            else:
                # Content is short enough, translate directly
                translated_text = translator.translate(content)
            
            # Validate translation result
            if not translated_text or len(translated_text.strip()) == 0:
                return jsonify({
                    'status': 'error',
                    'message': 'Translation returned empty result. The content might be too long or contain unsupported characters.'
                }), 500
            
            # Basic validation: check if translation seems reasonable
            if len(translated_text) < len(content) * 0.1:  # Translation is less than 10% of original
                logger.warning(f"Translation seems unusually short: {len(translated_text)} vs {len(content)}")
                
        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            error_message = str(e).lower()
            
            # Provide more specific error messages
            if 'quota' in error_message or 'limit' in error_message:
                return jsonify({
                    'status': 'error',
                    'message': 'Translation service quota exceeded. Please try again later.',
                    'error': str(e)
                }), 429
            elif 'language' in error_message or 'not supported' in error_message:
                return jsonify({
                    'status': 'error',
                    'message': f'Language pair not supported. Please check source and target languages.',
                    'error': str(e)
                }), 400
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Translation failed. Please try again with different language settings.',
                    'error': str(e)
                }), 500
        
        # Store translation history in database
        try:
            # Check if translations array exists, if not create it
            if 'translations' not in document:
                current_app.db.documents.update_one(
                    {'_id': ObjectId(document_id)},
                    {'$set': {'translations': []}}
                )
            
            # Save translation to database
            current_app.db.documents.update_one(
                {'_id': ObjectId(document_id)},
                {'$push': {
                    'translations': {
                        'target_language': target_language,
                        'target_language_name': SUPPORTED_LANGUAGES.get(target_language),
                        'translated_text': translated_text,
                        'source_language': source_language if source_language != 'auto' else 'auto-detected',
                        'timestamp': datetime.utcnow()
                    }
                }}
            )
        except Exception as e:
            logger.warning(f"Could not save translation history: {str(e)}")
        
        # Detect actual source language if auto was used
        detected_source = source_language
        if source_language == 'auto':
            # Try to detect the source language
            try:
                # Use a small sample for detection to avoid rate limits
                sample_text = content[:100] if len(content) > 100 else content
                # GoogleTranslator can detect language, but we'll mark it as auto-detected
                detected_source = 'auto-detected'
            except:
                detected_source = 'auto-detected'
        
        return jsonify({
            'status': 'success',
            'message': 'Translation completed successfully',
            'data': {
                'document_id': str(document_id),
                'title': document.get('filename', 'Untitled'),
                'source_language': detected_source,
                'target_language': target_language,
                'target_language_name': SUPPORTED_LANGUAGES.get(target_language),
                'original_text': content,  # Return full content, not truncated
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
@jwt_required()
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