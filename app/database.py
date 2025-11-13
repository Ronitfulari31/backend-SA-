from pymongo import MongoClient
import os
import logging

logger = logging.getLogger(__name__)

db = None

def init_db(app):
    """
    Initialize MongoDB connection and attach it to the Flask app
    """
    global db
    try:
        mongodb_uri = app.config.get('MONGODB_URI', 'mongodb://localhost:27017/legal_sentiment_db')
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db_name = mongodb_uri.split('/')[-1] or 'legalbot'
        db = client[db_name]
        app.db = db  # Attach db to app object
        logger.info(f"✓ Connected to MongoDB database: {db_name}")
        logger.info(f"✓ Available collections: {db.list_collection_names()}")
        return db
    except Exception as e:
        logger.error(f"✗ Failed to connect to MongoDB: {str(e)}")
        logger.warning("Proceeding without MongoDB connection (some features may not work)")
        return None

def get_db():
    global db
    if db is None:
        logger.warning("Database not initialized. Call init_db() first.")
    return db
