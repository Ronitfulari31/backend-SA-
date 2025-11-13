from flask import Blueprint, request, jsonify
from bson import ObjectId
from app.database import db
from rake_nltk import Rake
import yake
import logging

# Initialize Blueprint
keyword_bp = Blueprint('keywords', __name__, url_prefix='/api/documents')

# Setup logging
logger = logging.getLogger(__name__)


@keyword_bp.route('/<document_id>/nlp/keywords', methods=['POST'])
def extract_keywords(document_id):
    """
    Extract keywords using RAKE (Rapid Automatic Keyword Extraction)
    
    POST /api/documents/<document_id>/keywords
    Request Body:
    {
        "method": "rake",  # Keyword extraction method: "rake" or "yake" (default: "rake")
        "top_n": 10        # Number of top keywords to return (default: 10)
    }
    
    Returns:
        - keywords: List of extracted keywords with scores
        - top_keywords: Top N keywords
        - total_keywords: Total unique keywords found
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
        method = data.get('method', 'rake').lower()
        top_n = data.get('top_n', 10)
        
        # Validate inputs
        if method not in ['rake', 'yake']:
            return jsonify({
                'status': 'error',
                'message': 'method must be either "rake" or "yake"'
            }), 400
        
        if not isinstance(top_n, int) or top_n <= 0:
            return jsonify({
                'status': 'error',
                'message': 'top_n must be a positive integer'
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
        
        # Extract keywords based on method
        if method == 'rake':
            keywords_data = _extract_rake_keywords(content, top_n)
        else:  # yake
            keywords_data = _extract_yake_keywords(content, top_n)
        
        return jsonify({
            'status': 'success',
            'message': 'Keywords extracted successfully',
            'data': {
                'document_id': str(document_id),
                'title': document.get('title', 'Untitled'),
                'method': method.upper(),
                'content_preview': content[:300] + '...' if len(content) > 300 else content,
                'keywords': keywords_data['all_keywords'],
                'top_keywords': keywords_data['top_keywords'],
                'statistics': {
                    'total_keywords': keywords_data['total'],
                    'top_n_displayed': top_n,
                    'word_count': len(content.split())
                }
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error extracting keywords from document {document_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'An error occurred during keyword extraction',
            'error': str(e)
        }), 500


@keyword_bp.route('/<document_id>/nlp/keywords-compare', methods=['POST'])
def compare_keyword_methods(document_id):
    """
    Compare RAKE and YAKE keyword extraction methods
    
    POST /api/documents/<document_id>/keywords-compare
    Request Body:
    {
        "top_n": 10  # Number of top keywords (default: 10)
    }
    """
    try:
        if not ObjectId.is_valid(document_id):
            return jsonify({
                'status': 'error',
                'message': 'Invalid document ID format'
            }), 400
        
        data = request.get_json() or {}
        top_n = data.get('top_n', 10)
        
        if not isinstance(top_n, int) or top_n <= 0:
            return jsonify({
                'status': 'error',
                'message': 'top_n must be a positive integer'
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
            # Extract with RAKE
            rake_data = _extract_rake_keywords(content, top_n)
            
            # Extract with YAKE
            yake_data = _extract_yake_keywords(content, top_n)
            
            # Find common keywords
            rake_keywords_set = set([kw['keyword'] for kw in rake_data['top_keywords']])
            yake_keywords_set = set([kw['keyword'] for kw in yake_data['top_keywords']])
            common_keywords = list(rake_keywords_set.intersection(yake_keywords_set))
            
            return jsonify({
                'status': 'success',
                'message': 'Keyword extraction comparison completed',
                'data': {
                    'document_id': str(document_id),
                    'title': document.get('title', 'Untitled'),
                    'rake': {
                        'method': 'RAKE (Rapid Automatic Keyword Extraction)',
                        'total_keywords': rake_data['total'],
                        'top_keywords': rake_data['top_keywords']
                    },
                    'yake': {
                        'method': 'YAKE (Yet Another Keyword Extractor)',
                        'total_keywords': yake_data['total'],
                        'top_keywords': yake_data['top_keywords']
                    },
                    'comparison': {
                        'common_keywords': common_keywords,
                        'common_count': len(common_keywords),
                        'only_in_rake': [kw for kw in rake_keywords_set - yake_keywords_set],
                        'only_in_yake': [kw for kw in yake_keywords_set - rake_keywords_set]
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
        logger.error(f"Error comparing keyword methods: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'An error occurred',
            'error': str(e)
        }), 500


def _extract_rake_keywords(content, top_n):
    """
    Extract keywords using RAKE algorithm
    """
    try:
        rake = Rake(language='english')
        rake.extract_keywords_from_text(content)
        
        # Get ranked keywords
        keywords_ranked = rake.get_ranked_phrases_with_scores()
        
        all_keywords = [
            {
                'keyword': keyword,
                'score': round(score, 4)
            }
            for score, keyword in keywords_ranked
        ]
        
        top_keywords = all_keywords[:top_n]
        
        return {
            'all_keywords': all_keywords,
            'top_keywords': top_keywords,
            'total': len(all_keywords)
        }
    except Exception as e:
        logger.error(f"RAKE extraction error: {str(e)}")
        raise


def _extract_yake_keywords(content, top_n):
    """
    Extract keywords using YAKE algorithm
    """
    try:
        # Initialize YAKE keyword extractor
        kw_extractor = yake.KeywordExtractor(
            lan="en",
            n=3,  # Max ngram size
            top=len(content.split()),  # Extract all keywords
            features=None
        )
        
        keywords_extracted = kw_extractor.extract_keywords(content)
        
        all_keywords = [
            {
                'keyword': keyword,
                'score': round(score, 4)
            }
            for keyword, score in keywords_extracted
        ]
        
        # Sort by score (lower is better for YAKE)
        all_keywords.sort(key=lambda x: x['score'])
        
        top_keywords = all_keywords[:top_n]
        
        return {
            'all_keywords': all_keywords,
            'top_keywords': top_keywords,
            'total': len(all_keywords)
        }
    except Exception as e:
        logger.error(f"YAKE extraction error: {str(e)}")
        raise


@keyword_bp.route('<document_id>/nlp/keywords-frequency', methods=['GET'])
def get_keyword_frequency(document_id):
    """
    Get keyword frequency statistics
    
    GET /api/documents/<document_id>/keywords-frequency
    """
    try:
        if not ObjectId.is_valid(document_id):
            return jsonify({
                'status': 'error',
                'message': 'Invalid document ID format'
            }), 400
        
        document = db.documents.find_one({'_id': ObjectId(document_id)})
        
        if not document:
            return jsonify({
                'status': 'error',
                'message': 'Document not found'
            }), 404
        
        content = document.get('content', '').lower()
        
        if not content or len(content.strip()) == 0:
            return jsonify({
                'status': 'error',
                'message': 'Document content is empty'
            }), 400
        
        # Split into words and count frequency
        words = content.split()
        word_freq = {}
        
        for word in words:
            # Remove punctuation
            word = ''.join(char for char in word if char.isalnum())
            if len(word) > 3:  # Only words longer than 3 characters
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        return jsonify({
            'status': 'success',
            'message': 'Keyword frequency statistics retrieved',
            'data': {
                'document_id': str(document_id),
                'title': document.get('title', 'Untitled'),
                'total_unique_words': len(word_freq),
                'top_20_words': [
                    {'word': word, 'frequency': freq}
                    for word, freq in sorted_words[:20]
                ],
                'word_statistics': {
                    'total_words': len(words),
                    'average_frequency': round(sum(word_freq.values()) / len(word_freq), 2) if word_freq else 0,
                    'max_frequency': max(word_freq.values()) if word_freq else 0
                }
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting keyword frequency: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'An error occurred',
            'error': str(e)
        }), 500