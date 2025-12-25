"""
Documents Routes - Refactored for Multilingual Pipeline Integration
Handles document upload with automated processing through all services
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
import time
import logging
from bson import ObjectId

# Import models
from app.models.document import Document

from app.services.location_extraction import location_extraction_service
from app.services.pipeline import process_document_pipeline

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

        logger.info(f"Document created: {doc_id}, starting pipeline...")

        # Process through pipeline
        pipeline_result = process_document_pipeline(current_app.db, doc_id, raw_text)

        if pipeline_result['success']:
            return jsonify({
                'status': 'success',
                'message': 'Document uploaded and processed successfully',
                'data': {
                    'document_id': doc_id,
                    'filename': filename,
                    'file_type': file_type,
                    'processing_time': round(pipeline_result['processing_time'], 2),
                    'analysis': {
                        'language': pipeline_result['language'],
                        'sentiment': pipeline_result['sentiment'],
                        'event_type': pipeline_result['event_type'],
                        'locations_found': pipeline_result['locations_count']
                    }
                }
            }), 201
        else:
            return jsonify({
                'status': 'partial',
                'message': 'Document uploaded but processing failed',
                'data': {
                    'document_id': doc_id,
                    'error': pipeline_result.get('error')
                }
            }), 201

    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
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

        logger.info(f"Text document created: {doc_id}, starting pipeline...")

        # Process through pipeline
        pipeline_result = process_document_pipeline(current_app.db, doc_id, raw_text)

        if pipeline_result['success']:
            return jsonify({
                'status': 'success',
                'message': 'Text processed successfully',
                'data': {
                    'document_id': doc_id,
                    'processing_time': round(pipeline_result['processing_time'], 2),
                    'analysis': {
                        'language': pipeline_result['language'],
                        'sentiment': pipeline_result['sentiment'],
                        'event_type': pipeline_result['event_type'],
                        'locations_found': pipeline_result['locations_count']
                    }
                }
            }), 201
        else:
            return jsonify({
                'status': 'partial',
                'message': 'Text uploaded but processing failed',
                'data': {
                    'document_id': doc_id,
                    'error': pipeline_result.get('error')
                }
            }), 201

    except Exception as e:
        logger.error(f"Text upload error: {str(e)}")
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

                # Process pipeline
                pipeline_result = process_document_pipeline(current_app.db, doc_id, raw_text)

                if pipeline_result['success']:
                    results.append({
                        'index': idx,
                        'status': 'success',
                        'document_id': doc_id,
                        'language': pipeline_result['language'],
                        'sentiment': pipeline_result['sentiment'],
                        'event_type': pipeline_result['event_type']
                    })
                else:
                    results.append({
                        'index': idx,
                        'status': 'partial',
                        'document_id': doc_id,
                        'error': pipeline_result.get('error')
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

        return jsonify({
            'status': 'success',
            'message': 'Document retrieved successfully',
            'data': {
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
