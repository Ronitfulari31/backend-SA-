"""
Documents Routes - Refactored for Multilingual Pipeline Integration
Handles document upload with automated processing through all services
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_cors import cross_origin
from werkzeug.utils import secure_filename
import os
import time
import logging
from bson import ObjectId

# Import models
from app.models.document import Document

from app.services.location_extraction import location_extraction_service
from app.services.pipeline import process_document_pipeline
from app.services.translation import translation_service
from app.services.sentiment import get_sentiment_service
from app.utils.language import decide_second_language, translate_analysis_additive, get_or_create_translated_analysis

logger = logging.getLogger(__name__)
documents_bp = Blueprint('documents', __name__)

ALLOWED_EXTENSIONS = {'csv', 'txt', 'pdf', 'docx', 'json', 'md', 'rtf'}


def extract_text(file_path, file_type):
    """Extract text from various file formats"""
    text = ""
    try:
        if file_type == 'csv':
            import pandas as pd
            text = pd.read_csv(file_path).to_string()
        elif file_type == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        elif file_type == 'pdf':
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            text = " ".join([p.extract_text() or "" for p in reader.pages])
        elif file_type == 'docx':
            import docx
            doc = docx.Document(file_path)
            text = "\n".join([p.text for p in doc.paragraphs])
        elif file_type == 'json':
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            text = str(data)
        elif file_type == 'md':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        elif file_type == 'rtf':
            from striprtf.striprtf import rtf_to_text
            with open(file_path, 'r', encoding='utf-8') as f:
                text = rtf_to_text(f.read())
    except Exception as e:
        text = ""
        logger.warning(f"Text extraction failed for {file_type}: {e}")
    return text





@documents_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_document():
    """
    Upload a document and process through multilingual pipeline
    
    Accepts:
    - file: Document file (required)
    - source: Data source (optional, default: 'file')
    - location_hint: Location hint (optional)
    - event_type_hint: Event type hint (optional)
    """
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        # Check for file
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No file provided'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No file selected'
            }), 400

        # Get metadata from form data
        source = request.form.get('source', 'file')
        location_hint = request.form.get('location_hint', None)
        event_type_hint = request.form.get('event_type_hint', None)

        filename = secure_filename(file.filename)
        file_type = filename.split('.')[-1].lower()

        if file_type not in ALLOWED_EXTENSIONS:
            return jsonify({
                'status': 'error',
                'message': f'File type .{file_type} not allowed'
            }), 400

        # Save file
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)

        # Extract text
        raw_text = extract_text(file_path, file_type)
        
        if not raw_text or len(raw_text.strip()) == 0:
            return jsonify({
                'status': 'error',
                'message': 'Could not extract text from file'
            }), 400

        # Get user ID
        user_id = get_jwt_identity()

        # Create document with new schema
        doc_id = Document.create(
            current_app.db,
            user_id=user_id,
            raw_text=raw_text,
            filename=filename,
            file_path=file_path,
            file_type=file_type,
            source=source,
            location_hint=location_hint,
            event_type_hint=event_type_hint
        )

        return jsonify({
            'status': 'success',
            'message': 'Document uploaded and saved successfully',
            'data': {
                'document_id': doc_id,
                'filename': filename,
                'file_type': file_type,
                'status': 'pending_analysis'
            }
        }), 201

    except Exception as e:
        import traceback
        logger.error(f"Upload error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'message': f'Upload failed: {str(e)}'
        }), 500


@documents_bp.route('/upload-text', methods=['POST'])
@jwt_required()
def upload_text():
    """
    Upload raw text directly (no file upload)
    
    Request body:
    {
        "text": "Raw text content",
        "source": "twitter|news|file",
        "location_hint": "Optional location",
        "event_type_hint": "Optional event type"
}
    """
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Text content required'
            }), 400

        raw_text = data['text']
        source = data.get('source', 'api')
        location_hint = data.get('location_hint', None)
        event_type_hint = data.get('event_type_hint', None)

        if not raw_text or len(raw_text.strip()) == 0:
            return jsonify({
                'status': 'error',
                'message': 'Text cannot be empty'
            }), 400

        # Get user ID
        user_id = get_jwt_identity()

        # Create document
        doc_id = Document.create(
            current_app.db,
            user_id=user_id,
            raw_text=raw_text,
            source=source,
            location_hint=location_hint,
            event_type_hint=event_type_hint
        )

        return jsonify({
            'status': 'success',
            'message': 'Text saved successfully',
            'data': {
                'document_id': doc_id,
                'status': 'pending_analysis'
            }
        }), 201

    except Exception as e:
        import traceback
        logger.error(f"Text upload error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'message': f'Upload failed: {str(e)}'
        }), 500


@documents_bp.route('/upload-batch', methods=['POST'])
@jwt_required()
def upload_batch():
    """
    Upload multiple text documents at once
    
    Request body:
    {
        "documents": [
            {
                "text": "Document 1 text",
                "source": "twitter",
                "location_hint": "Mumbai",
                "event_type_hint": "flood"
            },
            ...
        ]
    }
    """
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        data = request.get_json()
        
        if not data or 'documents' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Documents array required'
            }), 400

        documents = data['documents']
        
        if not isinstance(documents, list) or len(documents) == 0:
            return jsonify({
                'status': 'error',
                'message': 'Documents must be a non-empty array'
            }), 400

        user_id = get_jwt_identity()
        results = []

        for idx, doc_data in enumerate(documents):
            try:
                raw_text = doc_data.get('text', '')
                
                if not raw_text:
                    results.append({
                        'index': idx,
                        'status': 'error',
                        'message': 'Empty text'
                    })
                    continue

                # Create document
                doc_id = Document.create(
                    current_app.db,
                    user_id=user_id,
                    raw_text=raw_text,
                    source=doc_data.get('source', 'batch'),
                    location_hint=doc_data.get('location_hint', None),
                    event_type_hint=doc_data.get('event_type_hint', None)
                )

                results.append({
                    'index': idx,
                    'status': 'success',
                    'document_id': doc_id,
                    'message': 'Saved successfully (ready for analysis)'
                })

            except Exception as e:
                results.append({
                    'index': idx,
                    'status': 'error',
                    'message': str(e)
                })

        success_count = sum(1 for r in results if r['status'] == 'success')

        return jsonify({
            'status': 'success',
            'message': f'Batch upload complete: {success_count}/{len(documents)} successful',
            'data': {
                'total': len(documents),
                'successful': success_count,
                'results': results
            }
        }), 201

    except Exception as e:
        logger.error(f"Batch upload error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Batch upload failed: {str(e)}'
        }), 500


@documents_bp.route('/list', methods=['GET'])
@jwt_required()
def list_documents():
    """
    List all documents for the logged-in user with filters
    
    Query params:
    - event_type: Filter by event type
    - sentiment: Filter by sentiment (positive, negative, neutral)
    - language: Filter by language
    - source: Filter by source
    - limit: Number of results (default: 100)
    """
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        user_id = get_jwt_identity()

        # Get filters from query params
        event_type = request.args.get('event_type', None)
        sentiment = request.args.get('sentiment', None)
        language = request.args.get('language', None)
        source = request.args.get('source', None)
        limit = int(request.args.get('limit', 100))

        # Get documents with filters
        documents = Document.get_by_filters(
            current_app.db,
            user_id=user_id,
            event_type=event_type,
            sentiment=sentiment,
            language=language,
            source=source,
            limit=limit
        )

        docs_list = []
        for doc in documents:
            docs_list.append({
                'document_id': str(doc['_id']),
                'filename': doc.get('filename', 'N/A'),
                'source': doc.get('source', 'unknown'),
                'language': doc.get('language', 'unknown'),
                'sentiment': doc.get('sentiment', {}).get('label', 'unknown'),
                'event_type': doc.get('event_type', 'unknown'),
                'locations': len(doc.get('locations', [])),
                'timestamp': str(doc.get('timestamp', '')),
                'processed': doc.get('processed', False),
                'text_preview': doc.get('clean_text','')[:150] + '...' if doc.get('clean_text') else doc.get('raw_text', '')[:150] + '...'
            })

        return jsonify({
            'status': 'success',
            'message': 'Documents retrieved successfully',
            'data': {
                'documents': docs_list,
                'total': len(docs_list),
                'filters_applied': {
                    'event_type': event_type,
                    'sentiment': sentiment,
                    'language': language,
                    'source': source
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"List documents error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve documents: {str(e)}'
        }), 500


@documents_bp.route('/<doc_id>', methods=['GET'])
@jwt_required()
def get_document(doc_id):
    """Get full document details with all analysis results"""
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        user_id = get_jwt_identity()

        # Find the document
        document = current_app.db.documents.find_one({
            '_id': ObjectId(doc_id),
            'user_id': user_id
        })

        if not document:
            return jsonify({
                'status': 'error',
                'message': 'Document not found'
            }), 404

        doc_data = {
            'document_id': str(document['_id']),
            'filename': document.get('filename', 'N/A'),
            'source': document.get('source', 'unknown'),
            'timestamp': str(document.get('timestamp', '')),
            'raw_text': document.get('raw_text', ''),
            'clean_text': document.get('clean_text', ''),
            'language': document.get('language', 'unknown'),
            'translated_text': document.get('translated_text', None),
            'sentiment': document.get('sentiment', {}),
            'event_type': document.get('event_type', 'unknown'),
            'event_confidence': document.get('event_confidence', 0.0),
            'locations': document.get('locations', []),
            'processing_time': document.get('processing_time', 0.0),
            'pipeline_metrics': document.get('pipeline_metrics', {}),
            'processed': document.get('processed', False)
        }

        # 🔹 Multi-Language Response Architecture (Additive)
        article_lang = document.get("language")
        second_lang = decide_second_language(article_lang)

        if second_lang:
            try:
                # Build analysis_en for translation helper
                analysis_en = {
                    "sentiment": doc_data["sentiment"],
                    "location": doc_data["locations"],
                }
                
                # Use read-through cache
                translated_data = get_or_create_translated_analysis(
                    doc=document,
                    analysis_en=analysis_en,
                    target_lang=second_lang,
                    translator_service=translation_service,
                    collection=current_app.db.documents,
                    logger=logger
                )
                
                doc_data["analysis_translated"] = {
                    second_lang: translated_data
                }
            except Exception as te:
                logger.error(f"Additive translation failed for {second_lang}: {te}")

        return jsonify({
            'status': 'success',
            'message': 'Document retrieved successfully',
            'data': doc_data
        }), 200

    except Exception as e:
        logger.error(f"Get document error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve document: {str(e)}'
        }), 500


@documents_bp.route('/<doc_id>', methods=['DELETE'])
@jwt_required()
def delete_document(doc_id):
    """Delete a document"""
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        user_id = get_jwt_identity()

        # Find the document
        document = current_app.db.documents.find_one({
            '_id': ObjectId(doc_id),
            'user_id': user_id
        })

        if not document:
            return jsonify({
                'status': 'error',
                'message': 'Document not found'
            }), 404

        # Delete file if exists
        try:
            file_path = document.get('file_path')
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.warning(f"Could not delete file: {e}")

        # Delete from database
        current_app.db.documents.delete_one({'_id': ObjectId(doc_id)})

        return jsonify({
            'status': 'success',
            'message': 'Document deleted successfully',
            'data': {
                'document_id': doc_id
            }
        }), 200

    except Exception as e:
        logger.error(f"Delete document error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to delete document: {str(e)}'
        }), 500


@documents_bp.route('/<doc_id>/analyze-sentiment', methods=['POST'])
@jwt_required()
def analyze_document_sentiment(doc_id):
    """Run standalone sentiment analysis on a document"""
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        user_id = get_jwt_identity()

        # Find the document
        document = current_app.db.documents.find_one({
            '_id': ObjectId(doc_id),
            'user_id': user_id
        })

        if not document:
            return jsonify({
                'status': 'error',
                'message': 'Document not found'
            }), 404

        # Perform Analysis
        start_time = time.time()
        sentiment_service = get_sentiment_service()
        
        # Prefer clean text, fall back to raw
        text_to_analyze = document.get('clean_text') or document.get('raw_text') or ""
        
        result = sentiment_service.analyze(raw_text=text_to_analyze)
        time_taken = time.time() - start_time

        # Update Document
        Document.update_sentiment(
            current_app.db,
            doc_id,
            label=result.get('sentiment'),
            confidence=result.get('confidence', 0.0),
            method=result.get('method', 'manual_trigger'),
            scores=result.get('scores', {}),
            time_taken=time_taken,
            collection="documents"
        )

        return jsonify({
            'status': 'success',
            'message': 'Sentiment analysis completed',
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"Sentiment analysis error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Analysis failed: {str(e)}'
        }), 500

    except Exception as e:
        logger.error(f"Delete document error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to delete document: {str(e)}'
        }), 500


@documents_bp.route('/<doc_id>/summarize', methods=['POST', 'OPTIONS'])
@cross_origin()
@jwt_required()
def summarize_document(doc_id):
    """Generate summary for a document"""
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        user_id = get_jwt_identity()

        # Find the document
        document = current_app.db.documents.find_one({
            '_id': ObjectId(doc_id),
            'user_id': user_id
        })

        if not document:
            return jsonify({
                'status': 'error',
                'message': 'Document not found'
            }), 404

        # Perform Summarization
        start_time = time.time()
        from app.services.summarization import summarization_service
        from app.services.translation import translation_service
        
        # Prefer clean text, fall back to raw
        text_to_summarize = document.get('clean_text') or document.get('raw_text') or ""
        
        # Detect document language
        doc_language = document.get('language', 'en')
        
        # Skip translation if language is None or unknown
        if not doc_language or doc_language == 'unknown':
            doc_language = 'en'
        
        logger.info(f"Document language detected as: {doc_language}")
        logger.info(f"Text preview: {text_to_summarize[:100]}...")
        
        # Step 1: Translate to English if not already English
        english_text = text_to_summarize
        if doc_language != 'en':
            try:
                logger.info(f"Translating document from {doc_language} to English for summarization")
                # Pass source language explicitly to avoid auto-detection issues
                result = translation_service.translate_to_english(text_to_summarize, source_language=doc_language)
                
                # Handle dict response from translate_to_english
                if isinstance(result, dict):
                    english_text = result.get('translated_text', text_to_summarize)
                else:
                    english_text = result
                    
                logger.info(f"Translated text preview: {english_text[:100]}...")
            except Exception as e:
                logger.warning(f"Translation to English failed: {str(e)}, using original text")
                english_text = text_to_summarize
        else:
            # Language is marked as English, but let's verify by checking the text
            # If text contains non-ASCII characters, it might be mislabeled
            if any(ord(char) > 127 for char in text_to_summarize[:200]):
                logger.warning(f"Document marked as English but contains non-ASCII characters. Attempting auto-translation.")
                try:
                    result = translation_service.translate_to_english(text_to_summarize, source_language='auto')
                    if isinstance(result, dict):
                        english_text = result.get('translated_text', text_to_summarize)
                        detected_lang = result.get('original_language', 'unknown')
                        logger.info(f"Auto-detected language: {detected_lang}")
                        # Update doc_language with the detected language for back-translation
                        if detected_lang and detected_lang != 'auto' and detected_lang != 'unknown':
                            doc_language = detected_lang
                    else:
                        english_text = result
                except Exception as e:
                    logger.warning(f"Auto-translation failed: {str(e)}")
        
        # Step 2: Generate English summary
        summary = summarization_service.summarize(english_text, method="lsa", sentences_count=3)
        time_taken = time.time() - start_time

        # Calculate reduction stats
        original_len = len(text_to_summarize.split())
        summary_len = len(summary.split())
        reduction = round((1 - (summary_len / original_len)) * 100, 1) if original_len > 0 else 0

        # Step 3: Translate summary back to original language if not English
        translated_summary = None
        if doc_language != 'en':
            try:
                logger.info(f"Translating summary from English to {doc_language}")
                # Use translate_text which uses Google Translate with Argos fallback
                # translate_text(text, target_lang, source_lang)
                translated_summary = translation_service.translate_text(summary, doc_language, 'en')
            except Exception as e:
                logger.warning(f"Failed to translate summary to {doc_language}: {str(e)}")
                translated_summary = None

        # Update Document with both summaries
        update_data = {
            'summary': summary,
            'metadata.summarized_at': datetime.utcnow()
        }
        
        # Only add translated summary if translation succeeded and language is not English
        if translated_summary and doc_language != 'en':
            update_data['summary_translated'] = {
                doc_language: translated_summary
            }

        current_app.db.documents.update_one(
            {'_id': ObjectId(doc_id)},
            {'$set': update_data}
        )

        # Prepare response
        response_data = {
            'summary': {
                'en': summary
            },
            'stats': {
                'time_taken': round(time_taken, 3),
                'reduction_percentage': reduction
            }
        }
        
        # Only include translated summary if it exists
        if translated_summary and doc_language != 'en':
            response_data['summary'][doc_language] = translated_summary

        return jsonify({
            'status': 'success',
            'message': 'Summary generated',
            'data': response_data
        }), 200

    except Exception as e:
        logger.error(f"Summarization error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Summarization failed: {str(e)}'
        }), 500


@documents_bp.route('/<doc_id>/extract-keywords', methods=['POST', 'OPTIONS'])
@cross_origin()
@jwt_required()
def extract_keywords(doc_id):
    """Extract keywords from a document"""
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        user_id = get_jwt_identity()

        # Find the document
        document = current_app.db.documents.find_one({
            '_id': ObjectId(doc_id),
            'user_id': user_id
        })

        if not document:
            return jsonify({
                'status': 'error',
                'message': 'Document not found'
            }), 404

        # Perform Keyword Extraction
        start_time = time.time()
        from app.services.keyword_extraction import keyword_extraction_service
        from app.services.translation import translation_service
        
        # Get the document text and language
        text = document.get('clean_text') or document.get('raw_text') or ""
        doc_language = document.get('language', 'en')
        
        if not text:
            return jsonify({
                'status': 'error',
                'message': 'No text available for keyword extraction'
            }), 400
        
        # Skip translation if language is None or unknown
        if not doc_language or doc_language == 'unknown':
            doc_language = 'en'
        
        logger.info(f"Document language detected as: {doc_language}")
        
        # Step 1: Translate to English for better keyword extraction
        english_text = text
        if doc_language != 'en':
            try:
                logger.info(f"Translating document from {doc_language} to English for keyword extraction")
                result = translation_service.translate_to_english(text, source_language=doc_language)
                
                # Handle case where translate_to_english returns a dict
                if isinstance(result, dict):
                    english_text = result.get('translated_text', text)
                else:
                    english_text = result
                
                # Ensure we have a string
                if not isinstance(english_text, str):
                    english_text = str(english_text)
                    
                logger.info(f"Translated text preview: {english_text[:100]}...")
            except Exception as e:
                logger.warning(f"Translation to English failed: {str(e)}, using original text")
                english_text = text
        else:
            # Language is marked as English, but let's verify by checking the text
            if any(ord(char) > 127 for char in text[:200]):
                logger.warning(f"Document marked as English but contains non-ASCII characters. Attempting auto-translation.")
                try:
                    result = translation_service.translate_to_english(text, source_language='auto')
                    if isinstance(result, dict):
                        english_text = result.get('translated_text', text)
                        detected_lang = result.get('original_language', 'unknown')
                        logger.info(f"Auto-detected language: {detected_lang}")
                        # Update doc_language with the detected language for back-translation
                        if detected_lang and detected_lang != 'auto' and detected_lang != 'unknown':
                            doc_language = detected_lang
                    else:
                        english_text = result
                except Exception as e:
                    logger.warning(f"Auto-translation failed: {str(e)}")
        
        # Step 2: Extract keywords from English text
        keywords = keyword_extraction_service.extract(english_text, method="rake", top_n=15)
        time_taken = time.time() - start_time

        # Format English keywords with scores (RAKE returns ranked phrases)
        keyword_data_en = []
        for idx, keyword in enumerate(keywords):
            # RAKE returns phrases in descending order of importance
            # Calculate a relevance score based on position (higher = more relevant)
            relevance = round((len(keywords) - idx) / len(keywords) * 100, 1) if keywords else 0
            keyword_data_en.append({
                'text': keyword,
                'score': relevance,
                'rank': idx + 1
            })

        # Step 3: Translate keywords back to original language if not English
        keyword_data_translated = None
        if doc_language != 'en' and keywords:
            try:
                logger.info(f"Translating keywords from English to {doc_language}")
                translated_keywords = []
                
                for idx, keyword in enumerate(keywords):
                    try:
                        # Translate each keyword individually
                        translated_keyword = translation_service.translate_text(keyword, doc_language, 'en')
                        relevance = round((len(keywords) - idx) / len(keywords) * 100, 1) if keywords else 0
                        translated_keywords.append({
                            'text': translated_keyword,
                            'score': relevance,
                            'rank': idx + 1
                        })
                    except Exception as e:
                        logger.warning(f"Failed to translate keyword '{keyword}': {str(e)}")
                        # Keep the English version if translation fails
                        relevance = round((len(keywords) - idx) / len(keywords) * 100, 1) if keywords else 0
                        translated_keywords.append({
                            'text': keyword,
                            'score': relevance,
                            'rank': idx + 1
                        })
                
                keyword_data_translated = translated_keywords
                logger.info(f"Successfully translated {len(translated_keywords)} keywords to {doc_language}")
            except Exception as e:
                logger.warning(f"Failed to translate keywords to {doc_language}: {str(e)}")
                keyword_data_translated = None

        # Update Document with keywords
        current_app.db.documents.update_one(
            {'_id': ObjectId(doc_id)},
            {'$set': {
                'keywords': keyword_data_en,
                'metadata.keywords_extracted_at': datetime.utcnow()
            }}
        )

        # Prepare response with both English and translated keywords
        response_data = {
            'keywords': {
                'en': keyword_data_en
            },
            'stats': {
                'time_taken': round(time_taken, 3),
                'total_keywords': len(keyword_data_en)
            }
        }
        
        # Only include translated keywords if they exist
        if keyword_data_translated and doc_language != 'en':
            response_data['keywords'][doc_language] = keyword_data_translated

        return jsonify({
            'status': 'success',
            'message': 'Keywords extracted in both English and original language',
            'data': response_data
        }), 200

    except Exception as e:
        logger.error(f"Keyword extraction error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Keyword extraction failed: {str(e)}'
        }), 500
