# app/__init__.py
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from pymongo import MongoClient
import logging
from app.config import config
from app.middleware.error_handler import register_error_handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_name='development'):
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    CORS(app, origins=app.config['CORS_ORIGINS'])
    jwt = JWTManager(app)
    
    # MongoDB connection
    try:
        client = MongoClient(app.config['MONGODB_URI'])
        db = client[app.config['MONGODB_DB_NAME']]
        
        # Store both client and db
        app.db = db
        app.mongo_client = client  # ✅ Store client too
        
        # Test connection - use client.admin_command() not db.admin_command()
        client.admin.command('ping')
        logger.info("✓ Connected to MongoDB successfully")
    except Exception as e:
        logger.error(f"✗ MongoDB connection error: {e}")
        app.db = None
        app.mongo_client = None
    
    # Register error handlers
    register_error_handlers(app)
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        try:
            if app.db is not None and app.mongo_client is not None:
                # ✅ Use client.admin.command() not db.admin_command()
                app.mongo_client.admin.command('ping')
                return jsonify({
                    'status': 'healthy',
                    'database': 'connected'
                }), 200
            else:
                return jsonify({
                    'status': 'unhealthy',
                    'database': 'disconnected'
                }), 500
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 500
    
    # Register blueprints
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    
    return app
