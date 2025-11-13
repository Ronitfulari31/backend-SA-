# app/routes/documents.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
from app.models.document import Document
import logging
from rake_nltk import Rake
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer


logger = logging.getLogger(__name__)
documents_bp = Blueprint('documents', __name__)

ALLOWED_EXTENSIONS = {'csv', 'txt', 'pdf', 'docx', 'json', 'md', 'rtf'}


def extract_text(file_path, file_type):
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
    """Upload a document (CSV, TXT, PDF, DOCX, JSON, Markdown, RTF)"""
    try:
        if current_app.db is None:
            return jsonify({
                'error': 'Database not available',
                'message': 'MongoDB connection failed'
            }), 500

        if 'file' not in request.files:
            return jsonify({
                'error': 'No file provided',
                'message': 'Please upload a file'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'error': 'No file selected',
                'message': 'Please select a file'
            }), 400

        filename = secure_filename(file.filename)
        file_type = filename.split('.')[-1].lower()

        if file_type not in ALLOWED_EXTENSIONS:
            return jsonify({
                'error': 'File type not allowed',
                'message': f'Files of type .{file_type} are not supported for text extraction'
            }), 400

        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)

        # Get user ID securely from JWT
        user_id = get_jwt_identity()  # Will be a string (ObjectId) from your JWT

        # Extract text content for indexing/analysis
        content = extract_text(file_path, file_type)

        doc_id = Document.create(
            current_app.db,
            user_id=user_id,
            filename=filename,
            file_path=file_path,
            file_type=file_type,
            content=content
        )

        return jsonify({
            'message': 'Document uploaded successfully',
            'data': {
                'document_id': doc_id,
                'filename': filename,
                'file_type': file_type
            },
            'status': 'success'
        }), 201

    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({
            'error': 'Upload failed',
            'message': f'An error occurred during upload: {str(e)}'
        }), 500


@documents_bp.route('/list', methods=['GET'])
@jwt_required()
def list_documents():
    """List all documents for the logged-in user"""
    try:
        if current_app.db is None:
            return jsonify({
                'error': 'Database not available',
                'message': 'MongoDB connection failed'
            }), 500

        user_id = get_jwt_identity()

        # Get all documents for the user
        documents = current_app.db.documents.find({'user_id': user_id}).sort('uploaded_at', -1)

        docs_list = []
        for doc in documents:
            docs_list.append({
                'document_id': str(doc['_id']),
                'filename': doc['filename'],
                'file_type': doc['file_type'],
                'uploaded_at': str(doc.get('uploaded_at', '')),
                'processed': doc.get('processed', False),
                'content_preview': doc.get('content', '')[:200] + '...' if doc.get('content') else 'No content'
            })

        return jsonify({
            'message': 'Documents retrieved successfully',
            'data': {
                'documents': docs_list,
                'total': len(docs_list)
            },
            'status': 'success'
        }), 200

    except Exception as e:
        logger.error(f"List documents error: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve documents',
            'message': f'An error occurred: {str(e)}'
        }), 500


@documents_bp.route('/<doc_id>', methods=['GET'])
@jwt_required()
def get_document(doc_id):
    """Get a single document with its content"""
    try:
        if current_app.db is None:
            return jsonify({
                'error': 'Database not available',
                'message': 'MongoDB connection failed'
            }), 500

        from bson import ObjectId

        user_id = get_jwt_identity()

        # Find the document
        document = current_app.db.documents.find_one({
            '_id': ObjectId(doc_id),
            'user_id': user_id
        })

        if not document:
            return jsonify({
                'error': 'Document not found',
                'message': 'The requested document does not exist or you do not have access'
            }), 404

        return jsonify({
            'message': 'Document retrieved successfully',
            'data': {
                'document': {
                    'document_id': str(document['_id']),
                    'filename': document['filename'],
                    'file_type': document['file_type'],
                    'uploaded_at': str(document.get('uploaded_at', '')),
                    'processed': document.get('processed', False),
                    'content': document.get('content', ''),
                    'file_path': document.get('file_path', '')
                }
            },
            'status': 'success'
        }), 200

    except Exception as e:
        logger.error(f"Get document error: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve document',
            'message': f'An error occurred: {str(e)}'
        }), 500


@documents_bp.route('/<doc_id>', methods=['DELETE'])
@jwt_required()
def delete_document(doc_id):
    """Delete a document"""
    try:
        if current_app.db is None:
            return jsonify({
                'error': 'Database not available',
                'message': 'MongoDB connection failed'
            }), 500

        from bson import ObjectId
        import os

        user_id = get_jwt_identity()

        # Find the document
        document = current_app.db.documents.find_one({
            '_id': ObjectId(doc_id),
            'user_id': user_id
        })

        if not document:
            return jsonify({
                'error': 'Document not found',
                'message': 'The requested document does not exist or you do not have access'
            }), 404

        # Delete the file from disk
        try:
            if os.path.exists(document['file_path']):
                os.remove(document['file_path'])
        except Exception as e:
            logger.warning(f"Could not delete file: {e}")

        # Delete from database
        current_app.db.documents.delete_one({'_id': ObjectId(doc_id)})

        return jsonify({
            'message': 'Document deleted successfully',
            'data': {
                'document_id': doc_id
            },
            'status': 'success'
        }), 200

    except Exception as e:
        logger.error(f"Delete document error: {str(e)}")
        return jsonify({
            'error': 'Failed to delete document',
            'message': f'An error occurred: {str(e)}'
        }), 500


