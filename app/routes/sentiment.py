from flask import Blueprint, request, jsonify
from bson import ObjectId
from app.database import db
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import logging

# Initialize Blueprint
sentiment_bp = Blueprint('sentiment', __name__, url_prefix='/api/documents')

# Initialize VADER Sentiment Analyzer
analyzer = SentimentIntensityAnalyzer()

# Setup logging
logger = logging.getLogger(__name__)


@sentiment_bp.route('/<document_id>/nlp/sentiment', methods=['GET'])
def analyze_sentiment(document_id):
    """
    Analyze sentiment of document content using TextBlob and VADER
    
    GET /api/documents/<document_id>/sentiment
    
    Returns:
        - polarity: -1 to 1 (TextBlob)
        - subjectivity: 0 to 1 (TextBlob)
        - sentiment_label: Positive/Negative/Neutral
        - vader_scores: Detailed VADER sentiment breakdown
    """
    try:
        # Validate document ID
        if not ObjectId.is_valid(document_id):
            return jsonify({
                'status': 'error',
                'message': 'Invalid document ID format'
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
        
        # TextBlob Sentiment Analysis
        blob = TextBlob(content)
        polarity = blob.sentiment.polarity  # Range: -1 to 1
        subjectivity = blob.sentiment.subjectivity  # Range: 0 to 1
        
        # VADER Sentiment Analysis (more advanced)
        vader_scores = analyzer.polarity_scores(content)
        
        # Determine sentiment label based on polarity
        if polarity > 0.1:
            sentiment_label = 'Positive'
            sentiment_color = 'green'
        elif polarity < -0.1:
            sentiment_label = 'Negative'
            sentiment_color = 'red'
        else:
            sentiment_label = 'Neutral'
            sentiment_color = 'gray'
        
        # Calculate word count and sentence count
        word_count = len(content.split())
        sentence_count = len(blob.sentences)
        
        return jsonify({
            'status': 'success',
            'message': 'Sentiment analysis completed successfully',
            'data': {
                'document_id': str(document_id),
                'title': document.get('title', 'Untitled'),
                'textblob_analysis': {
                    'polarity': round(polarity, 3),
                    'subjectivity': round(subjectivity, 3),
                    'sentiment': sentiment_label,
                    'color': sentiment_color
                },
                'vader_analysis': {
                    'positive': round(vader_scores['pos'], 3),
                    'negative': round(vader_scores['neg'], 3),
                    'neutral': round(vader_scores['neu'], 3),
                    'compound': round(vader_scores['compound'], 3),
                    'interpretation': _interpret_compound_score(vader_scores['compound'])
                },
                'content_stats': {
                    'word_count': word_count,
                    'sentence_count': len(blob.sentences),
                    'character_count': len(content)
                },
                'content_preview': content[:300] + '...' if len(content) > 300 else content
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error analyzing sentiment for document {document_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'An error occurred during sentiment analysis',
            'error': str(e)
        }), 500


@sentiment_bp.route('/documents/<document_id>/sentiment/summary', methods=['GET'])
def get_sentiment_summary(document_id):
    """
    Get a brief sentiment summary with key insights
    
    GET /api/documents/<document_id>/sentiment/summary
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
        
        content = document.get('content', '')
        
        if not content or len(content.strip()) == 0:
            return jsonify({
                'status': 'error',
                'message': 'Document content is empty'
            }), 400
        
        blob = TextBlob(content)
        vader_scores = analyzer.polarity_scores(content)
        
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        # Generate summary insights
        insights = []
        
        if vader_scores['compound'] > 0.5:
            insights.append("This document expresses strong positive sentiment")
        elif vader_scores['compound'] > 0.05:
            insights.append("This document has a positive tone overall")
        elif vader_scores['compound'] < -0.5:
            insights.append("This document expresses strong negative sentiment")
        elif vader_scores['compound'] < -0.05:
            insights.append("This document has a negative tone overall")
        else:
            insights.append("This document is mostly neutral in sentiment")
        
        if subjectivity > 0.6:
            insights.append("The content is highly subjective and opinion-based")
        elif subjectivity < 0.4:
            insights.append("The content is mostly objective and factual")
        else:
            insights.append("The content has a mix of objective and subjective elements")
        
        return jsonify({
            'status': 'success',
            'message': 'Sentiment summary generated',
            'data': {
                'document_id': str(document_id),
                'overall_sentiment': _get_sentiment_label(polarity),
                'polarity_score': round(polarity, 3),
                'subjectivity_score': round(subjectivity, 3),
                'vader_compound': round(vader_scores['compound'], 3),
                'insights': insights,
                'confidence': _calculate_confidence(vader_scores)
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error generating sentiment summary for {document_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'An error occurred',
            'error': str(e)
        }), 500


def _interpret_compound_score(compound):
    """
    Interpret VADER compound score
    compound >= 0.05 : positive
    compound <= -0.05 : negative
    -0.05 < compound < 0.05 : neutral
    """
    if compound >= 0.05:
        return "Positive"
    elif compound <= -0.05:
        return "Negative"
    else:
        return "Neutral"


def _get_sentiment_label(polarity):
    """Get sentiment label based on polarity score"""
    if polarity > 0.1:
        return "Positive"
    elif polarity < -0.1:
        return "Negative"
    else:
        return "Neutral"


def _calculate_confidence(vader_scores):
    """
    Calculate confidence score based on how dominant
    the sentiment is compared to others
    """
    max_score = max(vader_scores['pos'], vader_scores['neg'], vader_scores['neu'])
    return round(max_score * 100, 2)