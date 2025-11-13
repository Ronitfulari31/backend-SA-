from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import os
import logging


# Load environment variables
load_dotenv()


# Initialize Flask App
app = Flask(__name__)


# Configuration
app.config['MONGODB_URI'] = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/legalbot')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))


# Initialize Extensions
CORS(app)
JWTManager(app)


# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Import database connection
from app.database import init_db
init_db(app)


# ==========================================
# REGISTER ALL BLUEPRINT ROUTES
# ==========================================


# Import all blueprint modules
from app.routes.sentiment import sentiment_bp
from app.routes.translation import translation_bp
from app.routes.summarization import summarization_bp
from app.routes.keyword_extraction import keyword_bp
from app.routes.auth import auth_bp
from app.routes.documents import documents_bp  # Import documents blueprint


# Register all blueprints with correct URL prefixes
app.register_blueprint(sentiment_bp, url_prefix='/api/documents')
app.register_blueprint(translation_bp, url_prefix='/api/documents')
app.register_blueprint(summarization_bp, url_prefix='/api/documents')
app.register_blueprint(keyword_bp, url_prefix='/api/documents')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(documents_bp, url_prefix='/api/documents')  


# Log registration status
logger.info("✓ Sentiment Analysis API registered")
logger.info("✓ Translation API registered")
logger.info("✓ Summarization API registered")
logger.info("✓ Keyword Extraction API registered")
logger.info("✓ Authentication API registered")
logger.info("✓ Documents API registered")


# ==========================================
# HEALTH CHECK ENDPOINT
# ==========================================
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


# ==========================================
# NLP FEATURES LIST ENDPOINT
# ==========================================
@app.route('/api/nlp-features', methods=['GET'])
def get_nlp_features():
    """Get list of all available NLP features and their endpoints"""
    return {
        'status': 'success',
        'message': 'Available NLP Features',
        'features': [
            {
                'name': 'Sentiment Analysis',
                'description': 'Analyze sentiment of document content using TextBlob and VADER',
                'endpoints': [
                    {
                        'method': 'GET',
                        'route': '/api/documents/<document_id>/sentiment',
                        'description': 'Full sentiment analysis'
                    },
                    {
                        'method': 'GET',
                        'route': '/api/documents/<document_id>/sentiment/summary',
                        'description': 'Quick sentiment summary'
                    }
                ]
            },
            {
                'name': 'Translation',
                'description': 'Translate documents to multiple languages',
                'endpoints': [
                    {
                        'method': 'POST',
                        'route': '/api/documents/<document_id>/translate',
                        'description': 'Translate to single language',
                        'body': '{"target_language": "es", "source_language": "en"}'
                    },
                    {
                        'method': 'POST',
                        'route': '/api/documents/<document_id>/translate-batch',
                        'description': 'Translate to multiple languages',
                        'body': '{"target_languages": ["es", "fr", "de"]}'
                    },
                    {
                        'method': 'GET',
                        'route': '/api/languages',
                        'description': 'Get supported languages'
                    }
                ]
            },
            {
                'name': 'Summarization',
                'description': 'Summarize document content',
                'endpoints': [
                    {
                        'method': 'POST',
                        'route': '/api/documents/<document_id>/summarize',
                        'description': 'Summarize using LSA or Luhn',
                        'body': '{"sentences_count": 3, "method": "lsa"}'
                    },
                    {
                        'method': 'POST',
                        'route': '/api/documents/<document_id>/summarize-adaptive',
                        'description': 'Adaptive summarization',
                        'body': '{"compression_ratio": 0.3}'
                    },
                    {
                        'method': 'POST',
                        'route': '/api/documents/<document_id>/summarize-compare',
                        'description': 'Compare LSA and Luhn methods'
                    }
                ]
            },
            {
                'name': 'Keyword Extraction',
                'description': 'Extract keywords from documents',
                'endpoints': [
                    {
                        'method': 'POST',
                        'route': '/api/documents/<document_id>/keywords',
                        'description': 'Extract keywords using RAKE or YAKE',
                        'body': '{"method": "rake", "top_n": 10}'
                    },
                    {
                        'method': 'POST',
                        'route': '/api/documents/<document_id>/keywords-compare',
                        'description': 'Compare RAKE and YAKE methods'
                    },
                    {
                        'method': 'GET',
                        'route': '/api/documents/<document_id>/keywords-frequency',
                        'description': 'Get keyword frequency statistics'
                    }
                ]
            },
            {
                'name': 'Authentication',
                'description': 'User registration, login, and profile management',
                'endpoints': [
                    {
                        'method': 'POST',
                        'route': '/api/auth/register',
                        'description': 'Register a new user'
                    },
                    {
                        'method': 'POST',
                        'route': '/api/auth/login',
                        'description': 'Login and get JWT token'
                    },
                    {
                        'method': 'GET',
                        'route': '/api/auth/me',
                        'description': 'Get current user info (protected)'
                    }
                ]
            }
        ]
    }, 200


# ==========================================
# ERROR HANDLERS
# ==========================================
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return {
        'status': 'error',
        'message': 'Resource not found',
        'path': error.description
    }, 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal Server Error: {str(error)}")
    return {
        'status': 'error',
        'message': 'Internal server error'
    }, 500


if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("Starting LegalBot NLP Backend Server")
    logger.info("=" * 50)
    logger.info(f"MongoDB URI: {app.config['MONGODB_URI']}")
    logger.info("NLP Features Enabled:")
    logger.info("  ✓ Sentiment Analysis (TextBlob + VADER)")
    logger.info("  ✓ Translation (Deep Translator)")
    logger.info("  ✓ Summarization (Sumy - LSA & Luhn)")
    logger.info("  ✓ Keyword Extraction (RAKE & YAKE)")
    logger.info("  ✓ Authentication (JWT)")
    logger.info("  ✓ Documents (Upload, List, NLP)")
    logger.info("=" * 50)
    
    app.run(
        debug=os.getenv('FLASK_DEBUG', True),
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', 5000))
    )
