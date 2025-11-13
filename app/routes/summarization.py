from flask import Blueprint, request, jsonify
from bson import ObjectId
from app.database import db
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.summarizers.luhn import LuhnSummarizer
import logging

# Initialize Blueprint
summarization_bp = Blueprint('summarization', __name__, url_prefix='/api/documents')

# Setup logging
logger = logging.getLogger(__name__)


@summarization_bp.route('/<document_id>/nlp/summarize', methods=['POST'])
def summarize_document(document_id):
    """
    Summarize document content using extractive summarization
    
    POST /api/documents/<document_id>/summarize
    Request Body:
    {
        "sentences_count": 3,  # Number of sentences in summary (default: 3)
        "method": "lsa"        # Summarization method: "lsa" or "luhn" (default: "lsa")
    }
    
    Returns:
        - original_text: Original document content
        - summary: Summarized text
        - original_sentences: Total sentences in original
        - summary_sentences: Number of sentences in summary
        - compression_ratio: Percentage of original content in summary
    """
    try:
        # Validate document ID
        if not ObjectId.is_valid(document_id):
            return jsonify({
                'status': 'error',
                'message': 'Invalid document ID format'
            }), 400
        
        # Get request data
        data = request.get_json() or {}
        sentences_count = data.get('sentences_count', 3)
        method = data.get('method', 'lsa').lower()
        
        # Validate inputs
        if not isinstance(sentences_count, int) or sentences_count <= 0:
            return jsonify({
                'status': 'error',
                'message': 'sentences_count must be a positive integer'
            }), 400
        
        if method not in ['lsa', 'luhn']:
            return jsonify({
                'status': 'error',
                'message': 'method must be either "lsa" or "luhn"'
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
        
        # Parse and summarize
        try:
            tokenizer = Tokenizer("english")
            parser = PlaintextParser.from_string(content, tokenizer)
            
            # Choose summarization method
            if method == 'lsa':
                summarizer = LsaSummarizer()
            else:  # luhn
                summarizer = LuhnSummarizer()
            
            # Generate summary
            summary_sentences = summarizer(parser.document, sentences_count)
            summary_text = '\n'.join([str(sentence) for sentence in summary_sentences])
            
            # Calculate statistics
            total_sentences = len(parser.document.sentences)
            summary_sentence_count = len(summary_sentences)
            
            # Prevent division by zero
            if total_sentences > 0:
                compression_ratio = round((len(summary_text) / len(content)) * 100, 2)
            else:
                compression_ratio = 0
            
            return jsonify({
                'status': 'success',
                'message': 'Document summarized successfully',
                'data': {
                    'document_id': str(document_id),
                    'title': document.get('title', 'Untitled'),
                    'method': method.upper(),
                    'original_text': content[:300] + '...' if len(content) > 300 else content,
                    'summary': summary_text,
                    'statistics': {
                        'original_length': len(content),
                        'summary_length': len(summary_text),
                        'original_sentences': total_sentences,
                        'summary_sentences': summary_sentence_count,
                        'compression_ratio': f"{compression_ratio}%"
                    }
                }
            }), 200
        
        except Exception as e:
            logger.error(f"Summarization error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Summarization failed',
                'error': str(e)
            }), 500
    
    except Exception as e:
        logger.error(f"Error summarizing document {document_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'An error occurred during summarization',
            'error': str(e)
        }), 500


