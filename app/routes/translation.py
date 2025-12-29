from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.services.translation import translation_service
import logging

translation_bp = Blueprint('translation', __name__)
logger = logging.getLogger(__name__)

@translation_bp.route('/translate', methods=['POST'])
@jwt_required()
def translate_text():
    """
    Translate text using the translation service
    
    Request body:
    {
        "text": "Text to translate",
        "source_lang": "en",
        "target_lang": "es"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Text is required'
            }), 400

        text = data['text']
        source_lang = data.get('source_lang', 'auto')
        target_lang = data.get('target_lang', 'en')

        if not text:
            return jsonify({
                'status': 'error',
                'message': 'Text cannot be empty'
            }), 400

        # Use the service to translate
        translated_text = translation_service.translate_text(
            text=text,
            target_lang=target_lang,
            source_lang=source_lang
        )

        return jsonify({
            'status': 'success',
            'data': {
                'original_text': text,
                'translated_text': translated_text,
                'source_lang': source_lang,
                'target_lang': target_lang
            }
        }), 200

    except Exception as e:
        logger.error(f"Translation API error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Translation failed: {str(e)}'
        }), 500
