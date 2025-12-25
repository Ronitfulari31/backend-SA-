"""
Evaluation Routes - Research Metrics & Model Evaluation
Handles cross-lingual consistency, ML metrics, and performance tracking
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging

from app.services.evaluation import evaluation_service

logger = logging.getLogger(__name__)
evaluation_bp = Blueprint('evaluation', __name__)


@evaluation_bp.route('/cross-lingual-consistency', methods=['GET'])
@jwt_required()
def check_cross_lingual_consistency():
    """
    RESEARCH CRITICAL 
    Check cross-lingual sentiment consistency
    
    Compares sentiment of original text vs translated text
    to measure if sentiment is preserved across translation
    
    Query params:
    - limit: Number of documents to check (default: 100)
    - document_ids: Comma-separated list of specific document IDs (optional)
    """
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        # Get query params
        limit = int(request.args.get('limit', 100))
        document_ids_str = request.args.get('document_ids', None)
        
        document_ids = None
        if document_ids_str:
            document_ids = document_ids_str.split(',')

        logger.info(f"Checking cross-lingual consistency for {limit} documents...")

        # Call evaluation service
        result = evaluation_service.check_cross_lingual_consistency(
            document_ids=document_ids,
            limit=limit
        )

        if 'error' in result:
            return jsonify({
                'status': 'error',
                'message': result['error']
            }), 500

        return jsonify({
            'status': 'success',
            'message': 'Cross-lingual consistency analysis complete',
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"Cross-lingual consistency check error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Analysis failed: {str(e)}'
        }), 500


@evaluation_bp.route('/ml-metrics', methods=['POST'])
@jwt_required()
def calculate_ml_metrics():
    """
    Calculate ML classification metrics
    
    Request body:
    {
        "y_true": ["positive", "negative", "neutral", ...],
        "y_pred": ["positive", "negative", "neutral", ...],
        "labels": ["positive", "negative", "neutral"]  // optional
    }
    
    Returns: accuracy, precision, recall, F1 score, confusion matrix
    """
    try:
        data = request.get_json()
        
        if not data or 'y_true' not in data or 'y_pred' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Both y_true and y_pred are required'
            }), 400

        y_true = data['y_true']
        y_pred = data['y_pred']
        labels = data.get('labels', None)

        # Calculate metrics
        result = evaluation_service.calculate_ml_metrics(y_true, y_pred, labels)

        if 'error' in result:
            return jsonify({
                'status': 'error',
                'message': result['error']
            }), 400

        return jsonify({
            'status': 'success',
            'message': 'ML metrics calculated successfully',
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"ML metrics calculation error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Calculation failed: {str(e)}'
        }), 500


@evaluation_bp.route('/performance-metrics', methods=['GET'])
@jwt_required()
def get_performance_metrics():
    """
    Get system performance metrics
    
    Returns average latencies and throughput for:
    - Translation
    - Sentiment analysis
    - NER
    - Total processing time
    
    Query params:
    - limit: Number of documents to analyze (default: 100)
    - document_ids: Comma-separated list of specific document IDs (optional)
    """
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        # Get query params
        limit = int(request.args.get('limit', 100))
        document_ids_str = request.args.get('document_ids', None)
        
        document_ids = None
        if document_ids_str:
            document_ids = document_ids_str.split(',')

        logger.info(f"Calculating performance metrics for {limit} documents...")

        # Call evaluation service
        result = evaluation_service.calculate_performance_metrics(
            document_ids=document_ids,
            limit=limit
        )

        if 'error' in result:
            return jsonify({
                'status': 'error',
                'message': result['error']
            }), 500

        return jsonify({
            'status': 'success',
            'message': 'Performance metrics calculated successfully',
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"Performance metrics error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Calculation failed: {str(e)}'
        }), 500


@evaluation_bp.route('/benchmark-sentiment-models', methods=['POST'])
@jwt_required()
def benchmark_sentiment_models():
    """
    Benchmark different sentiment analysis models
    
    Request body:
    {
        "test_texts": [
            "This is a positive statement",
            "This is terrible",
            "This is ok"
        ]
    }
    
    Returns: Comparison of BERTweet, VADER, and TextBlob
    """
    try:
        data = request.get_json()
        
        if not data or 'test_texts' not in data:
            return jsonify({
                'status': 'error',
                'message': 'test_texts array is required'
            }), 400

        test_texts = data['test_texts']
        
        if not isinstance(test_texts, list) or len(test_texts) == 0:
            return jsonify({
                'status': 'error',
                'message': 'test_texts must be a non-empty array'
            }), 400

        logger.info(f"Benchmarking sentiment models on {len(test_texts)} texts...")

        # Call evaluation service
        result = evaluation_service.benchmark_sentiment_models(test_texts)

        if 'error' in result:
            return jsonify({
                'status': 'error',
                'message': result['error']
            }), 500

        return jsonify({
            'status': 'success',
            'message': 'Model benchmarking complete',
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"Model benchmarking error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Benchmarking failed: {str(e)}'
        }), 500