@documents_bp.route('/<doc_id>/sentiment', methods=['GET'])
@jwt_required()
def analyze_sentiment(doc_id):
    """Analyze sentiment of a document's content"""
    try:
        if current_app.db is None:
            return jsonify({
                'error': 'Database not available',
                'message': 'MongoDB connection failed'
            }), 500

        from bson import ObjectId
        from textblob import TextBlob

        user_id = get_jwt_identity()

        # Find the document
        document = current_app.db.documents.find_one({
            '_id': ObjectId(doc_id),
            'user_id': user_id
        })

        if not document:
            return jsonify({
                'error': 'Document not found',
                'message': 'The requested document does not exist or you do not have access'
            }), 404

        content = document.get('content', '')
        if not content:
            return jsonify({
                'error': 'No content',
                'message': 'Document has no text to analyze'
            }), 400

        # Analyze sentiment
        blob = TextBlob(content)
        polarity = blob.sentiment.polarity
        if polarity > 0:
            sentiment = 'positive'
        elif polarity < 0:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'

        return jsonify({
            'message': 'Sentiment analysis completed',
            'data': {
                'document_id': doc_id,
                'sentiment': sentiment,
                'polarity': polarity,
                'content_preview': content[:200] + '...'
            },
            'status': 'success'
        }), 200

    

    except Exception as e:
        logger.error(f"Sentiment analysis error: {str(e)}")
        return jsonify({
            'error': 'Sentiment analysis failed',
            'message': f'An error occurred: {str(e)}'
        }), 500


@documents_bp.route('/<doc_id>/keywords', methods=['GET'])
@jwt_required()
def extract_keywords(doc_id):
    """Extract keywords from a document's content"""
    try:
        if current_app.db is None:
            return jsonify({
                'error': 'Database not available',
                'message': 'MongoDB connection failed'
            }), 500

        from bson import ObjectId

        user_id = get_jwt_identity()

        # Find the document
        document = current_app.db.documents.find_one({
            '_id': ObjectId(doc_id),
            'user_id': user_id
        })

        if not document:
            return jsonify({
                'error': 'Document not found',
                'message': 'The requested document does not exist or you do not have access'
            }), 404

        content = document.get('content', '')
        if not content:
            return jsonify({
                'error': 'No content',
                'message': 'Document has no text to analyze'
            }), 400

        # Extract keywords
        r = Rake()
        r.extract_keywords_from_text(content)
        keywords = r.get_ranked_phrases()

        return jsonify({
            'message': 'Keywords extracted successfully',
            'data': {
                'document_id': doc_id,
                'keywords': keywords[:10],  # Top 10 keywords
                'content_preview': content[:200] + '...'
            },
            'status': 'success'
        }), 200

    except Exception as e:
        logger.error(f"Keyword extraction error: {str(e)}")
        return jsonify({
            'error': 'Keyword extraction failed',
            'message': f'An error occurred: {str(e)}'
        }), 500

from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer

@documents_bp.route('/<doc_id>/summarize', methods=['GET'])
@jwt_required()
def summarize_document(doc_id):
    """Summarize a document's content"""
    try:
        if current_app.db is None:
            return jsonify({
                'error': 'Database not available',
                'message': 'MongoDB connection failed'
            }), 500

        from bson import ObjectId

        user_id = get_jwt_identity()

        # Find the document
        document = current_app.db.documents.find_one({
            '_id': ObjectId(doc_id),
            'user_id': user_id
        })

        if not document:
            return jsonify({
                'error': 'Document not found',
                'message': 'The requested document does not exist or you do not have access'
            }), 404

        content = document.get('content', '')
        if not content:
            return jsonify({
                'error': 'No content',
                'message': 'Document has no text to analyze'
            }), 400

        # Summarize
        parser = PlaintextParser.from_string(content, Tokenizer("english"))
        summarizer = LsaSummarizer()
        summary_sentences = summarizer(parser.document, sentences_count=3)
        summary = " ".join([str(sentence) for sentence in summary_sentences])

        return jsonify({
            'message': 'Document summarized successfully',
            'data': {
                'document_id': doc_id,
                'summary': summary,
                'content_preview': content[:200] + '...'
            },
            'status': 'success'
        }), 200

    except Exception as e:
        logger.error(f"Summarization error: {str(e)}")
        return jsonify({
            'error': 'Summarization failed',
            'message': f'An error occurred: {str(e)}'
        }), 500
