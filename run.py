import os
import logging
import signal
from dotenv import load_dotenv
from app import create_app, socketio
from app.database import init_db, close_db

# Import all blueprints
# from app.routes.sentiment import sentiment_bp       # Replaced by SentimentService
# from app.routes.translation import translation_bp     # Replaced by TranslationService
# from app.routes.summarization import summarization_bp # Replaced by pipeline (future)
# from app.routes.keyword_extraction import keyword_bp  # Replaced by EventDetectionService
from app.routes.auth import auth_bp
from app.routes.documents import documents_bp
# from app.routes.ner import ner_bp                     # Replaced by LocationExtractionService
# from app.routes.classification import classification_bp # Replaced by EventDetectionService
from app.routes.reports import reports_bp
from app.routes.settings import settings_bp
from app.routes.dashboard import dashboard_bp
from app.routes.evaluation import evaluation_bp
# Uncomment if you later add a realtime Blueprint
# from app.routes.realtime import realtime_bp

# Load environment variables
load_dotenv()

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create app
app = create_app()

# Initialize database
init_db(app)

# Register all blueprints
# app.register_blueprint(sentiment_bp, url_prefix='/api/documents')
# app.register_blueprint(translation_bp, url_prefix='/api/documents')
# app.register_blueprint(summarization_bp, url_prefix='/api/documents')
# app.register_blueprint(keyword_bp, url_prefix='/api/documents')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(documents_bp, url_prefix='/api/documents')
# app.register_blueprint(ner_bp, url_prefix='/api/documents')
# app.register_blueprint(classification_bp, url_prefix='/api/documents')
app.register_blueprint(reports_bp, url_prefix='/api')
app.register_blueprint(settings_bp, url_prefix='/api')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
app.register_blueprint(evaluation_bp, url_prefix='/api/evaluation')
# Uncomment if realtime routes are added:
# app.register_blueprint(realtime_bp, url_prefix='/api')

# Log registration status
# logger.info("✓ Sentiment Analysis API registered")
# logger.info("✓ Translation API registered")
# logger.info("✓ Summarization API registered")
# logger.info("✓ Keyword Extraction API registered")
logger.info("✓ Authentication API registered")
logger.info("✓ Documents API registered")
# logger.info("✓ Named Entity Recognition API registered")
# logger.info("✓ Document Classification API registered")


# ---------------- Health Check ----------------
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'message': 'Backend server is running',
        'services': {
            'sentiment_analysis': 'active',
            'translation': 'active',
            'summarization': 'active',
            'keyword_extraction': 'active',
            'authentication': 'active',
            'documents': 'active'
        }
    }, 200


# ---------------- NLP Features Endpoint ----------------
@app.route('/api/nlp-features', methods=['GET'])
def get_nlp_features():
    """Get list of all available NLP features"""
    return {
        'status': 'success',
        'message': 'Available NLP Features',
        'features': [
            {
                'name': 'Sentiment Analysis',
                'description': 'Analyze sentiment of document content using TextBlob and VADER',
                'endpoints': [
                    {'method': 'GET', 'route': '/api/documents/<document_id>/sentiment', 'description': 'Full sentiment analysis'},
                    {'method': 'GET', 'route': '/api/documents/<document_id>/sentiment/summary', 'description': 'Quick sentiment summary'}
                ]
            },
            {
                'name': 'Translation',
                'description': 'Translate documents to multiple languages',
                'endpoints': [
                    {'method': 'POST', 'route': '/api/documents/<document_id>/translate', 'description': 'Translate to single language', 'body': '{"target_language": "es", "source_language": "en"}'},
                    {'method': 'POST', 'route': '/api/documents/<document_id>/translate-batch', 'description': 'Translate to multiple languages', 'body': '{"target_languages": ["es", "fr", "de"]}'},
                    {'method': 'GET', 'route': '/api/languages', 'description': 'Get supported languages'}
                ]
            },
            {
                'name': 'Summarization',
                'description': 'Summarize document content',
                'endpoints': [
                    {'method': 'POST', 'route': '/api/documents/<document_id>/summarize', 'description': 'Summarize using LSA or Luhn', 'body': '{"sentences_count": 3, "method": "lsa"}'},
                    {'method': 'POST', 'route': '/api/documents/<document_id>/summarize-adaptive', 'description': 'Adaptive summarization', 'body': '{"compression_ratio": 0.3}'},
                    {'method': 'POST', 'route': '/api/documents/<document_id>/summarize-compare', 'description': 'Compare LSA and Luhn methods'}
                ]
            },
            {
                'name': 'Keyword Extraction',
                'description': 'Extract keywords from documents',
                'endpoints': [
                    {'method': 'POST', 'route': '/api/documents/<document_id>/keywords', 'description': 'Extract keywords using RAKE or YAKE', 'body': '{"method": "rake", "top_n": 10}'},
                    {'method': 'POST', 'route': '/api/documents/<document_id>/keywords-compare', 'description': 'Compare RAKE and YAKE methods'},
                    {'method': 'GET', 'route': '/api/documents/<document_id>/keywords-frequency', 'description': 'Get keyword frequency statistics'}
                ]
            },
            {
                'name': 'Authentication',
                'description': 'User registration, login, and profile management',
                'endpoints': [
                    {'method': 'POST', 'route': '/api/auth/register', 'description': 'Register a new user'},
                    {'method': 'POST', 'route': '/api/auth/login', 'description': 'Login and get JWT token'},
                    {'method': 'GET', 'route': '/api/auth/me', 'description': 'Get current user info (protected)'}
                ]
            }
        ]
    }, 200


# ---------------- Error Handlers ----------------
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return {'status': 'error', 'message': 'Resource not found', 'path': str(error)}, 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal Server Error: {str(error)}")
    return {'status': 'error', 'message': 'Internal server error'}, 500


# ---------------- SocketIO Events (Temporarily Disabled) ----------------
# @socketio.on('connect')
# def handle_connect():
#     logger.info("Client connected")


# @socketio.on('disconnect')
# def handle_disconnect():
#     logger.info("Client disconnected")


# @socketio.on('send_update')
# def handle_update(data):
#     socketio.emit('update', data, broadcast=True)



# ---------------- Graceful Shutdown ----------------
def handle_shutdown(*args):
    """Handle shutdown signals (Ctrl+C, Docker stop, etc.)"""
    logger.info("🛑 Received shutdown signal. Closing MongoDB connection...")
    close_db()
    logger.info("✅ Shutdown complete. Bye 👋")
    exit(0)


signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)


# ---------------- Server Startup ----------------
if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🚀 Starting LegalBot NLP Backend Server")
    logger.info("=" * 60)
    logger.info(f"MongoDB URI: {app.config['MONGODB_URI']}")
    logger.info("NLP Features Enabled:")
    logger.info("  ✓ Sentiment Analysis (TextBlob + VADER)")
    logger.info("  ✓ Translation (Deep Translator)")
    logger.info("  ✓ Summarization (Sumy - LSA & Luhn)")
    logger.info("  ✓ Keyword Extraction (RAKE & YAKE)")
    logger.info("  ✓ Authentication (JWT)")
    logger.info("  ✓ Documents (Upload, List, NLP)")
    logger.info("=" * 60)

    # Use standard Flask run instead of socketio.run (temporarily disabled)
    app.run(
        debug=os.getenv('FLASK_DEBUG', True),
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', 5000))
    )

