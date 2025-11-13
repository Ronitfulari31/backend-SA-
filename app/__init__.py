from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from pymongo import MongoClient
import logging
from flask_socketio import SocketIO
from app.config import config
from app.middleware.error_handler import register_error_handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global SocketIO instance
socketio = SocketIO(cors_allowed_origins="*")


def create_app(config_name='development'):
    """Application factory"""
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config[config_name])

    # Initialize extensions
    CORS(app, origins=app.config.get('CORS_ORIGINS', '*'))
    JWTManager(app)
    socketio.init_app(app)

    # MongoDB connection
    try:
        client = MongoClient(app.config['MONGODB_URI'])
        db = client[app.config['MONGODB_DB_NAME']]
        app.db = db
        app.mongo_client = client

        client.admin.command('ping')
        logger.info("✓ Connected to MongoDB successfully")

        # Initialize your DB (indexes, collections, etc.)
        from app.database import init_db
        init_db(app.db)

    except Exception as e:
        logger.error(f"✗ MongoDB connection error: {e}")
        app.db = None
        app.mongo_client = None

    # Register global error handlers
    register_error_handlers(app)

    # Register routes and socket events
    from app.routes.realtime import register_realtime_events, realtime_bp
    app.register_blueprint(realtime_bp)
    register_realtime_events(socketio)

    return app
