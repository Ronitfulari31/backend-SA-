from flask import Flask
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

socketio = None  # Placeholder


def create_app(config_name='development'):
    """Application factory"""
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config[config_name])

    # Initialize extensions
    CORS(app, origins=app.config.get('CORS_ORIGINS', '*'))
    JWTManager(app)

    # MongoDB connection
    from app.database import init_db
    init_db(app)

    # Register global error handlers
    register_error_handlers(app)



    return app
