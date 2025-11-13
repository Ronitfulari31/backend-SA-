from pymongo import MongoClient
import logging

logger = logging.getLogger(__name__)

db = None
client = None


def init_db(app):
    """
    Initialize MongoDB connection and attach it to the Flask app.
    Ensures the connection is verified and accessible globally.
    """
    global db, client
    try:
        # Load URI from Flask config or fallback to default local DB
        mongodb_uri = app.config.get(
            'MONGODB_URI',
            'mongodb://localhost:27017/legal_sentiment_db'
        )

        # Establish connection with timeout
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')  # Test connection

        # Extract database name from URI (last part after '/')
        db_name = mongodb_uri.split('/')[-1] or 'legalbot'
        db = client[db_name]
        app.db = db
        app.mongo_client = client

        logger.info(f"✓ Connected to MongoDB: {mongodb_uri}")
        logger.info(f"✓ Using database: {db_name}")

        collections = db.list_collection_names()
        if collections:
            logger.info(f"✓ Available collections: {collections}")
        else:
            logger.info("ℹ No collections found yet — database initialized empty.")

        return db

    except Exception as e:
        logger.error(f"✗ Failed to connect to MongoDB: {str(e)}")
        logger.warning("⚠ Proceeding without MongoDB connection — some features may not work.")
        app.db = None
        app.mongo_client = None
        return None


def get_db():
    """
    Get the active MongoDB connection.
    Logs a warning if accessed before initialization.
    """
    global db
    if db is None:
        logger.warning("⚠ Database not initialized. Call init_db(app) first.")
    return db


def close_db():
    """
    Gracefully close MongoDB connection.
    Useful for shutdowns or tests.
    """
    global client
    if client:
        client.close()
        logger.info("✓ MongoDB connection closed.")