@summarization_bp.route('/<document_id>/nlp/summarize-adaptive', methods=['POST'])
def summarize_adaptive(document_id):
    """
    Adaptive summarization - automatically choose summary length based on content
    
    POST /api/documents/<document_id>/summarize-adaptive
    Request Body:
    {
        "compression_ratio": 0.3  # Optional: desired compression ratio (0.0-1.0)
    }
    """
    try:
        if not ObjectId.is_valid(document_id):
            return jsonify({
                'status': 'error',
                'message': 'Invalid document ID format'
            }), 400
        
        data = request.get_json() or {}
        compression_ratio = data.get('compression_ratio', 0.3)
        
        # Validate compression ratio
        if not isinstance(compression_ratio, (int, float)) or compression_ratio <= 0 or compression_ratio > 1:
            return jsonify({
                'status': 'error',
                'message': 'compression_ratio must be between 0 and 1'
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
        
        try:
            tokenizer = Tokenizer("english")
            parser = PlaintextParser.from_string(content, tokenizer)
            
            # Calculate adaptive sentence count
            total_sentences = len(parser.document.sentences)
            sentences_to_keep = max(1, int(total_sentences * compression_ratio))
            
            # Create summary
            summarizer = LsaSummarizer()
            summary_sentences = summarizer(parser.document, sentences_to_keep)
            summary_text = '\n'.join([str(sentence) for sentence in summary_sentences])
            
            actual_compression = round((len(summary_text) / len(content)) * 100, 2)
            
            return jsonify({
                'status': 'success',
                'message': 'Adaptive summarization completed',
                'data': {
                    'document_id': str(document_id),
                    'title': document.get('title', 'Untitled'),
                    'summary': summary_text,
                    'statistics': {
                        'original_sentences': total_sentences,
                        'summary_sentences': sentences_to_keep,
                        'requested_compression_ratio': f"{compression_ratio*100}%",
                        'actual_compression_ratio': f"{actual_compression}%"
                    }
                }
            }), 200
        
        except Exception as e:
            logger.error(f"Adaptive summarization error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Adaptive summarization failed',
                'error': str(e)
            }), 500
    
    except Exception as e:
        logger.error(f"Error in adaptive summarization: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'An error occurred',
            'error': str(e)
        }), 500


@summarization_bp.route('<document_id>/nlp/summarize-compare', methods=['POST'])
def compare_summaries(document_id):
    """
    Compare LSA and Luhn summarization methods
    
    POST /api/documents/<document_id>/summarize-compare
    Request Body:
    {
        "sentences_count": 3
    }
    """
    try:
        if not ObjectId.is_valid(document_id):
            return jsonify({
                'status': 'error',
                'message': 'Invalid document ID format'
            }), 400
        
        data = request.get_json() or {}
        sentences_count = data.get('sentences_count', 3)
        
        if not isinstance(sentences_count, int) or sentences_count <= 0:
            return jsonify({
                'status': 'error',
                'message': 'sentences_count must be a positive integer'
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
        
        try:
            tokenizer = Tokenizer("english")
            parser = PlaintextParser.from_string(content, tokenizer)
            
            # LSA Summarization
            lsa_summarizer = LsaSummarizer()
            lsa_summary = lsa_summarizer(parser.document, sentences_count)
            lsa_text = '\n'.join([str(sentence) for sentence in lsa_summary])
            
            # Luhn Summarization
            luhn_summarizer = LuhnSummarizer()
            luhn_summary = luhn_summarizer(parser.document, sentences_count)
            luhn_text = '\n'.join([str(sentence) for sentence in luhn_summary])
            
            return jsonify({
                'status': 'success',
                'message': 'Comparison completed',
                'data': {
                    'document_id': str(document_id),
                    'title': document.get('title', 'Untitled'),
                    'lsa_summary': {
                        'method': 'LSA (Latent Semantic Analysis)',
                        'summary': lsa_text,
                        'length': len(lsa_text)
                    },
                    'luhn_summary': {
                        'method': 'Luhn Algorithm',
                        'summary': luhn_text,
                        'length': len(luhn_text)
                    },
                    'statistics': {
                        'original_length': len(content),
                        'lsa_compression': round((len(lsa_text) / len(content)) * 100, 2),
                        'luhn_compression': round((len(luhn_text) / len(content)) * 100, 2)
                    }
                }
            }), 200
        
        except Exception as e:
            logger.error(f"Comparison error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Comparison failed',
                'error': str(e)
            }), 500
    
    except Exception as e:
        logger.error(f"Error comparing summaries: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'An error occurred',
            'error': str(e)
        }), 500