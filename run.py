import os
import logging
import signal
from dotenv import load_dotenv

from app import create_app
from app.database import init_db, close_db

# ---------------------------------------------------------
# ENVIRONMENT SETUP (CRITICAL FOR ML STABILITY)
# ---------------------------------------------------------

# Hugging Face cache redirection (prevents C:\ drive bloat)
os.environ.setdefault(
    "HF_HOME",
    r"D:\Projects\Backend(SA)_cache\hf_cache"
)

# Disable Hugging Face telemetry
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

# ---------------------------------------------------------
# LOAD ENV & LOGGING
# ---------------------------------------------------------

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# CREATE APPLICATION (NO ML LOAD HERE)
# ---------------------------------------------------------

app = create_app()
init_db(app)

# ---------------------------------------------------------
# IMPORT & REGISTER BLUEPRINTS
# ---------------------------------------------------------

from app.routes.auth import auth_bp
from app.routes.documents import documents_bp
from app.routes.reports import reports_bp
from app.routes.settings import settings_bp
from app.routes.dashboard import dashboard_bp
from app.routes.evaluation import evaluation_bp
from app.routes.news import news_bp

app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(documents_bp, url_prefix="/api/documents")
app.register_blueprint(reports_bp, url_prefix="/api")
app.register_blueprint(settings_bp, url_prefix="/api")
app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
app.register_blueprint(evaluation_bp, url_prefix="/api/evaluation")
app.register_blueprint(news_bp, url_prefix="/api/news")

logger.info("✓ Authentication API registered")
logger.info("✓ Documents API registered")
logger.info("✓ Dashboard API registered")
logger.info("✓ Evaluation API registered")
logger.info("✓ News API registered")

# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health_check():
    """
    Lightweight health check.
    NOTE: Does NOT trigger ML model loading.
    """
    return {
        "status": "healthy",
        "message": "Backend server is running",
        "services": {
            "sentiment_analysis": "lazy",
            "translation": "active",
            "event_detection": "active",
            "location_extraction": "active",
            "authentication": "active",
            "documents": "active",
        },
    }, 200


# ---------------------------------------------------------
# NLP FEATURES METADATA
# ---------------------------------------------------------

@app.route("/api/nlp-features", methods=["GET"])
def get_nlp_features():
    return {
        "status": "success",
        "features": [
            "Sentiment Analysis (BERTweet / VADER / TextBlob)",
            "Multilingual Translation",
            "Event Detection (Keyword + ML Hybrid)",
            "Location Extraction (NER)",
            "Cross-Lingual Evaluation",
        ],
    }, 200


# ---------------------------------------------------------
# ERROR HANDLERS
# ---------------------------------------------------------

@app.errorhandler(404)
def not_found(error):
    return {
        "status": "error",
        "message": "Resource not found",
        "path": str(error),
    }, 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error: {error}")
    return {
        "status": "error",
        "message": "Internal server error",
    }, 500


# ---------------------------------------------------------
# GRACEFUL SHUTDOWN
# ---------------------------------------------------------

def handle_shutdown(*args):
    logger.info("🛑 Shutdown signal received")
    close_db()
    logger.info("✅ MongoDB connection closed")
    logger.info("👋 Server stopped cleanly")
    exit(0)


signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

# ---------------------------------------------------------
# SERVER STARTUP
# ---------------------------------------------------------

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🚀 Multimodal Post-Disaster Intelligence Backend")
    logger.info("=" * 60)
    logger.info("STATUS: Core services initialized")
    logger.info(f"DATABASE: {app.config.get('MONGODB_URI')}")
    logger.info(f"HF CACHE: {os.environ.get('HF_HOME')}")
    logger.info("-" * 60)
    logger.info("ML SERVICES:")
    logger.info("  ✓ Sentiment Analysis (lazy-loaded BERTweet)")
    logger.info("  ✓ Event Detection (keyword + ML)")
    logger.info("  ✓ Location Extraction")
    logger.info("=" * 60)
    logger.info("Server is listening for requests...")

    app.run(
        debug=os.getenv("FLASK_DEBUG", True),
        host=os.getenv("FLASK_HOST", "0.0.0.0"),
        port=int(os.getenv("FLASK_PORT", 5000)),
        use_reloader=False  # Windows-safe, avoids duplicate ML loads
    )
