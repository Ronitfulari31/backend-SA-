import logging
import os

# ---------------------------------------------------------
# Environment Safeguards (Early Initialization)
# ---------------------------------------------------------
D_CACHE_BASE = r"D:\Projects\Backend(SA)_cache"
os.environ["ARGOS_PACKAGES_DIR"] = os.path.join(D_CACHE_BASE, "argos_cache", "packages")
os.environ["TEMP"] = os.path.join(D_CACHE_BASE, "temp")
os.environ["TMP"] = os.environ["TEMP"]

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from app.config import config
from app.middleware.error_handler import register_error_handlers


# ---------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

socketio = None  # Placeholder


# ---------------------------------------------------------
# Application Factory
# ---------------------------------------------------------
def create_app(config_name='development'):
    """Application factory"""
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config[config_name])

    # -----------------------------------------------------
    # 🔐 Mandatory Config Validation
    # -----------------------------------------------------
    if not app.config.get("NEWSAPI_KEY"):
        raise RuntimeError(
            "NEWSAPI_KEY is not set. "
            "Please define it in the .env file."
        )

    logger.info("Configuration loaded successfully")

    # -----------------------------------------------------
    # Initialize Extensions
    # -----------------------------------------------------
    CORS(app, origins=app.config.get('CORS_ORIGINS', '*'))
    JWTManager(app)

    # -----------------------------------------------------
    # Database Initialization
    # -----------------------------------------------------
    from app.database import init_db
    init_db(app)

    # -----------------------------------------------------
    # Register Error Handlers
    # -----------------------------------------------------
    register_error_handlers(app)

    # -----------------------------------------------------
    # Diagnostics & Logging
    # -----------------------------------------------------
    from app.services.translation import translation_service
    translation_service.init_argos()

    logger.info("Application initialized successfully")

    return app
