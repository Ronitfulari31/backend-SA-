"""
Dashboard Routes - Chart-Ready Analytics APIs
Provides aggregated data for post-disaster intelligence visualization
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import logging
from collections import Counter

logger = logging.getLogger(__name__)
dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/sentiment-distribution', methods=['GET'])
@jwt_required()
def get_sentiment_distribution():
    """
    Get sentiment distribution (chart-ready)
    
    Query params:
    - event_type: Filter by event type (optional)
    - source: Filter by source (optional)
    - start_date: Start date filter (optional, ISO format)
    - end_date: End date filter (optional, ISO format)
    
    Returns:
    {
        "positive": 120,
        "neutral": 60,
        "negative": 210
    }
    """
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        user_id = get_jwt_identity()

        # Build query
        query = {'user_id': user_id, 'processed': True}
        
        event_type = request.args.get('event_type')
        if event_type:
            query['event_type'] = event_type
        
        source = request.args.get('source')
        if source:
            query['source'] = source
        
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if start_date or end_date:
            query['timestamp'] = {}
            if start_date:
                query['timestamp']['$gte'] = datetime.fromisoformat(start_date)
            if end_date:
                query['timestamp']['$lte'] = datetime.fromisoformat(end_date)

        # Aggregate sentiment counts
        pipeline = [
            {'$match': query},
            {'$group': {
                '_id': '$sentiment.label',
                'count': {'$sum': 1}
            }}
        ]
        
        results = list(current_app.db.documents.aggregate(pipeline))
        
        # Format for chart
        sentiment_dist = {
            'positive': 0,
            'neutral': 0,
            'negative': 0
        }
        
        for result in results:
            sentiment = result['_id']
            if sentiment in sentiment_dist:
                sentiment_dist[sentiment] = result['count']

        return jsonify({
            'status': 'success',
            'message': 'Sentiment distribution retrieved',
            'data': sentiment_dist
        }), 200

    except Exception as e:
        logger.error(f"Sentiment distribution error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get sentiment distribution: {str(e)}'
        }), 500


@dashboard_bp.route('/sentiment-trend', methods=['GET'])
@jwt_required()
def get_sentiment_trend():
    """
    Get sentiment trend over time (chart-ready)
    
    Query params:
    - interval: hourly|daily|weekly (default: hourly)
    - event_type: Filter by event type (optional)
    - hours: Number of hours to look back (default: 24)
    
    Returns:
    [
        {"time": "2025-01-01T10:00", "positive": 20, "neutral": 15, "negative": 40},
        {"time": "2025-01-01T11:00", "positive": 25, "neutral": 10, "negative": 70}
    ]
    """
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        user_id = get_jwt_identity()
        
        interval = request.args.get('interval', 'hourly')
        event_type = request.args.get('event_type')
        hours = int(request.args.get('hours', 24))

        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        # Build query
        query = {
            'user_id': user_id,
            'processed': True,
            'timestamp': {'$gte': start_time, '$lte': end_time}
        }
        
        if event_type:
            query['event_type'] = event_type

        # Get documents
        documents = list(current_app.db.documents.find(query).sort('timestamp', 1))

        # Group by time interval
        trend_data = {}
        
        for doc in documents:
            timestamp = doc.get('timestamp')
            if not timestamp:
                continue
            
            # Round to interval
            if interval == 'hourly':
                time_key = timestamp.replace(minute=0, second=0, microsecond=0)
            elif interval == 'daily':
                time_key = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            else:  # weekly
                time_key = timestamp - timedelta(days=timestamp.weekday())
                time_key = time_key.replace(hour=0, minute=0, second=0, microsecond=0)
            
            time_str = time_key.isoformat()
            
            if time_str not in trend_data:
                trend_data[time_str] = {
                    'time': time_str,
                    'positive': 0,
                    'neutral': 0,
                    'negative': 0
                }
            
            sentiment = doc.get('sentiment', {}).get('label', 'neutral')
            if sentiment in ['positive', 'neutral', 'negative']:
                trend_data[time_str][sentiment] += 1

        # Convert to list and sort by time
        trend_list = sorted(trend_data.values(), key=lambda x: x['time'])

        return jsonify({
            'status': 'success',
            'message': 'Sentiment trend retrieved',
            'data': trend_list
        }), 200

    except Exception as e:
        logger.error(f"Sentiment trend error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get sentiment trend: {str(e)}'
        }), 500


@dashboard_bp.route('/keyword-cloud', methods=['GET'])
@jwt_required()
def get_keyword_cloud():
    """
    Get keyword cloud data (chart-ready)
    
    Query params:
    - top_n: Number of top keywords (default: 50)
    - event_type: Filter by event type (optional)
    - sentiment: Filter by sentiment (optional)
    
    Returns:
    ["flood", "water", "rescue", "help", "emergency", ...]
    """
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        user_id = get_jwt_identity()
        
        top_n = int(request.args.get('top_n', 50))
        event_type = request.args.get('event_type')
        sentiment = request.args.get('sentiment')

        # Build query
        query = {'user_id': user_id, 'processed': True}
        
        if event_type:
            query['event_type'] = event_type
        if sentiment:
            query['sentiment.label'] = sentiment

        # Get documents
        documents = list(current_app.db.documents.find(query, {'clean_text': 1}))

        # Extract keywords using simple word frequency
        from nltk.corpus import stopwords
        from nltk.tokenize import word_tokenize
        import nltk
        
        try:
            stopwords_set = set(stopwords.words('english'))
        except:
            # Download stopwords if not available
            nltk.download('stopwords', quiet=True)
            nltk.download('punkt', quiet=True)
            stopwords_set = set(stopwords.words('english'))

        all_words = []
        
        for doc in documents:
            text = doc.get('clean_text', '')
            if not text:
                continue
            
            # Tokenize and filter
            try:
                words = word_tokenize(text.lower())
                filtered_words = [
                    word for word in words 
                    if word.isalpha() and len(word) > 3 and word not in stopwords_set
                ]
                all_words.extend(filtered_words)
            except:
                pass

        # Get top N keywords
        word_counts = Counter(all_words)
        top_keywords = [word for word, count in word_counts.most_common(top_n)]

        return jsonify({
            'status': 'success',
            'message': 'Keyword cloud retrieved',
            'data': top_keywords
        }), 200

    except Exception as e:
        logger.error(f"Keyword cloud error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get keyword cloud: {str(e)}'
        }), 500


@dashboard_bp.route('/location-heatmap', methods=['GET'])
@jwt_required()
def get_location_heatmap():
    """
    Get location heatmap data (chart-ready)
    
    Query params:
    - event_type: Filter by event type (default: all)
    - sentiment: Filter by sentiment (optional)
    
    Returns:
    {
        "Pune": {"count": 45, "sentiment": "negative"},
        "Mumbai": {"count": 32, "sentiment": "negative"}
    }
    """
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        user_id = get_jwt_identity()
        
        event_type = request.args.get('event_type')
        sentiment_filter = request.args.get('sentiment')

        # Build query
        query = {
            'user_id': user_id,
            'processed': True,
            'locations': {'$exists': True, '$ne': []}
        }
        
        if event_type and event_type != 'all':
            query['event_type'] = event_type
        if sentiment_filter:
            query['sentiment.label'] = sentiment_filter

        # Get documents
        documents = list(current_app.db.documents.find(query, {
            'locations': 1,
            'sentiment.label': 1,
            'event_type': 1
        }))

        # Aggregate location counts and sentiment
        location_data = {}
        
        for doc in documents:
            locations = doc.get('locations', [])
            sentiment = doc.get('sentiment', {}).get('label', 'neutral')
            
            for loc in locations:
                # Get the most specific location (city > state > country)
                location_name = loc.get('city') or loc.get('state') or loc.get('country')
                
                if not location_name:
                    continue
                
                if location_name not in location_data:
                    location_data[location_name] = {
                        'count': 0,
                        'sentiments': []
                    }
                
                location_data[location_name]['count'] += 1
                location_data[location_name]['sentiments'].append(sentiment)

        # Calculate dominant sentiment for each location
        heatmap_data = {}
        for location, data in location_data.items():
            sentiment_counts = Counter(data['sentiments'])
            dominant_sentiment = sentiment_counts.most_common(1)[0][0] if sentiment_counts else 'neutral'
            
            heatmap_data[location] = {
                'count': data['count'],
                'sentiment': dominant_sentiment
            }

        return jsonify({
            'status': 'success',
            'message': 'Location heatmap retrieved',
            'data': heatmap_data
        }), 200

    except Exception as e:
        logger.error(f"Location heatmap error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get location heatmap: {str(e)}'
        }), 500


@dashboard_bp.route('/event-distribution', methods=['GET'])
@jwt_required()
def get_event_distribution():
    """
    Get event type distribution (chart-ready)
    
    Returns:
    {
        "flood": 120,
        "fire": 45,
        "earthquake": 12,
        "landslide": 8,
        "terror_attack": 3,
        "other": 33
    }
    """
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        user_id = get_jwt_identity()

        # Aggregate event counts
        pipeline = [
            {'$match': {'user_id': user_id, 'processed': True}},
            {'$group': {
                '_id': '$event_type',
                'count': {'$sum': 1}
            }}
        ]
        
        results = list(current_app.db.documents.aggregate(pipeline))
        
        # Format for chart
        event_dist = {}
        for result in results:
            event_type = result['_id'] or 'other'
            event_dist[event_type] = result['count']

        return jsonify({
            'status': 'success',
            'message': 'Event distribution retrieved',
            'data': event_dist
        }), 200

    except Exception as e:
        logger.error(f"Event distribution error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get event distribution: {str(e)}'
        }), 500


@dashboard_bp.route('/language-distribution', methods=['GET'])
@jwt_required()
def get_language_distribution():
    """
    Get language distribution (chart-ready)
    
    Returns:
    {
        "en": 150,
        "hi": 80,
        "es": 40,
        "fr": 25
    }
    """
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        user_id = get_jwt_identity()

        # Aggregate language counts
        pipeline = [
            {'$match': {'user_id': user_id, 'processed': True}},
            {'$group': {
                '_id': '$language',
                'count': {'$sum': 1}
            }}
        ]
        
        results = list(current_app.db.documents.aggregate(pipeline))
        
        # Format for chart
        language_dist = {}
        for result in results:
            language = result['_id'] or 'unknown'
            language_dist[language] = result['count']

        return jsonify({
            'status': 'success',
            'message': 'Language distribution retrieved',
            'data': language_dist
        }), 200

    except Exception as e:
        logger.error(f"Language distribution error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get language distribution: {str(e)}'
        }), 500


@dashboard_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_overall_stats():
    """
    Get overall dashboard statistics
    
    Returns summary stats for quick overview
    """
    try:
        if current_app.db is None:
            return jsonify({
                'status': 'error',
                'message': 'Database not available'
            }), 500

        user_id = get_jwt_identity()

        # Get total counts
        total_documents = current_app.db.documents.count_documents({'user_id': user_id})
        processed_documents = current_app.db.documents.count_documents({
            'user_id': user_id,
            'processed': True
        })
        
        # Get unique languages count
        languages = current_app.db.documents.distinct('language', {'user_id': user_id})
        unique_languages = len([lang for lang in languages if lang])
        
        # Get document sources
        sources = current_app.db.documents.distinct('source', {'user_id': user_id})

        return jsonify({
            'status': 'success',
            'message': 'Overall stats retrieved',
            'data': {
                'total_documents': total_documents,
                'processed_documents': processed_documents,
                'unique_languages': unique_languages,
                'sources': sources
            }
        }), 200

    except Exception as e:
        logger.error(f"Overall stats error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get overall stats: {str(e)}'
        }), 500
